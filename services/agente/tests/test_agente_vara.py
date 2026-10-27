"""La vara (`agente/vara.py`): que mida, que no se engañe y que no filtre datos."""
from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import pytest
from agente import agente, conversacion, guardia, historial, jugadas, respuestas, vara
from agente.espacio import Espacio
from agente.historial import Mensaje

DIA = 86400
T0 = 1785000000
BIENVENIDA = "Gracias por comunicarte con la finca. Dinos tus fechas y personas"


def _m(ident, texto, del_negocio, ts, hilo, tipo="text"):
    return Mensaje(id=ident, hilo=hilo, del_negocio=del_negocio, ts=ts, tipo=tipo, texto=texto)


def _universo(raiz: Path, hilos: int = 60, dias: int = 90) -> Espacio:
    """Un negocio ficticio: cada hilo llega, recibe la bienvenida y una persona contesta."""
    espacio = Espacio("prueba-vara", raiz)
    respuestas_casa = ["25,000 el fin de semana", "Que fecha ?", "Ya tenemos ocupado esa fecha",
                       "Estamos ubicados en Chiconcuac", "Con gusto quedo pendiente"]
    mensajes = []
    for i in range(hilos):
        h = f"52177700{i:05d}"
        t = T0 + int(i * dias * DIA / hilos)
        mensajes += [
            _m(f"a{i}", "¡Hola! Quiero más información", False, t, h),
            _m(f"b{i}", BIENVENIDA, True, t + 2, h),
            _m(f"c{i}", f"Para {10 + i % 20} personas, ¿precio?", False, t + 60, h),
            _m(f"d{i}", respuestas_casa[i % len(respuestas_casa)], True, t + 900, h),
            _m(f"e{i}", "Ok gracias", False, t + 2000, h),
        ]
    historial.guardar(espacio, mensajes)
    return espacio


@pytest.fixture()
def bitacora(tmp_path, monkeypatch):
    ruta = tmp_path / "intentos.jsonl"
    monkeypatch.setenv(vara.VARIABLE_BITACORA, str(ruta))
    return ruta


# ----------------------------------------------------------------- el agente en vivo
def test_vara_la_bienvenida_automatica_no_calla_al_agente_en_vivo():
    """Hallazgo 2026-10-27: la bienvenida de WhatsApp Business contaba como "una
    persona ya contestó" y el agente callaba 24 h (339 de 1,003 momentos)."""
    h = "5210000000001"
    hilo = [_m("a", "Hola", False, T0, h), _m("b", BIENVENIDA, True, T0 + 2, h),
            _m("c", "¿Precio para 20?", False, T0 + 60, h)]
    assert not agente.lo_lleva_una_persona(hilo, hilo[-1], {BIENVENIDA})
    hilo.insert(2, _m("p", "Que fecha ?", True, T0 + 30, h))      # una persona sí escribió
    assert agente.lo_lleva_una_persona(hilo, hilo[-1], {BIENVENIDA})


def test_vara_decidir_en_vivo_no_se_calla_por_la_bienvenida(espacio):
    """El turno real, con perfil aprobado: tras la bienvenida no dice "lo lleva una persona"."""
    mensajes = []
    for i in range(jugadas.USOS_DE_PLANTILLA):
        h = f"5510000{i:04d}"
        mensajes += [_m(f"x{i}", "Hola", False, T0 + i, h), _m(f"y{i}", BIENVENIDA, True, T0 + i + 2, h)]
    historial.guardar(espacio, mensajes)
    entrante = _m("z0", "¿Tienen alberca?", False, T0 + 120, "55100000000")
    historial.guardar(espacio, [entrante])
    salida = agente.decidir(espacio, entrante, en_vivo=True)
    assert "lo lleva una persona" not in salida.motivo


