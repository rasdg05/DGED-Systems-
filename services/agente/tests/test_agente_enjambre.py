"""El enjambre local (D-027): pendientes con una sola vara, rondas con candados y taller por HTTP."""
from __future__ import annotations

import pytest
from agente import agente, canal, historial, pendientes, rondas
from agente.espacio import Espacio
from agente.historial import Mensaje
from fastapi.testclient import TestClient

HILO = "5210000007777"
MAESTRA = {"llave": "secreto-de-prueba"}


def _m(ident: str, texto: str | None, del_negocio: bool = False, ts: int = 1790000000, hilo: str = HILO,
       tipo: str = "text") -> Mensaje:
    return Mensaje(id=ident, hilo=hilo, del_negocio=del_negocio, ts=ts, tipo=tipo, texto=texto)


@pytest.fixture()
def con_pendiente(espacio):
    historial.guardar(espacio, [
        _m("wamid.E1", "Hola, ¿tienen la quinta libre en noviembre?", ts=1790000000),
        _m("wamid.E2", "Claro, ¿para qué fechas y cuántas personas?", True, ts=1790000100),
        _m("wamid.E3", "Del 9 al 11 de noviembre, somos ocho. ¿Cuánto sería?", ts=1790000200),
    ])
    return espacio


def _ronda(**entrada) -> dict:
    base = {"hilo": HILO, "ultimo_id": "wamid.E3", "resumen": "quinta, noviembre, 8 personas",
            "textos": ["Con gusto, le comparto la cotización."]}
    return {"nombre": "prueba-1", "orden": "dueño, prueba: «atiende los pendientes»", "entradas": [dict(base, **entrada)]}


# ----------------------------------------------------------------- pendientes
def test_pendientes_una_sola_vara_para_acuses_reclamos_y_medios(espacio):
    historial.guardar(espacio, [
        _m("a1", "precio?", hilo="5211"), _m("a2", "son 5 mil", True, ts=1790000010, hilo="5211"),
        _m("a3", "ok gracias, lo platico y le aviso", ts=1790000020, hilo="5211"),
        _m("b1", "Exijo mi reembolso, me deben mi dinero", hilo="5212"),
        _m("c1", None, hilo="5213", tipo="imagen"),
        _m("d1", "¿Aceptan mascotas?", hilo="5214"),
    ])
    por_hilo = {p.hilo: p.estado for p in pendientes.leer(historial.hilos(espacio))}
    assert (por_hilo["5211"], por_hilo["5212"], por_hilo["5213"], por_hilo["5214"]) == \
        ("no_pide", "reclamo", "solo_medios", "espera")


def test_pendientes_una_plantilla_no_es_una_persona(espacio):
    saludo = "Gracias por comunicarte. ¿Qué fechas?"
    mensajes = []
    for i in range(pendientes.USOS_DE_PLANTILLA):
        h = f"53{i:03d}"
        mensajes += [_m(f"p{i}", "Info", hilo=h), _m(f"q{i}", saludo, True, ts=1790000001, hilo=h),
                     _m(f"r{i}", "¿Precio para 10?", ts=1790000002, hilo=h)]
    historial.guardar(espacio, mensajes)
    lista = [p for p in pendientes.leer(historial.hilos(espacio)) if p.hilo.startswith("53")]
    assert len(lista) == pendientes.USOS_DE_PLANTILLA and not any(p.hubo_persona for p in lista)
    assert pendientes.resumen(lista)["espera_sin_persona_nunca"] == pendientes.USOS_DE_PLANTILLA


