"""El envío por el dispositivo vinculado (D-037): mismos candados, al paso de una persona."""
from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from agente import agente, canal, enviador, historial, rondas, vinculado
from agente.app import app
from fastapi.testclient import TestClient
from tests.test_agente_enjambre import _calendario, _m, _ronda

AQUI = Path(agente.__file__).parent
MEDIODIA = datetime(2026, 10, 28, 18, 0, tzinfo=timezone.utc)  # 12:00 en México
APROBADOR = "Dueña de muestra"


@pytest.fixture()
def con_pendiente(espacio):
    """La misma plática pendiente que en `test_agente_enjambre`."""
    historial.guardar(espacio, [
        _m("wamid.E1", "Hola, ¿tienen la quinta libre en noviembre?", ts=1790000000),
        _m("wamid.E2", "Claro, ¿para qué fechas y cuántas personas?", True, ts=1790000100),
        _m("wamid.E3", "Del 9 al 11 de noviembre, somos ocho. ¿Cuánto sería?", ts=1790000200),
    ])
    return espacio


def _vinculado(espacio, encendido="sin_cifra"):
    espacio.escribir_json("config.json", dict(espacio.config(), canal="vinculado", encendido=encendido))
    vinculado.publicar(espacio, "conectado", numero="5210000000000")


def _ronda_aprobada(espacio, nombre="prueba-1", **entrada):
    salidas, _ = rondas.cargar(espacio, dict(_ronda(**entrada), nombre=nombre))
    for s in salidas:
        agente.aprobar_salida(espacio, s.id, APROBADOR)
        canal.enviar(espacio, s)
    return salidas


class Buzon:
    def __init__(self, falla=False):
        self.mandados, self.falla = [], falla

    def __call__(self, hilo, texto):
        if self.falla:
            raise ConnectionError("whatsapp")
        self.mandados.append((hilo, texto))