# ----------------------------------------------------------------- fidelidad
def test_vara_simula_con_el_mismo_codigo_del_turno(espacio):
    """Donde el turno no va al modelo, la vara y `decidir` dicen lo mismo; donde
    iría, la vara dice `ia` y no llama a nada."""
    from agente import perfil

    activo = perfil.activo(espacio)
    casos = ["Exijo mi reembolso", "¿Eres un bot?", "Quiero hablar con una persona", "Ya rentamos en otro lado",
             "Ok gracias", "¿Aceptan mascotas?", "¿Tienen disponible del 13 al 15 para 20?"]
    for i, texto in enumerate(casos):
        h = f"56{i:08d}"
        entrante = _m(f"k{i}", texto, False, T0 + i, h)
        historial.guardar(espacio, [entrante])
        real = agente.decidir(espacio, entrante)
        momento = jugadas.Momento(id="r", hilo=h, ts=T0 + i + 5, entrante=entrante, prefijo=(entrante,),
                                  tanda=(), casa="acuse", cliente=texto)
        simulado = vara.simular(momento, activo)
        if simulado["via"] == "ia":
            assert real.via not in ("regla", "guardada", "silencio")
        else:
            assert (simulado["via"], simulado["motivo"]) == (real.via, real.motivo)


def test_vara_el_camino_que_decide_no_lee_el_reloj_de_pared():
    """El backtest re-simula momentos viejos: si el código del turno mirara la hora
    de HOY, la vara no mediría al agente de entonces (fq-bot §6.7)."""
    fuentes = [inspect.getsource(agente.antes_del_modelo), inspect.getsource(agente.lo_lleva_una_persona)]
    fuentes += [inspect.getsource(mod) for mod in (jugadas, conversacion, respuestas, guardia)]
    for fuente in fuentes:
        assert not re.search(r"datetime\.now|time\.time\(|date\.today|utcnow", fuente)