# ----------------------------------------------------------------- invariantes de la ronda
def test_inv_ronda_si_la_platica_se_movio_no_sale(con_pendiente, monkeypatch):
    """Gestor `COLA_CAMBIADA`: al cargar y otra vez al enviar."""
    aceptadas, descartadas = rondas.validar(con_pendiente, _ronda(ultimo_id="wamid.E1"))
    assert not aceptadas and descartadas[0]["motivo"] == rondas.SE_MOVIO
    salidas, _ = rondas.cargar(con_pendiente, _ronda())
    historial.guardar(con_pendiente, [_m("wamid.E4", "¿Sigue ahí?", ts=1790000300)])
    assert canal.motivo_para_no_enviar(con_pendiente, salidas[0]) != ""
    agente.aprobar_salida(con_pendiente, salidas[0].id, "Dueña de muestra")
    canal_listo = dict(con_pendiente.config(), phone_number_id="123", encendido="sin_cifra")
    con_pendiente.escribir_json("config.json", canal_listo)
    monkeypatch.setenv("WHATSAPP_TOKEN", "t")
    assert canal.motivo_para_no_enviar(con_pendiente, salidas[0]) == rondas.SE_MOVIO


def test_inv_ronda_ninguna_cifra_en_el_texto_del_enjambre(con_pendiente):
    for texto in ("Le queda en $7,000 la noche.", "Se la dejo en seis mil.", "Son 7000 pesos."):
        _, descartadas = rondas.validar(con_pendiente, _ronda(textos=[texto]))
        assert descartadas and "cifra" in descartadas[0]["motivo"], texto


VACIO = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n"
RESERVA_QUINTA = ("BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nDTSTART;VALUE=DATE:20261109\n"
                  "DTEND;VALUE=DATE:20261111\nSUMMARY:Reserved\nEND:VEVENT\nEND:VCALENDAR\n")


def _calendario(espacio, ics=VACIO):
    from agente import calendario
    calendario.agregar_fuente(espacio, "quinta", "google", "https://ejemplo.test/quinta.ics")
    calendario.bajar(espacio, lambda _url: ics)


def test_inv_ronda_la_cifra_la_pone_el_cotizador_y_espera_aprobacion(con_pendiente):
    _calendario(con_pendiente)
    pedido = {"propiedad": "quinta", "llegada": "2026-11-09", "salida": "2026-11-11", "personas": 8}
    salidas, descartadas = rondas.cargar(con_pendiente, _ronda(cotizacion=pedido))
    assert not descartadas and len(salidas) == 1
    s = salidas[0]
    assert s.via == "ronda" and s.requiere_aprobacion and s.cotizacion["total"]
    assert s.texto.endswith(s.cotizacion["texto"])
    assert canal.motivo_para_no_enviar(con_pendiente, s) != ""  # sin aprobación ni conector
    from agente import sombra
    assert not sombra.error_de_cifra(s)


def test_inv_ronda_no_contesta_reclamos_ni_acuses_y_no_se_carga_dos_veces(con_pendiente):
    historial.guardar(con_pendiente, [_m("x1", "Quiero mi reembolso, es un fraude", hilo="5299")])
    _, descartadas = rondas.validar(con_pendiente, _ronda(hilo="5299", ultimo_id="x1"))
    assert "reclamo" in descartadas[0]["motivo"]
    rondas.cargar(con_pendiente, _ronda())
    with pytest.raises(rondas.RondaInvalida):
        rondas.cargar(con_pendiente, _ronda())


def test_inv_ronda_no_le_escribe_dos_veces_al_mismo_mensaje(con_pendiente, monkeypatch):
    """Lo enviado por el vinculado no vuelve al historial: la plática sigue "sin
    contestar" y sin este candado el enjambre del día siguiente le volvía a escribir."""
    from agente import local
    rondas.cargar(con_pendiente, _ronda())
    otra = dict(_ronda(), nombre="prueba-2")
    _, descartadas = rondas.validar(con_pendiente, otra)
    assert "ya tiene una salida" in descartadas[0]["motivo"]
    monkeypatch.setattr(local, "_espacio", lambda _id: con_pendiente)
    _, escritos = local.lotes(con_pendiente.cliente_id, dias=100_000)
    assert not any(HILO in r.read_text(encoding="utf-8") for r in escritos)
    historial.guardar(con_pendiente, [_m("wamid.E4", "¿Siguen teniendo la quinta?", ts=1790000300)])
    aceptadas, _ = rondas.validar(con_pendiente, dict(otra, entradas=[dict(otra["entradas"][0], ultimo_id="wamid.E4")]))
    assert len(aceptadas) == 1  # el cliente volvió a escribir: ese mensaje nuevo sí se contesta


