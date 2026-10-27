"""Las ocho invariantes de `docs/15-agente-a-la-medida.md`, una por test (o familia).

Suben a `MEMORY/CONSTITUCION.md` con el nombre de su test. Todas corren sin red
ni clave: el modelo es falso, el canal es falso.
"""
from __future__ import annotations

import json

import pytest
from agente import agente, canal, gasto, modelo, perfil, sombra
from agente.espacio import Espacio, EspacioInvalido, llave_de, llave_valida
from agente.mcp import HERRAMIENTAS, Servidor
from conftest import ModeloFalso, entrante, leer_muestra, montar

META_NADA = "[[META cotizar=no persona=no dificil=no]]"


def _cotiza(texto="Con gusto, le paso el precio.", propiedad="finca", llegada="2026-11-13",
            salida="2026-11-15", personas="25", evento="si"):
    return (f"{texto} [[META cotizar=si propiedad={propiedad} llegada={llegada} salida={salida} "
            f"personas={personas} evento={evento} persona=no dificil=no]]")


# 1 — Ninguna cifra sale si no la produjo el cotizador de ese cliente.
@pytest.mark.parametrize("borrador", [
    "La finca le sale en 9000 la noche.",
    "Son $8,500 por noche.",
    "Le queda en 6 mil más o menos.",
    "Para el 14 de noviembre sí hay lugar.",
])
def test_inv1_cifra_del_modelo_no_sale(espacio, borrador):
    salida = agente.decidir(espacio, entrante("Cuánto cuesta la finca?"), ModeloFalso(f"{borrador} {META_NADA}"))
    assert salida.via == "persona"
    assert salida.texto == agente.LO_CONFIRMO and borrador in salida.borrador
    assert "cifra" in salida.motivo


def test_inv1_la_cotizacion_solo_trae_cifras_del_cotizador(espacio):
    salida = agente.decidir(espacio, entrante("Precio de la finca 13 al 15 de nov, 25 personas, con evento"),
                            ModeloFalso(_cotiza()))
    assert salida.via == "cotizador"
    # Viernes 13 y sábado 14 de noviembre de 2026: dos noches de fin de semana,
    # 5 personas extra por noche y el evento. Las tarifas son de la muestra ficticia.
    assert salida.cotizacion["total"] == 2 * 850000 + 2 * 5 * 25000 + 500000
    assert "$24,500" in salida.texto
    assert not sombra.error_de_cifra(salida)


def test_inv1_respuesta_guardada_con_monto_no_se_usa(espacio):
    activo = perfil.activo(espacio)
    activo["faq"].append({"pregunta": "Cuánto cuesta la quinta?", "respuesta": "La quinta sale en $3,500.",
                          "origen": {}})
    from agente import respuestas
    assert respuestas.buscar(activo, "cuánto cuesta la quinta") is None


# 2 — Ninguna cotización sale sin aprobación de una persona.
def test_inv2_cotizacion_no_sale_sin_aprobacion(espacio, monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "token-de-prueba")
    config = espacio.config()
    config.update(phone_number_id="100000000000001", encendido="sin_cifra")
    espacio.escribir_json("config.json", config)
    enviados = []
    salida = agente.atender(espacio, entrante("Precio de la finca"), ModeloFalso(_cotiza()))
    assert salida.requiere_aprobacion
    with pytest.raises(canal.EnvioNoPermitido, match="aprobación"):
        canal.enviar(espacio, salida, transporte=lambda url, cuerpo: enviados.append(cuerpo))
    assert enviados == []
    with pytest.raises(perfil.AprobacionInvalida):
        agente.aprobar_salida(espacio, salida.id, "alguien que no está en el alta")
    agente.aprobar_salida(espacio, salida.id, "Encargado de muestra")
    canal.enviar(espacio, salida, transporte=lambda url, cuerpo: enviados.append(cuerpo) or {"ok": 1})
    assert len(enviados) == 1 and "$24,500" in enviados[0]["text"]["body"]


# 3 — Ningún dato del perfil existe sin el mensaje o documento de donde salió.
def test_inv3_todo_renglon_activo_prueba_su_origen(espacio):
    activo = perfil.activo(espacio)
    mensajes = {m.id: m for m in __import__("agente.historial", fromlist=["x"]).cargar(espacio)}
    for seccion in perfil.SECCIONES:
        for renglon in activo[seccion]:
            assert perfil.motivo_de_rechazo(espacio, seccion, renglon, mensajes) == ""


def test_inv3_los_renglones_malos_de_la_muestra_caen(espacio):
    v = perfil.leer_version(espacio, perfil.version_activa(espacio))
    motivos = sorted(d["motivo"] for d in v["descartados"])
    assert len(motivos) == 2
    assert any("cifra que no está en la cita" in m for m in motivos)
    assert any("cliente final" in m for m in motivos)