# ----------------------------------------------------------------- partición
def test_vara_holdout_out_of_time_con_embargo_y_purga_por_hilo():
    moms = [{"id": str(i), "hilo": f"h{i % 30}", "ts": T0 + i * DIA // 2} for i in range(200)]
    dev, holdout, info = vara.partir(moms)
    corte = vara.corte_de(moms)
    assert len(holdout) == 50 and min(m["ts"] for m in holdout) == corte
    assert all(m["ts"] < corte - vara.EMBARGO_DIAS * DIA for m in dev)
    assert not {m["hilo"] for m in dev} & {m["hilo"] for m in holdout}
    assert info["purgados"] == 200 - len(dev) - len(holdout) > 0


# ----------------------------------------------------------------- que mida algo
def test_vara_placebo_no_cae_con_un_agente_constante_y_si_con_el_oraculo():
    casas = ["cifra", "pide:fechas", "acuse", "disponibilidad", "info:ubicacion"] * 20
    moms = [{"casa": c, "bot": "persona", "oraculo": c} for c in casas]
    assert not vara.placebo(moms)["colapsa"]              # pasarlo todo no es habilidad
    assert vara.placebo(moms, bot="oraculo")["colapsa"]  # la vara distingue al que sí acierta


def test_vara_costos():
    assert vara.puntaje({"casa": "cifra", "bot": "persona"}) == (0.3, "politica_pasa")
    assert vara.puntaje({"casa": "acuse", "bot": "silencio"}) == (0.3, "politica_silencio")
    assert vara.puntaje({"casa": "pide:fechas", "bot": "silencio", "cliente": "¿Precio?"}) == (-1.0, "calla_cuando_pedian")
    # costos v2: tras un "Ok" la casa tomó la iniciativa; callar es la política, no un error caro
    assert vara.puntaje({"casa": "pide:otra", "bot": "silencio", "cliente": "Ok"})[1] == "neutra"
    assert vara.puntaje({"casa": "confirma", "bot": "silencio", "cliente": "Ah ok / Te confirmo entonces"})[1] != \
        "calla_cuando_pedian"
    assert vara.puntaje({"casa": "info:ubicacion", "bot": "info:ubicacion"}) == (1.0, "igual")
    assert vara.puntaje({"casa": "cifra", "bot": "cifra", "texto": "Son $5,000"})[1] == "cifra"
    assert vara.puntaje({"casa": "acuse", "bot": "otra", "texto": "Soy una persona"})[1] == "dice_ser_persona"


def test_vara_dsr_y_pbo():
    assert vara.dsr([0.2, 0.3, 0.25, 0.4, 0.1] * 10, 1)["dsr"] > 0.95
    assert vara.dsr([0.2, -0.3, 0.05, -0.1, 0.1] * 10, 20)["dsr"] < 0.95
    assert vara.pbo([[0.3] * 8])["pbo"] is None
    assert vara.pbo([[0.3] * 8, [0.3] * 8])["pbo"] is None        # idénticos: no es 1.0
    assert vara.pbo([[0.1, 0.2] * 4, [0.3, 0.1] * 4])["pbo"] is not None


# ----------------------------------------------------------------- holdout y bitácora
def test_vara_el_holdout_se_abre_una_vez_por_candidato(tmp_path, bitacora):
    espacio = _universo(tmp_path)
    inf = vara.medir(espacio, "base", abrir_holdout=True)
    assert inf["particion"]["n_holdout"] > 0 and inf["holdout"]["n"] > 0
    with pytest.raises(vara.HoldoutYaAbierto):
        vara.medir(espacio, "base-otra-vez", abrir_holdout=True)
    assert "vara.py" not in vara.MODULOS_DEL_AGENTE         # editar la vara no hace un candidato nuevo
    assert vara.medir(espacio, "base-dev2")["perfil"]["aperturas_previas"] == 1
    vara.medir(espacio, "base-dev")                           # el desarrollo se mide las veces que sea


def test_vara_un_perfil_que_cita_el_holdout_no_lo_abre(tmp_path, bitacora):
    espacio = _universo(tmp_path)
    ultimo = historial.cargar(espacio)[-2]                    # un mensaje del negocio, del final
    activo = {"faq": [{"pregunta": "x", "respuesta": "y",
                       "origen": {"tipo": "mensaje", "id": ultimo.id, "cita": ultimo.texto}}]}
    with pytest.raises(vara.PerfilMiraElHoldout):
        vara.medir(espacio, "p-mira", activo=activo, abrir_holdout=True)
    assert vara.medir(espacio, "p-mira", activo=activo)["perfil"]["citas_en_embargo_u_holdout"] == 1


HASHES = ("bot", "universo", "sello", "commit", "fecha")


def _sin_hashes(fila: dict) -> str:
    return json.dumps({k: v for k, v in fila.items() if k not in HASHES}, ensure_ascii=False)


def _sin_datos_de_clientes(texto: str, espacio: Espacio) -> None:
    for linea in texto.splitlines():
        assert not re.search(r"\d{8,}", _sin_hashes(json.loads(linea))), "un teléfono en la bitácora"
    for m in historial.cargar(espacio):
        assert m.hilo not in texto
        if m.texto and len(m.texto) > 12:
            assert m.texto not in texto, "un texto de cliente en la bitácora"


def test_vara_la_bitacora_solo_lleva_agregados(tmp_path, bitacora):
    espacio = _universo(tmp_path)
    vara.medir(espacio, "base")
    vara.medir(espacio, "base2", contra="base")
    texto = bitacora.read_text(encoding="utf-8")
    _sin_datos_de_clientes(texto, espacio)
    filas = [json.loads(x) for x in texto.splitlines()]
    assert [f["variante"] for f in filas] == ["base", "base2"]
    assert filas[1]["contra"]["base"] == "base" and filas[1]["contra"]["delta_puntaje"] == 0
    # las predicciones selladas viven en el espacio (fuera de git), con su hash en la bitácora
    libro = espacio.ruta("vara/predicciones_base.jsonl")
    import hashlib
    assert hashlib.sha256(libro.read_bytes()).hexdigest() == filas[0]["sello"]


def test_vara_la_bitacora_del_repo_no_lleva_telefonos_ni_textos():
    """La que se sube a git: solo hashes, n y métricas."""
    if not vara.BITACORA.exists():
        pytest.skip("todavía no hay intentos")
    claves_permitidas = {"fecha", "cliente_id", "variante", "descripcion", "commit", "bot", "universo", "clasificador",
                         "costos_version", "vara_version", "sello", "particion", "perfil", "por_bloque", "placebo",
                         "cpcv", "dev", "holdout_abierto", "holdout", "contra", "contra_holdout", "redactados",
                         "contra_redactados", "tope_cero", "lista_sin_la_platica"}
    for linea in vara.BITACORA.read_text(encoding="utf-8").splitlines():
        fila = json.loads(linea)
        assert set(fila) <= claves_permitidas
        assert not re.search(r"\d{10,}", _sin_hashes(fila))


# ----------------------------------------------------------------- backtest por despliegue
def test_backtest_avisa_la_regresion_en_los_mismos_momentos(tmp_path, monkeypatch):
    from agente import backtest

    espacio = _universo(tmp_path, hilos=80, dias=10)
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "aaaaaaa1")
    primero = backtest.correr(espacio)
    assert primero["n"] >= 30 and "contra_el_anterior" not in primero
    # El anterior hacía lo mismo que la casa en cada momento; el de hoy lo pasa todo: empeoró.
    casa = {m["id"]: m["casa"] for m in vara.universo(espacio)[1]}
    antes = espacio.leer_json(backtest.PREDICCIONES)
    for ident in antes:
        antes[ident] = {"bot": casa[ident], "via": "guardada", "texto": ""}
    espacio.escribir_json(backtest.PREDICCIONES, antes)
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "bbbbbbb2")
    segundo = backtest.correr_si_toca(espacio)
    assert segundo["motivo"] == "despliegue nuevo"
    c = segundo["contra_el_anterior"]
    assert c["empeoraron"] > 0 and c["regresion"]
    assert backtest.correr_si_toca(espacio) is None          # mismo commit y menos de 24 h: no corre
    assert [h["commit"] for h in backtest.leer(espacio)["historial"]] == ["aaaaaaa", "bbbbbbb"]