def test_inv_ronda_sin_perfil_no_hay_cotizacion(tmp_path, monkeypatch):
    monkeypatch.setenv("TENANT_INTERNAL_TOKEN", "s")
    vacio = Espacio("sin-perfil", tmp_path)
    historial.guardar(vacio, [_m("wamid.E3", "¿Cuánto por dos noches?")])
    pedido = {"propiedad": "quinta", "llegada": "2026-11-09", "salida": "2026-11-11", "personas": 8}
    _, descartadas = rondas.validar(vacio, _ronda(cotizacion=pedido))
    assert "perfil aprobado" in descartadas[0]["motivo"]
    aceptadas, _ = rondas.validar(vacio, _ronda())  # sin cifra sí puede
    assert len(aceptadas) == 1


# ----------------------------------------------------------------- taller por HTTP
def test_taller_espejo_pendientes_ronda_y_propuesta_solo_con_la_maestra(con_pendiente):
    from agente.app import app
    from agente.espacio import llave_de
    http, base = TestClient(app), f"/espacios/{con_pendiente.cliente_id}"
    cliente = {"llave": llave_de(con_pendiente.cliente_id)}
    for metodo, ruta in (("get", "espejo.json"), ("get", "pendientes.json"), ("post", "rondas"), ("post", "propuestas")):
        r = getattr(http, metodo)(f"{base}/{ruta}", params=cliente, **({"json": {}} if metodo == "post" else {}))
        assert r.status_code == 404, ruta
    assert http.get(f"{base}/espejo.json", params=MAESTRA).json()["activa"] == 1
    assert http.get(f"{base}/pendientes.json", params=MAESTRA).json()["resumen"]["espera"] >= 1
    probada = http.post(f"{base}/rondas", params=MAESTRA, json=_ronda()).json()
    assert probada == {"probada": True, "aceptadas": 1, "descartadas": []}
    assert not con_pendiente.ruta("rondas/prueba-1.json").exists()  # probar no escribe
    cargada = http.post(f"{base}/rondas", params=dict(MAESTRA, probar="false"), json=_ronda()).json()
    assert len(cargada["esperan_aprobacion"]) == 1
    r = http.post(f"{base}/propuestas", params=MAESTRA, json={"nombre": "enjambre", "perfil": {
        "voz": [{"frase": "inventada", "origen": {"tipo": "mensaje", "id": "no-existe", "cita": "inventada"}}]}})
    assert r.status_code == 200 and r.json()["version"] == 2 and r.json()["descartados"]


# ----------------------------------------------------------------- copia local
def test_local_bajar_deja_tope_cero_y_sombra_y_lotes_solo_con_espera(con_pendiente, tmp_path, monkeypatch):
    import json

    from agente import gasto, local
    crudo = con_pendiente.ruta(historial.ARCHIVO).read_bytes()
    espejo = {"alta": con_pendiente.leer_json("alta.json"), "activa": 1,
              "versiones": {"1": perfil_v1(con_pendiente)}, "salidas": [], "aprobaciones_salida": []}
    respuestas = {"/espacios/muestra-vacacional/historial.jsonl": crudo,
                  "/espacios/muestra-vacacional/espejo.json": json.dumps(espejo).encode()}
    monkeypatch.setattr(local, "_pedir", lambda metodo, ruta, *a, **k: respuestas[ruta])
    monkeypatch.setenv("AGENTE_DATOS_LOCAL", str(tmp_path / "copia"))
    monkeypatch.setenv("TENANT_INTERNAL_TOKEN", "x")
    hecho = local.bajar("muestra-vacacional")
    copia = local._espacio("muestra-vacacional")
    assert hecho["mensajes"] == len(historial.cargar(con_pendiente)) and hecho["activa"] == 1
    assert copia.config()["encendido"] == "sombra" and not gasto.puede_gastar(copia)
    with pytest.raises(gasto.TopeAlcanzado):
        gasto.exigir_saldo(copia)
    resumen, escritos = local.lotes("muestra-vacacional", por_lote=1, dias=100_000)
    platicas = [p for r in escritos for p in json.loads(r.read_text(encoding="utf-8"))["platicas"]]
    assert len(platicas) == resumen["espera"] and all(p["tipo"] == "contestar" for p in platicas)
    assert any(p["ultimo_id"] == "wamid.E3" for p in platicas)