@pytest.mark.parametrize("origen, motivo", [
    (None, "sin origen"),
    ({"tipo": "mensaje", "id": "wamid.NOEXISTE", "cita": "hola"}, "no existe"),
    ({"tipo": "mensaje", "id": "wamid.MUESTRA0103", "cita": "la noche cuesta 6000"}, "no está literal"),
    ({"tipo": "documento", "nombre": "../../fuera.txt", "cita": "x"}, "fuera del espacio"),
])
def test_inv3_origen_que_no_se_prueba_no_entra(espacio, origen, motivo):
    renglon = {"frase": "algo", **({"origen": origen} if origen else {})}
    limpio, descartados = perfil.validar(espacio, {"voz": [renglon]})
    assert limpio["voz"] == [] and motivo in descartados[0]["motivo"]


# 4 — Los datos de un cliente nunca aparecen en el contexto, la caché ni las herramientas de otro.
def test_inv4_el_contexto_es_solo_del_espacio(tmp_path, monkeypatch):
    monkeypatch.setenv("TENANT_INTERNAL_TOKEN", "secreto")
    a = montar(tmp_path, "negocio-a")
    b = Espacio("negocio-b", tmp_path)
    from agente import alta, historial
    alta.registrar(b, dict(leer_muestra("alta.json"), nombre_comercial="Otro negocio",
                           aprobador="Dueño B", giro="taller"))
    historial.guardar(b, [historial.Mensaje("wamid.B1", "5219999999999", True, 1, "text",
                                            "Afinación completa en $1,234 pesos")])
    n, _ = perfil.proponer(b, {"reglas": [{"propiedad": "afinacion", "tipo": "evento", "monto_centavos": 123400,
                                           "origen": {"tipo": "mensaje", "id": "wamid.B1",
                                                      "cita": "Afinación completa en $1,234"}}],
                               "voz": [{"frase": "Afinación completa", "origen": {
                                   "tipo": "mensaje", "id": "wamid.B1", "cita": "Afinación completa"}}]},
                            autor="t", nombre="b")
    perfil.aprobar(b, n, aprobador="Dueño B")
    falso = ModeloFalso("Claro. " + META_NADA)
    agente.decidir(a, entrante("Qué incluye la finca?"), falso)
    pedido = json.dumps(falso.llamadas[0], ensure_ascii=False, default=str)
    assert "negocio-a" in pedido and "Afinación" not in pedido and "negocio-b" not in pedido
    assert falso.llamadas[0]["system"][-1]["cache_control"] == {"type": "ephemeral"}
    # Un perfil de B no puede citar un mensaje de A.
    _, descartados = perfil.validar(b, {"voz": [{"frase": "x", "origen": {
        "tipo": "mensaje", "id": "wamid.MUESTRA0101", "cita": "Buenas tardes"}}]})
    assert "no existe" in descartados[0]["motivo"]
    # La llave de A no abre B, y sin secreto no abre nada.
    assert llave_valida("negocio-a", llave_de("negocio-a"))
    assert not llave_valida("negocio-b", llave_de("negocio-a"))
    monkeypatch.setenv("TENANT_INTERNAL_TOKEN", "")
    assert not llave_valida("negocio-a", llave_de("negocio-a", "secreto"))
    # Las herramientas del MCP no reciben id de cliente.
    for h in HERRAMIENTAS:
        assert not set(h["inputSchema"].get("properties", {})) & {"cliente", "cliente_id", "espacio"}
    with pytest.raises(EspacioInvalido):
        a.ruta("../negocio-b/alta.json")


# 5 — Al llegar al tope de gasto, cero llamadas a la API para ese cliente.
def test_inv5_al_tope_cero_llamadas(espacio):
    config = espacio.config()
    config["tope_usd_mes"] = 0.0001
    espacio.escribir_json("config.json", config)
    falso = ModeloFalso(*(["Claro. " + META_NADA] * 10))
    primera = agente.decidir(espacio, entrante("Qué incluye la finca?", ident="wamid.T1"), falso)
    assert primera.via == "modelo" and len(falso.llamadas) == 1
    assert gasto.gastado_usd(espacio) >= 0.0001
    for i in range(5):
        s = agente.decidir(espacio, entrante("Y la quinta qué incluye?", ident=f"wamid.T{i + 2}"), falso)
        assert s.via == "persona" and "tope" in s.motivo
    assert len(falso.llamadas) == 1


