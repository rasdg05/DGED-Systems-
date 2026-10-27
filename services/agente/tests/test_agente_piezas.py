"""Las piezas del agente, una por una: historial, cotizador, voz, gasto, sombra, simbiosis, MCP y servidor."""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import sys
from datetime import date
from types import SimpleNamespace

import pytest
from agente import agente, canal, cotizador, gasto, historial, mcp, modelo, perfil, respuestas, simbiosis, sombra, voz
from agente.espacio import Espacio, llave_de
from conftest import MUESTRA, ModeloFalso, entrante, leer_muestra, montar

sys.path.insert(0, str(MUESTRA))
from generar_muestra import CONVERSACIONES  # noqa: E402


# --------------------------------------------------------------------------- #
#  Historial (forma medida de los webhooks de coexistencia)                    #
# --------------------------------------------------------------------------- #
def test_historial_lee_hilos_y_quien_habla(espacio):
    mensajes = historial.cargar(espacio)
    assert len(mensajes) == sum(len(c) for c in CONVERSACIONES)
    primero = historial.por_id(espacio)["wamid.MUESTRA0101"]
    assert primero.del_negocio and primero.hilo == "5210000000001"
    assert historial.guardar(espacio, mensajes) == 0  # Meta reenvía porciones: no se duplica


def test_historial_medio_sin_contenido_y_eco_del_negocio():
    carga = {"entry": [{"changes": [
        {"field": "history", "value": {"metadata": {"display_phone_number": "521"}, "history": [{"threads": [
            {"id": "529", "messages": [{"from": "529", "id": "w1", "timestamp": "5", "type": "media_placeholder"}]}]}]}},
        {"field": "smb_message_echoes", "value": {"metadata": {"display_phone_number": "521"}, "message_echoes": [
            {"from": "521", "to": "529", "id": "w2", "timestamp": "6", "type": "text", "text": {"body": "Listo"}}]}},
        {"field": "messages", "value": {"metadata": {"display_phone_number": "521"}, "messages": [
            {"from": "529", "id": "w3", "timestamp": "x", "type": "image", "image": {"caption": "así quedó"}}]}},
    ]}]}
    m = {x.id: x for x in historial.de_webhook(carga)}
    assert m["w1"].texto is None and not m["w1"].del_negocio
    assert m["w2"].del_negocio and m["w2"].hilo == "529" and m["w2"].texto == "Listo"
    assert m["w3"].texto == "así quedó" and m["w3"].ts == 0



# --------------------------------------------------------------------------- #
#  Cotizador                                                                   #
# --------------------------------------------------------------------------- #
def test_cotizador_entre_semana_quinta(espacio):
    c = cotizador.cotizar(perfil.activo(espacio), "quinta", date(2026, 11, 9), date(2026, 11, 11), 8)
    assert c.completa and c.total == 2 * 350000 and c.anticipo == 350000
    assert c.texto() == ("Quinta, del 9 al 11 de noviembre de 2026 (2 noches, 8 personas): $7,000. "
                         "Anticipo de 50%: $3,500.")


@pytest.mark.parametrize("propiedad, llegada, salida, personas, falta", [
    ("quinta", date(2026, 11, 9), date(2026, 11, 10), 8, "mínimo de 2 noches"),
    ("quinta", date(2026, 11, 9), date(2026, 11, 11), 15, "capacidad de 12"),
    ("cabaña", date(2026, 11, 9), date(2026, 11, 11), 4, "tarifas de cabaña"),
    ("finca", date(2026, 11, 11), date(2026, 11, 9), 4, "fechas válidas"),
    # Viernes en temporada alta: la regla de temporada y la de fin de semana dan
    # montos distintos con la misma especificidad. No se adivina cuál manda.
    ("finca", date(2026, 12, 18), date(2026, 12, 20), 10, "dos reglas chocan"),
])
def test_cotizador_lo_que_falta_no_se_adivina(espacio, propiedad, llegada, salida, personas, falta):
    c = cotizador.cotizar(perfil.activo(espacio), propiedad, llegada, salida, personas)
    assert not c.completa and c.total is None and c.anticipo is None
    assert any(falta in f for f in c.faltan)
    assert "$" not in c.texto()