def perfil_v1(espacio) -> dict:
    from agente import perfil
    return perfil.leer_version(espacio, 1)


def test_inv_ronda_no_vende_fechas_que_el_calendario_no_da_por_libres(con_pendiente):
    """LXIII: sin calendario, ocupada o sin saber, la ronda no lleva esa cotización."""
    pedido = {"propiedad": "quinta", "llegada": "2026-11-09", "salida": "2026-11-11", "personas": 8}
    _, descartadas = rondas.validar(con_pendiente, _ronda(cotizacion=pedido))
    assert "sin calendario" in descartadas[0]["motivo"]
    _calendario(con_pendiente, RESERVA_QUINTA)
    _, descartadas = rondas.validar(con_pendiente, _ronda(cotizacion=pedido))
    assert "ocupada" in descartadas[0]["motivo"]
    _calendario(con_pendiente, "<html>login</html>")  # el iCal dejó de responder: no se sabe
    _, descartadas = rondas.validar(con_pendiente, _ronda(cotizacion=pedido))
    assert "ocupada" in descartadas[0]["motivo"]  # lo ocupado de antes sigue ocupado
    # el seguimiento sin fechas sí sale
    aceptadas, _ = rondas.validar(con_pendiente, _ronda())
    assert aceptadas


def test_inv_si_se_aparto_despues_de_aprobar_no_se_envia(con_pendiente, monkeypatch):
    """LXIII al enviar: otra plataforma vendió esas noches entre la ronda y el sí."""
    _calendario(con_pendiente)
    pedido = {"propiedad": "quinta", "llegada": "2026-11-09", "salida": "2026-11-11", "personas": 8}
    salidas, _ = rondas.cargar(con_pendiente, _ronda(cotizacion=pedido))
    agente.aprobar_salida(con_pendiente, salidas[0].id, "Dueña de muestra")
    con_pendiente.escribir_json("config.json", dict(con_pendiente.config(), phone_number_id="123", encendido="sin_cifra"))
    monkeypatch.setenv("WHATSAPP_TOKEN", "t")
    assert "apartadas" not in canal.motivo_para_no_enviar(con_pendiente, salidas[0])
    _calendario(con_pendiente, RESERVA_QUINTA)
    assert "apartadas" in canal.motivo_para_no_enviar(con_pendiente, salidas[0])


def test_ronda_de_seguimiento_solo_lo_que_el_semaforo_marca(espacio):
    """D-041: lo cotizado sin respuesta de 24 h a 21 días sí; recién cotizado o frío, no."""
    import time
    ahora = int(time.time())
    historial.guardar(espacio, [
        _m("s1", "Precio para 20?", hilo="5301", ts=ahora - 3 * 86400),
        _m("s2", "Son 22,000 el fin de semana", True, hilo="5301", ts=ahora - 3 * 86400 + 60),
        _m("r1", "Precio para 20?", hilo="5302", ts=ahora - 3600),
        _m("r2", "Son 22,000 el fin de semana", True, hilo="5302", ts=ahora - 3500),
        _m("f1", "Precio para 20?", hilo="5303", ts=ahora - 40 * 86400),
        _m("f2", "Son 22,000 el fin de semana", True, hilo="5303", ts=ahora - 40 * 86400 + 60),
    ])
    texto = ["Buenas tardes, pudo revisar la información?"]
    ronda = {"nombre": "seg-1", "orden": "dueño, prueba", "entradas": [
        {"hilo": "5301", "ultimo_id": "s2", "textos": texto}, {"hilo": "5302", "ultimo_id": "r2", "textos": texto},
        {"hilo": "5303", "ultimo_id": "f2", "textos": texto}]}
    aceptadas, descartadas = rondas.validar(espacio, ronda)
    assert [a["hilo"] for a in aceptadas] == ["5301"]
    assert {d["hilo"] for d in descartadas} == {"5302", "5303"}