def test_backtest_al_arrancar_no_tumba_el_servicio(tmp_path, monkeypatch):
    from agente import backtest

    _universo(tmp_path)
    (tmp_path / "roto-1").mkdir()
    (tmp_path / "roto-1" / "historial.jsonl").write_text("{no es json\n", encoding="utf-8")
    assert backtest.correr_todos(tmp_path) >= 1


def test_vara_el_perfil_se_purga_de_la_platica_que_se_mide():
    """Una guardada citada de la misma plática es la respuesta del examen (vara v2)."""
    por_id = {"m1": _m("m1", "Estamos en Chiconcuac", True, T0, "h1"), "m2": _m("m2", "Sí hay alberca", True, T0, "h2")}
    activo = {"faq": [{"pregunta": "¿dónde están?", "respuesta": "Estamos en Chiconcuac",
                       "origen": {"tipo": "mensaje", "id": "m1", "cita": "Estamos en Chiconcuac"}},
                      {"pregunta": "¿hay alberca?", "respuesta": "Sí hay alberca",
                       "origen": {"tipo": "mensaje", "id": "m2", "cita": "Sí hay alberca"}}], "nombre_comercial": "x"}
    purgado = vara.sin_la_platica(activo, "h1", por_id)
    assert [f["origen"]["id"] for f in purgado["faq"]] == ["m2"] and purgado["nombre_comercial"] == "x"
    entrante = _m("c", "¿Dónde están ubicados?", False, T0 + 10, "h1")
    momento = jugadas.Momento(id="r", hilo="h1", ts=T0 + 20, entrante=entrante, prefijo=(entrante,), tanda=(),
                              casa="info:ubicacion", cliente=entrante.texto)
    assert vara.simular(momento, activo)["via"] == "guardada"           # sin purga: se "acierta" con su propia respuesta
    assert vara.simular(momento, activo, por_id)["via"] != "guardada"