def test_cotizador_temporada_que_cruza_el_anio():
    temporadas = [{"nombre": "alta", "desde": "12-15", "hasta": "01-06"}]
    assert cotizador.temporada_de(date(2027, 1, 2), temporadas) == "alta"
    assert cotizador.temporada_de(date(2026, 12, 14), temporadas) is None
    reglas = {"reglas": [{"propiedad": "p", "tipo": "noche", "temporada": "alta", "monto_centavos": 100},
                         {"propiedad": "p", "tipo": "noche", "monto_centavos": 50}], "temporadas": temporadas}
    c = cotizador.cotizar(reglas, "p", date(2026, 12, 14), date(2026, 12, 16), 2)
    assert c.total == 150 and c.texto().endswith("$1.50.")


def test_cotizacion_incompleta_va_a_la_persona(espacio):
    s = agente.decidir(espacio, entrante("La quinta una noche"),
                       ModeloFalso("Con gusto. [[META cotizar=si propiedad=quinta llegada=2026-11-09 "
                                   "salida=2026-11-10 personas=4 evento=no persona=no dificil=no]]"))
    assert s.via == "persona" and "mínimo" in s.motivo and s.cotizacion["total"] is None


# --------------------------------------------------------------------------- #
#  Voz, respuestas guardadas y META                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("texto, rasgo", [
    ("¡Claro! Con gusto 🙌", "emoji"),
    ("Entiendo su situación, desafortunadamente no hay.", "chatbot"),
    ("**Incluye:**\n- alberca", "formato"),
    ("Claro, te mando la info", "tutea"),
])
def test_voz_ajena_va_a_la_persona(espacio, texto, rasgo):
    assert any(rasgo in h for h in voz.hallazgos(texto, perfil.activo(espacio)))
    s = agente.decidir(espacio, entrante("Qué incluye?"), ModeloFalso(texto + " [[META persona=no]]"))
    assert s.via == "persona" and "voz ajena" in s.motivo


def test_voz_del_negocio_pasa(espacio):
    activo = perfil.activo(espacio)
    for frase in activo["voz"]:
        assert voz.hallazgos(frase["frase"], activo) == []


def test_respuesta_guardada_no_llama_al_modelo(espacio):
    falso = ModeloFalso()
    s = agente.decidir(espacio, entrante("Oiga cual es el horario de entrada y salida?"), falso)
    assert s.via == "guardada" and "3 de la tarde" in s.texto and falso.llamadas == []
    assert respuestas.buscar(perfil.activo(espacio), "tienen estacionamiento techado?") is None


def test_meta_se_quita_y_se_lee():
    texto, meta = modelo.extraer_meta("Claro.\n[[META cotizar=si propiedad=finca personas=12 duda=si hay fecha libre]]")
    assert texto == "Claro." and meta["propiedad"] == "finca" and meta["duda"] == "si hay fecha libre"
    assert modelo.extraer_meta("Sin meta") == ("Sin meta", {})


def test_el_modelo_pide_persona_o_declina(espacio):
    s = agente.decidir(espacio, entrante("Quiero cancelar"), ModeloFalso("Lo reviso. [[META persona=si duda=cancelación]]"))
    assert s.via == "persona" and s.motivo == "cancelación"
    s = agente.decidir(espacio, entrante("algo"), ModeloFalso("", stop_reason="refusal"))
    assert s.via == "persona" and "declinó" in s.motivo


def test_dificil_sube_al_modelo_grande_una_vez(espacio):
    falso = ModeloFalso("Lo veo. [[META dificil=si]]", "Claro, la finca tiene alberca. [[META persona=no]]")
    s = agente.decidir(espacio, entrante("Pregunta rara"), falso)
    assert [c["model"] for c in falso.llamadas] == [modelo.MODELO_RUTINA, modelo.MODELO_GRANDE]
    assert falso.llamadas[1]["fallbacks"] == "default" and s.via == "modelo"


