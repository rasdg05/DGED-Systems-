"""La mesa de la dueña (D-042), como `dueno.py` de Gestor: órdenes por WhatsApp,
reportes, y una administradora nunca es clienta."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from agente import agente, enviador, historial, mesa, rondas, semaforo, vinculado
from agente.historial import Mensaje
from tests.test_agente_enjambre import _m, _ronda

DUENA = "5210000000000"      # el teléfono de quien aprueba en la muestra (alta: 5210000000000)
OTRA = "5217770001111"       # otra administradora, de config.json
CLIENTE = "5210000007777"


@pytest.fixture()
def con_mesa(espacio):
    espacio.escribir_json("config.json", dict(espacio.config(), administradores=["+52 777 000 1111"]))
    historial.guardar(espacio, [
        _m("wamid.E1", "Hola, ¿tienen la quinta libre en noviembre?", ts=1790000000),
        _m("wamid.E2", "Claro, ¿para qué fechas y cuántas personas?", True, ts=1790000100),
        _m("wamid.E3", "Del 9 al 11 de noviembre, somos ocho. ¿Cuánto sería?", ts=1790000200),
        Mensaje("d1", DUENA, False, 1790000300, "text", "Oye, mañana llega la familia"),
    ])
    return espacio


def _orden(espacio, de, texto, ident="o1"):
    m = Mensaje(ident, de, False, 1790000400, "text", texto)
    historial.guardar(espacio, [m])
    return mesa.atender(espacio, m)


def test_una_administradora_no_es_clienta(con_mesa):
    assert mesa.es_admin(con_mesa, DUENA) and mesa.es_admin(con_mesa, OTRA) and not mesa.es_admin(con_mesa, CLIENTE)
    assert mesa.es_admin(con_mesa, "527770001111") and mesa.es_admin(con_mesa, "7770001111")  # misma lada, otra forma
    hilos = mesa.clientes(con_mesa, historial.hilos(con_mesa))
    assert DUENA not in hilos and CLIENTE in hilos
    assert all(f.hilo != DUENA for f in semaforo.leer(hilos))
    _, descartadas = rondas.validar(con_mesa, {"nombre": "a-la-duena", "orden": "x", "entradas": [
        {"hilo": DUENA, "ultimo_id": "d1", "textos": ["Hola, sigue interesada?"]}]})
    assert descartadas and "no existe" in descartadas[0]["motivo"]


@pytest.mark.parametrize("texto, orden", [
    ("Estado", "estado"), ("reporte", "estado"), ("¿Pendientes?", "pendientes"), ("cola", "cola"),
    ("Aprueba la ronda", "aprueba"), ("aprueba ronda prueba-1", "aprueba"), ("Enciende el envío", "enciende"),
    ("pausa el envio", "pausa"), ("ayuda", "ayuda"), ("Oye, mañana llega la familia", None),
])
def test_ordenes(texto, orden):
    o = mesa.leer_orden(texto)
    assert (o or {}).get("orden") == orden


def test_la_mesa_contesta_a_la_duena_y_no_a_clientes(con_mesa):
    assert _orden(con_mesa, CLIENTE, "estado", "c9") is None
    assert _orden(con_mesa, DUENA, "Oye, mañana llega la familia", "d2") is None  # plática normal: no se contesta sola
    r = _orden(con_mesa, DUENA, "estado", "d3")
    assert r.startswith("Reporte de su asistente") and "Semáforo" in r
    assert con_mesa.leer_lineas(mesa.SALIDA)[-1]["para"] == DUENA


def test_aprobar_la_ronda_y_encender_solo_lo_ordena_quien_aprueba(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    rondas.cargar(con_mesa, _ronda())
    assert "solo lo puede ordenar" in _orden(con_mesa, OTRA, "aprueba la ronda", "x1")
    r = _orden(con_mesa, DUENA, "aprueba la ronda", "x2")
    assert "Aprobé 1" in r and "En cola: 0" in r and "enciende el envío" in r  # en pausa: aprobada, no encolada
    assert agente.aprobadas(con_mesa)
    r = _orden(con_mesa, DUENA, "enciende el envío", "x3")
    assert "encendido" in r.lower() and "Ya van a la cola 1" in r  # lo aprobado en pausa sale al encender
    assert len(enviador.pendientes(con_mesa)) == 1
    c = con_mesa.config()
    assert (c["canal"], c["encendido"]) == ("vinculado", "sin_cifra")
    assert con_mesa.leer_lineas("cambios_canal.jsonl")[-1]["por"] == "Dueña de muestra"
    assert "pausa" in _orden(con_mesa, DUENA, "pausa el envío", "x4").lower()
    assert con_mesa.config()["encendido"] == "sombra"


def test_la_mesa_solo_le_escribe_a_administradoras(con_mesa):
    mesa.encolar(con_mesa, DUENA, "reporte")
    mesa.encolar(con_mesa, CLIENTE, "esto no debe salir")  # algo que alguien metió al buzón a mano
    mandados = []
    assert mesa.despachar(con_mesa, lambda h, t: mandados.append(h)) == 1
    assert mandados == [DUENA]
    assert con_mesa.leer_lineas(mesa.ENVIADOS)[-1]["motivo"] == "no es administradora"
    assert mesa.despachar(con_mesa, lambda h, t: mandados.append(h)) == 0  # no se repite


def test_reporte_una_vez_por_horario_a_cada_administradora(con_mesa):
    temprano = datetime(2026, 10, 28, 13, 0, tzinfo=timezone.utc)   # 7:00 en México
    assert mesa.reporte_si_toca(con_mesa, temprano) == 0
    manana = datetime(2026, 10, 28, 15, 5, tzinfo=timezone.utc)     # 9:05
    assert mesa.reporte_si_toca(con_mesa, manana) == 2
    assert mesa.reporte_si_toca(con_mesa, manana) == 0
    destinos = {e["para"] for e in con_mesa.leer_lineas(mesa.SALIDA)}
    assert destinos == {DUENA, "521" + OTRA[-10:]}
    assert mesa.reporte_si_toca(con_mesa, datetime(2026, 10, 29, 1, 30, tzinfo=timezone.utc)) == 2  # 19:30


def test_la_cola_de_clientes_nunca_manda_a_una_administradora(con_mesa):
    """Defensa de fondo: aunque una salida a una administradora llegara a la cola."""
    vinculado.publicar(con_mesa, "conectado")
    con_mesa.escribir_json("config.json", dict(con_mesa.config(), canal="vinculado", encendido="sin_cifra"))
    s = agente.Salida(cliente_id=con_mesa.cliente_id, hilo=DUENA, responde_a="d1", via="regla", texto="Hola")
    con_mesa.agregar_linea(agente.ARCHIVO, s.a_dict())
    enviador.encolar(con_mesa, s.id)
    mandados = []
    enviador.turno(con_mesa, lambda h, t: mandados.append(h), datetime(2026, 10, 28, 18, 0, tzinfo=timezone.utc))
    assert not mandados and "administradora" in con_mesa.leer_lineas(enviador.ENVIADOS)[-1]["motivo"]


def test_lo_aprobado_ya_no_cuenta_como_esperando_su_si(con_mesa):
    """Hallazgo en producción, 2026-10-27: la Cola decía "128 esperan su sí" con la ronda ya aprobada."""
    salidas, _ = rondas.cargar(con_mesa, _ronda())
    assert any(s.requiere_aprobacion and not s.aprobada_por for s in agente.salidas(con_mesa))
    agente.aprobar_salida(con_mesa, salidas[0].id, "Dueña de muestra")
    assert not any(s.requiere_aprobacion and not s.aprobada_por for s in agente.salidas(con_mesa))
