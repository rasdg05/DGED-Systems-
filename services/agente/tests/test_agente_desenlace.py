"""Qué pasó con cada ronda (`desenlace.py`, corrida GM del 2026-10-29): la métrica que manda."""
from __future__ import annotations

from agente import agente, desenlace, historial, mesa
from agente.historial import Mensaje

H = 3600
T0 = 1790000000


def _m(i, hilo, de_negocio, ts, texto):
    return Mensaje(i, hilo, de_negocio, ts, "text", texto)


def _ronda(espacio, casos):
    """casos: (hilo, [mensajes después del envío]). Cada hilo recibió el mismo seguimiento aprobado."""
    texto = "Hola, sigue buscando lugar? Con gusto le confirmamos disponibilidad."
    mensajes = []
    for hilo, despues in casos:
        mensajes += [_m(f"{hilo}-0", hilo, False, T0, "Precio para 20?"),
                     _m(f"{hilo}-1", hilo, True, T0 + 60, "Son 12,000"),
                     _m(f"dged-{hilo}", hilo, True, T0 + 48 * H, texto)] + despues
        s = agente.Salida(cliente_id=espacio.cliente_id, hilo=hilo, responde_a=f"{hilo}-1", via="ronda",
                          texto=texto, motivo="ronda 2026-10-27-seguimiento: cotizado sin respuesta",
                          requiere_aprobacion=True, aprobada_por="Dueña de muestra")
        espacio.agregar_linea(agente.ARCHIVO, s.a_dict())
    historial.guardar(espacio, mensajes)


def test_desenlace_cuenta_lo_que_paso_despues_del_envio(espacio):
    _ronda(espacio, [
        ("521000000101", []),                                                               # no contestó
        ("521000000102", [_m("a", "521000000102", False, T0 + 50 * H, "Gracias ya tenemos opción")]),
        ("521000000103", [_m("b", "521000000103", False, T0 + 50 * H, "Lo platico y le aviso")]),
        ("521000000104", [_m("c", "521000000104", False, T0 + 50 * H, "Sería para 35 personas o 30")]),
        ("521000000105", [_m("d", "521000000105", False, T0 + 49 * H, "Sí, para el 14, somos 20"),
                          _m("e", "521000000105", True, T0 + 51 * H, "Para esa fecha le queda en 12,000")]),
    ])
    (fila,) = desenlace.de_rondas(espacio)
    assert fila["ronda"] == "2026-10-27-seguimiento" and fila["enviados"] == 5
    assert (fila["contestaron"], fila["cerraron"], fila["no_piden"], fila["esperan_respuesta"]) == (4, 1, 1, 1)
    assert fila["atendidos"] == 1 and fila["con_cifra"] == 1 and fila["horas_a_persona"]["mediana"] == 2.0
    assert not fila["concluye"]                                            # n < 30
    assert "esperan respuesta 1" in desenlace.linea(fila) and "5210" not in desenlace.linea(fila)
    assert desenlace.linea(dict(fila, contestaron=0)).endswith("5 enviados, nadie ha contestado todavía.")


def test_desenlace_no_cuenta_lo_que_no_salio_ni_lo_que_no_es_ronda(espacio):
    s = agente.Salida(cliente_id=espacio.cliente_id, hilo="521000000201", responde_a="x", via="ronda",
                      texto="nunca salió", motivo="ronda 2026-10-28-am: x", requiere_aprobacion=True,
                      aprobada_por="Dueña de muestra")
    espacio.agregar_linea(agente.ARCHIVO, s.a_dict())
    assert desenlace.de_rondas(espacio) == []
    assert desenlace.nombre_de_ronda("cotización incompleta") == "sin nombre"


def test_el_reporte_de_la_mesa_dice_que_paso_con_la_ronda(espacio):
    import time
    ahora = time.time()
    global T0
    viejo, T0 = T0, int(ahora - 72 * H)
    try:
        _ronda(espacio, [("521000000301", [_m("r1", "521000000301", False, T0 + 50 * H, "Es el máximo de personas?")])])
    finally:
        T0 = viejo
    texto = mesa.reporte(espacio)
    assert "Ronda 2026-10-27-seguimiento: contestaron 1 de 1" in texto
    assert texto.index("Contestaron al seguimiento") < texto.index("Lo más urgente")


def test_el_reporte_dice_el_texto_del_cliente_en_una_linea():
    assert mesa._dicho("Es en marzo el 26 al 28\nPara 120 personas") == "Es en marzo el 26 al 28 / Para 120 personas"
    assert mesa._dicho("") == "(foto o audio)" and mesa._dicho(None) == "(foto o audio)"
    assert mesa._dicho("x" * 80).endswith("…")