def test_falla_de_la_api_pasa_a_la_persona(espacio):
    def revienta(**_):
        raise ConnectionError("sin red")
    roto = SimpleNamespace(messages=SimpleNamespace(create=revienta))
    s = agente.decidir(espacio, entrante("Hola"), roto)
    assert s.via == "persona" and "ConnectionError" in s.motivo


def test_sin_perfil_o_sin_texto_va_a_la_persona(tmp_path, espacio):
    vacio = Espacio("sin-perfil", tmp_path)
    assert agente.decidir(vacio, entrante("Hola")).motivo == "sin perfil aprobado"
    foto = historial.Mensaje("w9", "1", False, 1, "image", None)
    assert "sin texto" in agente.decidir(espacio, foto).motivo


def test_la_conversacion_solo_ve_lo_anterior_y_empieza_en_cliente(espacio):
    m = historial.por_id(espacio)["wamid.MUESTRA0102"]
    conv = agente._conversacion(espacio, m)
    assert conv[0]["role"] == "user" and "25 personas" in conv[-1]["content"]
    assert all("$6,000" not in c["content"] for c in conv)


# --------------------------------------------------------------------------- #
#  Gasto                                                                       #
# --------------------------------------------------------------------------- #
def test_costo_con_precios_de_la_skill():
    assert gasto.costo_usd("claude-opus-5-5", entrada=1_000_000, salida=0) == pytest.approx(4.0)
    assert gasto.costo_usd("claude-haiku-5-5", entrada=0, salida=1_000_000) == pytest.approx(0.5)
    assert gasto.costo_usd("claude-haiku-5-5", entrada=1_000_000, salida=0, lote=True) == pytest.approx(0.25)
    assert gasto.costo_usd("claude-opus-5-5", entrada=0, salida=0, cache_escritura=1_000_000) == pytest.approx(5.0)
    with pytest.raises(gasto.PrecioDesconocido):
        gasto.costo_usd("modelo-sin-precio", entrada=1, salida=1)


def test_estimado_de_un_cliente_tipico_es_explicito():
    e = gasto.estimar_mes(conversaciones=300, turnos_por_conversacion=4, fraccion_guardadas=0.3,
                          perfil_tokens=6000, historia_tokens=1500, salida_tokens=150,
                          fraccion_escala_grande=0.05, mensajes_historial=3000, perfil_inicial=True)
    assert e["total"] == pytest.approx(sum(v for k, v in e.items() if k not in ("total", "precios_de")))
    assert e["precios_de"] == gasto.PRECIOS_FECHA and e["total"] < 20


def test_tope_desde_el_entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("TENANT_TOPE_USD_MES", "12.5")
    assert gasto.tope_usd(Espacio("con-entorno", tmp_path)) == 12.5
    monkeypatch.setenv("TENANT_TOPE_USD_MES", "no-es-numero")
    assert gasto.tope_usd(Espacio("con-entorno", tmp_path)) == 0.0


# --------------------------------------------------------------------------- #
#  Sombra y vara                                                               #
# --------------------------------------------------------------------------- #
def test_repaso_y_vara_sobre_la_muestra(espacio):
    textos = [f"Respuesta {i}. [[META persona=no]]" for i in range(20)]
    n = sombra.repasar(espacio, ModeloFalso(*textos))
    assert n == len(agente.salidas(espacio)) > 0
    assert sombra.repasar(espacio, ModeloFalso()) == 0  # no repite
    informe = sombra.medir(espacio)
    d = informe["desarrollo"]
    assert d["n"] < sombra.MINIMO and d["concluye"] is False  # n < 30 no concluye
    assert d["errores_de_cifra"] == 0
    assert informe["holdout"]["sellado"] is True
    assert informe["mediana_segundos_hasta_cotizacion_persona"] > 0
    abierto = sombra.medir(espacio, abrir_holdout=True)
    assert "cobertura" in abierto["holdout"] and espacio.leer_lineas("vara_aperturas.jsonl")