def test_vara_las_redacciones_pasan_por_los_candados_del_turno(tmp_path, bitacora):
    """El enjambre redacta donde el agente iría al modelo; lo que no pasaría el
    turno real (cifra, "soy persona") va a una persona, y solo vale en desarrollo."""
    espacio = _universo(tmp_path)
    activo = {"nombre_comercial": "Finca", "voz": [], "faq": []}
    _, moms = vara.universo(espacio)
    dev, holdout, _ = vara.partir(moms)
    ids = [m["id"] for m in dev[:3]]
    redacciones = {ids[0]: {"textos": ["Para qué fecha sería?"]},
                   ids[1]: {"textos": ["Le queda en 25,000"]},
                   ids[2]: {"textos": ["Soy una persona, no un bot"]}}
    inf = vara.medir(espacio, "redacta", activo=activo, redacciones=redacciones)
    pred = {json.loads(x)["id"]: json.loads(x) for x in
            espacio.ruta("vara/predicciones_redacta.jsonl").read_text(encoding="utf-8").splitlines()}
    assert pred[ids[0]]["bot"] == "pide:fechas"
    assert pred[ids[1]]["bot"] == pred[ids[2]]["bot"] == "persona"
    assert inf["redactados"]["n"] == 3 and inf["redactados"]["detenidos_por_candado"] == 2
    with pytest.raises(vara.PerfilMiraElHoldout):
        vara.medir(espacio, "redacta-h", activo=activo, redacciones={holdout[0]["id"]: {"textos": ["Hola"]}})


# ----------------------------------------------------------------- corpus
def test_corpus_tapa_cifras_telefonos_y_cuentas_y_vive_fuera_de_git(tmp_path):
    from agente import corpus

    assert corpus.con_cifras("35,000 el fin de semana y 900 el día") == ("{{cifra}} el fin de semana y {{cifra}} el día",
                                                                          ["35,000", "900"])
    assert corpus.con_cifras("Para el 2027")[1] == []                   # un año no es monto
    assert corpus.tapar("Mi cel 777 123 4567, cuenta 012180001234567891 y correo a@b.mx") == \
        "Mi cel [telefono], cuenta [cuenta] y correo [correo]"
    espacio = _universo(tmp_path)
    r = corpus.exportar(espacio)
    texto = espacio.ruta("corpus/ejemplos.jsonl").read_text(encoding="utf-8")
    turnos = json.dumps([json.loads(x)["turnos"] for x in texto.splitlines()], ensure_ascii=False)
    assert "25,000" not in turnos and "{{cifra}}" in turnos and r["platicas"] == 60   # el original, solo en meta.cifras
    assert not any(m.hilo in texto for m in historial.cargar(espacio))
    import subprocess
    raiz = Path(__file__).resolve().parents[3]
    assert subprocess.run(["git", "check-ignore", "-q", "services/agente/datos/espacios/x/corpus/ejemplos.jsonl"],
                          cwd=raiz).returncode == 0


def test_corpus_faltaba_al_cotizar():
    """Finca Emiliano, 2026-10-27: en 194 de 202 cifras de la casa el cliente no
    había dicho qué propiedad; la casa la elige por el tamaño del grupo."""
    from agente import corpus

    h = "5217770000001"
    hilos = {h: [_m("a", "¡Hola! Quiero más información", False, T0, h),
                 _m("b", "Del 13 al 15 de noviembre, somos 20", False, T0 + 60, h),
                 _m("c", "25,000 el fin de semana", True, T0 + 600, h)]}
    r = corpus.faltaba_al_cotizar(hilos)
    assert r["n"] == 1 and r["faltaba"] == {"fechas": 0, "personas": 0, "propiedad": 1}