# ----------------------------------------------------------------- dónde vive el envío
def test_la_unica_llamada_que_escribe_a_whatsapp_vive_en_mandador():
    """El lector sigue sin enviar en su código; el envío tiene un solo lugar."""
    con_envio = set()
    for archivo in AQUI.glob("*.py"):
        llamadas = {n.func.attr for n in ast.walk(ast.parse(archivo.read_text(encoding="utf-8")))
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        if any(c in llamadas for c in ("send_message", "SendMessage", "send_chat_presence", "mark_read")):
            con_envio.add(archivo.name)
    assert con_envio == {"mandador.py"}


# ----------------------------------------------------------------- canal
def test_sin_lector_conectado_el_vinculado_no_es_canal(con_pendiente):
    con_pendiente.escribir_json("config.json", dict(con_pendiente.config(), canal="vinculado", encendido="sin_cifra"))
    assert not canal.configurado(con_pendiente)
    vinculado.publicar(con_pendiente, "conectado")
    assert canal.configurado(con_pendiente) and not canal.oficial(con_pendiente)


def test_aprobada_se_encola_y_no_sale_dos_veces(con_pendiente):
    _vinculado(con_pendiente)
    salidas = _ronda_aprobada(con_pendiente)
    canal.enviar(con_pendiente, salidas[0])  # aprobar otra vez no la duplica
    assert enviador.pendientes(con_pendiente) == [salidas[0].id]
    buzon = Buzon()
    assert enviador.turno(con_pendiente, buzon, MEDIODIA) == {"salida": salidas[0].id, "enviado": True}
    assert buzon.mandados == [(salidas[0].hilo, salidas[0].texto)]
    assert enviador.turno(con_pendiente, buzon, MEDIODIA + timedelta(hours=1)) is None
    assert len(buzon.mandados) == 1


# ----------------------------------------------------------------- al paso de una persona
def test_horario_pausa_y_tope_del_dia(con_pendiente):
    _vinculado(con_pendiente)
    s = _ronda_aprobada(con_pendiente)[0]
    noche = datetime(2026, 10, 28, 5, 0, tzinfo=timezone.utc)  # 23:00 en México
    assert "fuera de horario" in enviador.turno(con_pendiente, Buzon(), noche)["espera"]
    con_pendiente.agregar_linea(enviador.ENVIADOS, {"salida": "otra", "enviado": True, "hilo": "52",
                                                    "cuando": (MEDIODIA - timedelta(seconds=10)).isoformat()})
    assert enviador.turno(con_pendiente, Buzon(), MEDIODIA)["espera"] == "pausa entre envíos"
    for i in range(enviador.TOPE_DIA):
        con_pendiente.agregar_linea(enviador.ENVIADOS, {"salida": f"x{i}", "enviado": True, "hilo": "52",
                                                        "cuando": (MEDIODIA - timedelta(hours=2)).isoformat()})
    assert "tope del día" in enviador.turno(con_pendiente, Buzon(), MEDIODIA + timedelta(minutes=5))["espera"]
    assert s.id in enviador.pendientes(con_pendiente)


def test_el_espacio_no_puede_ir_mas_rapido_que_los_techos(con_pendiente):
    con_pendiente.escribir_json("config.json", dict(con_pendiente.config(), envio={
        "pausa_min": 1, "pausa_max": 2, "tope_dia": 5000, "hora_desde": 0, "hora_hasta": 23}))
    r = enviador.Ritmo.de(con_pendiente)
    assert (r.pausa_min, r.tope_dia) == (enviador.PAUSA_MIN, enviador.TOPE_DIA)
    assert r.hora_desde >= enviador.HORA_DESDE - 1 and r.hora_hasta <= enviador.HORA_HASTA + 1


# ----------------------------------------------------------------- se revisa justo antes
def test_si_la_platica_se_movio_o_se_aparto_la_fecha_no_sale(con_pendiente):
    _vinculado(con_pendiente)
    _calendario(con_pendiente)
    pedido = {"propiedad": "quinta", "llegada": "2026-11-09", "salida": "2026-11-11", "personas": 8}
    s = _ronda_aprobada(con_pendiente, cotizacion=pedido)[0]
    from tests.test_agente_enjambre import RESERVA_QUINTA
    _calendario(con_pendiente, RESERVA_QUINTA)
    buzon = Buzon()
    enviador.turno(con_pendiente, buzon, MEDIODIA)
    assert not buzon.mandados
    registro = con_pendiente.leer_lineas(enviador.ENVIADOS)[-1]
    assert registro["salida"] == s.id and not registro["enviado"] and "apartadas" in registro["motivo"]


def test_la_platica_que_contesto_el_cliente_ya_no_recibe_la_ronda(con_pendiente):
    _vinculado(con_pendiente)
    s = _ronda_aprobada(con_pendiente)[0]
    historial.guardar(con_pendiente, [_m("wamid.E9", "Ya no, gracias", ts=1790000900)])
    buzon = Buzon()
    enviador.turno(con_pendiente, buzon, MEDIODIA)
    assert not buzon.mandados and con_pendiente.leer_lineas(enviador.ENVIADOS)[-1]["salida"] == s.id


def test_en_sombra_nada_sale_aunque_este_aprobado(con_pendiente):
    _vinculado(con_pendiente, encendido="sombra")
    salidas, _ = rondas.cargar(con_pendiente, _ronda())
    agente.aprobar_salida(con_pendiente, salidas[0].id, APROBADOR)
    assert "sombra" in canal.motivo_para_no_enviar(con_pendiente, salidas[0])


def test_si_whatsapp_falla_queda_escrito_y_no_se_reintenta_solo(con_pendiente):
    _vinculado(con_pendiente)
    _ronda_aprobada(con_pendiente)
    assert enviador.turno(con_pendiente, Buzon(falla=True), MEDIODIA)["enviado"] is False
    assert enviador.pendientes(con_pendiente) == []


# ----------------------------------------------------------------- el sí a toda la ronda
def test_aprobar_la_ronda_completa_solo_con_la_maestra_y_una_persona_del_alta(con_pendiente):
    _vinculado(con_pendiente)
    rondas.cargar(con_pendiente, _ronda())
    http, ruta = TestClient(app), f"/espacios/{con_pendiente.cliente_id}/rondas/prueba-1/aprobar"
    from agente.espacio import llave_de
    assert http.post(ruta, json={"aprobador": APROBADOR},
                     headers={"X-Tenant-Key": llave_de(con_pendiente.cliente_id)}).status_code == 404
    maestra = {"X-Tenant-Key": "secreto-de-prueba"}
    assert http.post(ruta, json={"aprobador": "alguien"}, headers=maestra).status_code == 403
    r = http.post(ruta, json={"aprobador": APROBADOR}, headers=maestra).json()
    assert len(r["encoladas"]) == 1 and not r["no_salen"]
    assert enviador.pendientes(con_pendiente) == r["encoladas"]


def test_el_canal_lo_cambia_solo_la_maestra_y_queda_escrito(con_pendiente):
    http, ruta = TestClient(app), f"/espacios/{con_pendiente.cliente_id}/canal"
    from agente.espacio import llave_de
    cuerpo = {"canal": "vinculado", "encendido": "sin_cifra"}
    assert http.post(ruta, json=cuerpo, headers={"X-Tenant-Key": llave_de(con_pendiente.cliente_id)}).status_code == 404
    maestra = {"X-Tenant-Key": "secreto-de-prueba"}
    assert http.post(ruta, json={"canal": "telegram", "encendido": "sin_cifra"}, headers=maestra).status_code == 422
    r = http.post(ruta, json=cuerpo, headers=maestra).json()
    assert r["antes"] == {"canal": "oficial", "encendido": "sombra"} and not r["listo"]  # sin lector conectado
    assert con_pendiente.config()["canal"] == "vinculado" and con_pendiente.leer_lineas("cambios_canal.jsonl")


def test_lo_enviado_entra_al_historial_y_la_platica_ya_no_espera(con_pendiente):
    """LXX. 2026-10-28: lo enviado por el vinculado no volvía al historial y el semáforo
    seguía contando como sin respuesta a quien ya recibió la ronda."""
    from agente import pendientes
    _vinculado(con_pendiente)
    s = _ronda_aprobada(con_pendiente)[0]
    enviador.turno(con_pendiente, lambda h, t: "WAMID-1", MEDIODIA)
    hilo = historial.hilos(con_pendiente)[s.hilo]
    assert hilo[-1].id == "WAMID-1" and hilo[-1].del_negocio and hilo[-1].texto == s.texto
    assert s.hilo not in {p.hilo for p in pendientes.leer(historial.hilos(con_pendiente))}
    historial.guardar(con_pendiente, [historial.Mensaje("WAMID-1", s.hilo, True, 1, "text", s.texto)])  # el eco
    assert sum(1 for m in historial.hilos(con_pendiente)[s.hilo] if m.texto == s.texto) == 1


def test_lo_enviado_antes_se_asienta_una_vez(con_pendiente):
    _vinculado(con_pendiente)
    s = _ronda_aprobada(con_pendiente)[0]
    con_pendiente.agregar_linea(enviador.ENVIADOS, {"salida": s.id, "hilo": s.hilo, "enviado": True,
                                                    "cuando": MEDIODIA.isoformat()})
    assert enviador.asentar_enviados(con_pendiente) == 1
    assert enviador.asentar_enviados(con_pendiente) == 0
    assert historial.hilos(con_pendiente)[s.hilo][-1].id == f"dged-{s.id}"