def test_vara_acierto_y_placebo():
    def par(i, borrador, real):
        s = agente.Salida("c", "h", f"e{i}", "modelo", borrador)
        e = historial.Mensaje(f"e{i}", "h", False, i, "text", "?")
        r = historial.Mensaje(f"r{i}", "h", True, i + 1, "text", real)
        return {"salida": s, "entrante": e, "real": r}
    pares = [par(i, f"respuesta distinta numero {'x' * i} {i}", f"respuesta distinta numero {'x' * i} {i}")
             for i in range(40)]
    m = sombra.metricas(pares)
    assert m["habria_enviado_sin_editar"] == 1.0 and m["concluye"]
    assert m["placebo"] < m["habria_enviado_sin_editar"]


def test_error_de_cifra_se_cuenta():
    assert sombra.error_de_cifra(agente.Salida("c", "h", "e", "modelo", "Son 300"))
    assert sombra.error_de_cifra(agente.Salida("c", "h", "e", "guardada", "Cuesta $300"))
    assert not sombra.error_de_cifra(agente.Salida("c", "h", "e", "guardada", "A las 3 de la tarde"))
    assert not sombra.error_de_cifra(agente.Salida("c", "h", "e", "persona", "Son 300"))


# --------------------------------------------------------------------------- #
#  Simbiosis (respuestas grabadas, sin red)                                    #
# --------------------------------------------------------------------------- #
class LoteFalso:
    def __init__(self, categoria="faq"):
        self.categoria, self.pedidos = categoria, []
        self.batches = SimpleNamespace(create=self._create, retrieve=lambda _id: SimpleNamespace(processing_status="ended"),
                                       results=self._results)
        self.messages = SimpleNamespace(batches=self.batches)

    def _create(self, requests):
        self.pedidos = requests
        return SimpleNamespace(id="lote_1")

    def _results(self, _id):
        uso = SimpleNamespace(input_tokens=100, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0)
        for p in self.pedidos:
            msg = SimpleNamespace(usage=uso, content=[SimpleNamespace(type="text", text=json.dumps({"categoria": self.categoria}))])
            yield SimpleNamespace(custom_id=p["custom_id"], result=SimpleNamespace(type="succeeded", message=msg))


def test_clasificacion_en_lote_con_el_modelo_chico(espacio):
    falso = LoteFalso()
    simbiosis.enviar_lote(espacio, falso)
    assert falso.pedidos and all(p["params"]["model"] == modelo.MODELO_RUTINA for p in falso.pedidos)
    assert all(len(p["custom_id"]) <= 64 and p["custom_id"].isalnum() for p in falso.pedidos)
    clases = simbiosis.recoger_lote(espacio, falso)
    negocio = [m for m in historial.cargar(espacio) if m.del_negocio]
    assert set(clases) == {m.id for m in negocio} and set(clases.values()) == {"faq"}
    lotes = [r for r in espacio.leer_lineas(gasto.ARCHIVO) if r["motivo"] == "clasificacion"]
    assert len(lotes) == len(negocio) and all(r["lote"] for r in lotes)


def test_construir_perfil_valida_y_no_enciende(espacio):
    grabado = leer_muestra("perfil_grabado.json")
    for seccion in perfil.SECCIONES:  # la API llena todos los campos del esquema
        for fila in grabado[seccion]:
            fila["origen"] = {"tipo": "mensaje", "id": "", "campo": "", "nombre": "", "cita": "", **fila["origen"]}
    grabado["voz"].append({"frase": "inventada", "origen": {"tipo": "mensaje", "id": "wamid.NO", "campo": "",
                                                            "nombre": "", "cita": "inventada"}})
    activa = perfil.version_activa(espacio)
    falso = ModeloFalso(json.dumps(grabado, ensure_ascii=False))
    n, descartados = simbiosis.construir_perfil(espacio, falso, desde_ts=0)
    pedido = falso.llamadas[0]
    assert pedido["model"] == modelo.MODELO_GRANDE and pedido["output_config"]["format"]["type"] == "json_schema"
    assert "5210000000000" not in pedido["messages"][0]["content"]  # el teléfono del aprobador no va
    assert perfil.version_activa(espacio) == activa and n == activa + 1
    assert any(d["renglon"].get("frase") == "inventada" for d in descartados)
    with pytest.raises(RuntimeError, match="no terminó"):
        simbiosis.construir_perfil(espacio, ModeloFalso("{}", stop_reason="max_tokens"))