def test_inv5_sin_tope_configurado_no_se_gasta(tmp_path, monkeypatch):
    monkeypatch.setenv("TENANT_TOPE_USD_MES", "")
    espacio = montar(tmp_path, tope=None)
    falso = ModeloFalso("Claro. " + META_NADA)
    assert agente.decidir(espacio, entrante("Qué incluye la finca?"), falso).via == "persona"
    assert falso.llamadas == []


# 6 — Un cambio propuesto por un agente de código no toca producción hasta que se aprueba.
def test_inv6_el_mcp_propone_y_no_enciende(espacio):
    antes = perfil.version_activa(espacio)
    activo_antes = perfil.activo(espacio)
    servidor = Servidor(espacio)
    nombres = {h["name"] for h in HERRAMIENTAS}
    assert "proponer_cambio" in nombres and not any("aprob" in n or "activ" in n for n in nombres)
    r = servidor.atender({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "proponer_cambio", "arguments": {"nombre": "voz más corta", "motivo": "prueba",
                                                 "quitar": {"voz": [0]}}}})
    nueva = json.loads(r["result"]["content"][0]["text"])["version"]
    assert nueva == antes + 1
    assert perfil.version_activa(espacio) == antes and perfil.activo(espacio) == activo_antes
    perfil.aprobar(espacio, nueva, aprobador="Dueña de muestra")
    assert perfil.version_activa(espacio) == nueva
    assert perfil.leer_version(espacio, antes)["perfil"] == activo_antes  # la anterior se conserva
    with pytest.raises(perfil.AprobacionInvalida):
        perfil.aprobar(espacio, antes, aprobador="agente de código (MCP)")


# 7 — Sin conector oficial configurado, el agente no envía nada.
def test_inv7_sin_conector_oficial_no_se_envia(espacio, monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "")
    config = espacio.config()
    config.update(encendido="sin_cifra", phone_number_id="100000000000001")
    espacio.escribir_json("config.json", config)
    salida = agente.decidir(espacio, entrante("Cuál es el horario de entrada?"))
    assert salida.via == "guardada"
    with pytest.raises(canal.CanalDormido, match="sin conector oficial"):
        canal.enviar(espacio, salida, transporte=lambda *a: pytest.fail("no debió enviar"))


def test_inv7_sin_clave_el_agente_duerme_y_pasa_a_la_persona(espacio, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    salida = agente.decidir(espacio, entrante("Qué incluye la finca?"))
    assert salida.via == "persona" and "ANTHROPIC_API_KEY" in salida.motivo
    with pytest.raises(modelo.Dormido):
        modelo.cliente_real()


def test_inv7_en_sombra_nada_sale_aunque_haya_conector(espacio, monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "token")
    config = espacio.config()
    config["phone_number_id"] = "100000000000001"
    espacio.escribir_json("config.json", config)
    salida = agente.decidir(espacio, entrante("Cuál es el horario de entrada?"))
    assert "sombra" in canal.motivo_para_no_enviar(espacio, salida)


# 8 — Datos de los clientes finales solo en el espacio; se borran al terminar el contrato.
def test_inv8_todo_vive_en_el_espacio_y_se_borra(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    raiz = tmp_path / "espacios"
    espacio = montar(raiz, "se-va")
    agente.atender(espacio, entrante("Hola, mi correo es cliente@example.com"), ModeloFalso("Claro. " + META_NADA))
    sombra.medir(espacio)
    fuera = [p for p in tmp_path.rglob("*") if p.is_file() and espacio.carpeta not in p.parents]
    assert fuera == []
    assert any("cliente@example.com" in p.read_text(encoding="utf-8")
               for p in espacio.carpeta.rglob("*.jsonl"))
    espacio.borrar()
    assert not espacio.carpeta.exists()
    assert [p for p in raiz.rglob("*") if p.is_file()] == []


def test_inv8_la_raiz_de_espacios_no_va_a_git(monkeypatch):
    """Lo pregunta a git, no al texto del .gitignore: `datos/espacios/` solo tapaba la
    raíz del repo y el servidor arrancado desde services/agente escribe en
    services/agente/datos/espacios (lo destapó la copia local, 2026-10-27)."""
    import subprocess
    from pathlib import Path

    from agente.espacio import raiz_por_defecto
    from agente.local import RAIZ_LOCAL
    monkeypatch.delenv("AGENTE_DATOS", raising=False)
    repo = Path(__file__).resolve().parents[3]
    for raiz in (repo / raiz_por_defecto(), repo / "services" / "agente" / raiz_por_defecto(), RAIZ_LOCAL):
        archivo = raiz / "un-negocio" / "historial.jsonl"
        r = subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", "--no-index", str(archivo)])
        assert r.returncode == 0, f"{archivo} iría a git"