def test_inv_ronda_no_pregunta_lo_que_el_cliente_ya_dijo(espacio):
    """Gestor C5-I. Corrida GM, 2026-10-29: una ronda aprobada preguntó "Para cuántas personas
    sería" a quien había dicho 150; la casa lo hace en 15 de 43 de sus "¿cuántas personas?"."""
    h = "5210000008888"
    historial.guardar(espacio, [
        _m("p1", "25 personas del 28 al 30 de noviembre", ts=1790000000, hilo=h),
        _m("p2", "Le comparto la información de la finca", True, ts=1790000100, hilo=h),
        _m("p3", "¿Y si hay alberca?", ts=1790000200, hilo=h),
    ])
    ronda = {"nombre": "prueba-2", "orden": "dueño, prueba", "entradas": [
        {"hilo": h, "ultimo_id": "p3", "resumen": "x", "textos": ["Sí tenemos alberca. Para cuántas personas sería?"]}]}
    _, descartadas = rondas.validar(espacio, ronda)
    assert descartadas and descartadas[0]["motivo"] == "pregunta lo que el cliente ya dijo: personas (25)"
    ronda["entradas"][0]["textos"] = ["Sí tenemos alberca. Qué fecha les interesa más?"]
    _, descartadas = rondas.validar(espacio, ronda)
    assert descartadas and descartadas[0]["motivo"].startswith("pregunta lo que el cliente ya dijo: fechas")
    ronda["entradas"][0]["textos"] = ["Sí tenemos alberca climatizada."]
    aceptadas, descartadas = rondas.validar(espacio, ronda)
    assert aceptadas and not descartadas


def test_ronda_pedir_otra_fecha_cuando_la_suya_ya_paso_no_es_repetir():
    from datetime import datetime
    viejo = int(datetime(2026, 10, 1, 12).timestamp())
    ms = [_m("a", "Para el 10 de octubre, somos 6 personas", ts=viejo),
          _m("b", "Ya tenemos ocupado esa fecha", True, ts=viejo + 60),
          _m("c", "Ok", ts=int(datetime(2026, 10, 27, 12).timestamp()))]
    assert rondas.pregunta_lo_ya_dicho(ms, "Sigue buscando? Para qué fecha sería ahora?") == ""
    assert rondas.pregunta_lo_ya_dicho(ms, "Para cuántas personas sería?") == "personas (6)"


@pytest.mark.parametrize("texto", [
    "Siguen interesados en sus fechas de enero? Con gusto se las aparto.",
    "Hola, seguimos a tus órdenes, te gustaría apartar la quinta para tus fechas?",
])
def test_ronda_confirmar_sus_fechas_no_es_preguntarlas(texto):
    """Falsos positivos al pasar el candado por las 138 rondas enviadas (corrida GM)."""
    ms = [_m("a", "Del 28 al 30 de diciembre, somos 6 personas", ts=1790000000)]
    assert rondas.pregunta_lo_ya_dicho(ms, texto) == ""
    assert rondas.pregunta_lo_ya_dicho(ms, "Nos comparte sus fechas para apartar?").startswith("fechas")


def test_ronda_pedir_otra_fecha_tras_un_ocupado_no_es_repetir():
    ms = [_m("a", "Del 28 al 30 de diciembre, somos 6 personas", ts=1790000000),
          _m("b", "Ya tenemos reservado, una disculpa", True, ts=1790000060)]
    assert rondas.pregunta_lo_ya_dicho(ms, "Sigue buscando? Si me dice qué fechas le paso la información.") == ""