# --------------------------------------------------------------------------- #
#  MCP por stdio                                                               #
# --------------------------------------------------------------------------- #
def test_mcp_por_stdio(espacio, monkeypatch):
    monkeypatch.setenv("AGENTE_ESPACIO", espacio.cliente_id)
    monkeypatch.setenv("AGENTE_LLAVE", llave_de(espacio.cliente_id))
    entrada = "\n".join(json.dumps(p) for p in [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "leer_perfil", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "ver_metricas", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "ver_sombra", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "aprobar", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 7, "method": "otra/cosa"},
    ]) + "\nno es json\n"
    salida = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(entrada))
    monkeypatch.setattr(sys, "stdout", salida)
    assert mcp.main() == 0
    r = [json.loads(linea) for linea in salida.getvalue().splitlines()]
    assert [x.get("id") for x in r] == [1, 2, 3, 4, 5, 6, 7, None]
    assert json.loads(r[2]["result"]["content"][0]["text"])["activa"] == perfil.version_activa(espacio)
    assert r[5]["error"]["code"] == -32602 and r[6]["error"]["code"] == -32601


def test_mcp_no_abre_sin_llave_del_espacio(espacio, monkeypatch, capsys):
    monkeypatch.setenv("AGENTE_ESPACIO", espacio.cliente_id)
    monkeypatch.setenv("AGENTE_LLAVE", llave_de("otro-negocio"))
    assert mcp.main() == 2 and "no se abre" in capsys.readouterr().err


def test_mcp_error_de_herramienta_no_tumba_el_servidor(espacio):
    r = mcp.Servidor(espacio).atender({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                       "params": {"name": "proponer_cambio", "arguments": {"motivo": "sin nombre"}}})
    assert r["result"]["isError"] is True and "KeyError" in r["result"]["content"][0]["text"]
    assert perfil.versiones(espacio) == [1]


# --------------------------------------------------------------------------- #
#  Servidor (webhook firmado, revisión, aprobaciones)                          #
# --------------------------------------------------------------------------- #
@pytest.fixture()
def http(espacio, monkeypatch):
    from agente.app import app
    from fastapi.testclient import TestClient
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "secreto-app")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verifica")
    config = espacio.config()
    config["phone_number_id"] = "100000000000001"
    espacio.escribir_json("config.json", config)
    return TestClient(app)


def _firmado(cuerpo: dict) -> tuple[bytes, dict]:
    datos = json.dumps(cuerpo).encode()
    firma = "sha256=" + hmac.new(b"secreto-app", datos, hashlib.sha256).hexdigest()
    return datos, {"X-Hub-Signature-256": firma, "Content-Type": "application/json"}


def test_webhook_verificacion_y_firma(http):
    assert http.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "verifica",
                                        "hub.challenge": "42"}).text == "42"
    assert http.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "otra"}).status_code == 403
    datos, cabeceras = _firmado({"entry": []})
    assert http.post("/webhook", content=datos, headers=dict(cabeceras, **{"X-Hub-Signature-256": "sha256=00"})).status_code == 401
    assert http.post("/webhook", content=datos, headers=cabeceras).status_code == 200
    assert http.get("/health").json()["ok"] is True
    assert http.get("/api/health").json()["service"] == "dged-agente"


def test_webhook_mensaje_vivo_queda_en_sombra(http, espacio):
    carga = {"object": "whatsapp_business_account", "entry": [{"id": "1", "changes": [{"field": "messages", "value": {
        "metadata": {"display_phone_number": "5210000000000", "phone_number_id": "100000000000001"},
        "messages": [{"from": "5210000000077", "id": "wamid.VIVO1", "timestamp": "1790000000", "type": "text",
                      "text": {"body": "Cual es el horario de entrada y salida?"}}]}}]}]}
    datos, cabeceras = _firmado(carga)
    assert http.post("/webhook", content=datos, headers=cabeceras).json() == {"guardados": 0, "salidas": 1}
    assert agente.salidas(espacio)[-1].via == "guardada"
    assert not espacio.leer_lineas("enviados.jsonl")  # en sombra no sale


def test_revision_y_aprobacion_con_llave(http, espacio):
    llave = {"X-Tenant-Key": llave_de(espacio.cliente_id)}
    assert http.get(f"/espacios/{espacio.cliente_id}/revision").status_code == 401
    assert http.get("/espacios/NO_VALIDO/revision", headers=llave).status_code == 404
    assert "Sin propuestas" in http.get(f"/espacios/{espacio.cliente_id}/revision", headers=llave).text
    n, _ = perfil.proponer(espacio, leer_muestra("perfil_grabado.json"), autor="t", nombre="segunda")
    pagina = http.get(f"/espacios/{espacio.cliente_id}/revision", headers=llave).text
    assert "De dónde salió" in pagina and "La finca entre semana sale en $6,000" in pagina
    assert "No entraron" in pagina
    url = f"/espacios/{espacio.cliente_id}/versiones/{n}/aprobar"
    assert http.post(url, json={"aprobador": "otro"}, headers=llave).status_code == 403
    assert http.post(url, json={"aprobador": "Dueña de muestra"}, headers=llave).json() == {"activa": n}


def test_aprobar_salida_por_http(http, espacio):
    llave = {"X-Tenant-Key": llave_de(espacio.cliente_id)}
    s = agente.atender(espacio, entrante("Precio"), ModeloFalso(
        "Con gusto. [[META cotizar=si propiedad=quinta llegada=2026-11-09 salida=2026-11-11 personas=4 evento=no]]"))
    base = f"/espacios/{espacio.cliente_id}/salidas"
    assert http.post(f"{base}/nada/aprobar", json={"aprobador": "Encargado de muestra"}, headers=llave).status_code == 404
    assert http.post(f"{base}/{s.id}/aprobar", json={"aprobador": "x"}, headers=llave).status_code == 403
    r = http.post(f"{base}/{s.id}/aprobar", json={"aprobador": "Encargado de muestra"}, headers=llave).json()
    assert r["aprobada"] and not r["enviada"] and "conector" in r["motivo"]


def test_canal_envia_por_la_cloud_api(espacio, monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "t")
    config = espacio.config()
    config.update(phone_number_id="100000000000001", encendido="sin_cifra")
    espacio.escribir_json("config.json", config)
    s = agente.decidir(espacio, entrante("Cual es el horario de entrada y salida?"))
    vistos = []
    canal.enviar(espacio, s, transporte=lambda url, cuerpo: vistos.append((url, cuerpo)) or {"messages": [{}]})
    url, cuerpo = vistos[0]
    assert url.endswith("/100000000000001/messages") and cuerpo["messaging_product"] == "whatsapp"
    otro = montar(espacio.raiz, "otro-negocio")
    assert "otro cliente" in canal.motivo_para_no_enviar(otro, s)


def test_numeros_lee_las_dos_formas_mexicanas_de_escribir_montos():
    """El enjambre lo encontró (2026-10-27): *"12.000"* se leía 12 y *"$600,00"*
    60000, y un renglón real del perfil se tiraba por "cifra que no está en la cita"."""
    from agente.perfil import numeros

    assert numeros("12.000") == {"12000"}
    assert numeros("Mesas con 10 sillas $600,00 c/u") == {"10", "600"}
    assert numeros("$3,500.00") == {"3500"} and numeros("35,000 el fin") == {"35000"}
    assert "2000.50" in numeros("2,000.50")
    # el candado de la cifra lee igual: la del cotizador escrita con punto de miles sigue permitida
    from agente import guardia
    assert guardia.cifras_no_permitidas("Le queda en 12.000", numeros("$12,000")) == []
