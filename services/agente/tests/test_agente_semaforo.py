"""El semáforo (como el de Gestor): un estado por plática, la más urgente primero."""
from __future__ import annotations

from agente import semaforo
from agente.historial import Mensaje

H = 3600


def _m(i, hilo, del_negocio, ts, texto):
    return Mensaje(i, hilo, del_negocio, ts, "text", texto)


def _estados(hilos, ahora):
    return {f.hilo: (f.estado, f.color, f.seguimiento) for f in semaforo.leer(hilos, ahora)}


def test_un_estado_por_platica_y_su_color():
    hilos = {
        "sin": [_m("1", "sin", False, 0, "Info por favor")],
        "cot": [_m("2", "cot", False, 0, "Precio para 20?"), _m("3", "cot", True, 60, "Son 22,000 el fin de semana")],
        "pro": [_m("4", "pro", False, 0, "Tienen libre el 5?"), _m("5", "pro", True, 30, "Déjeme revisar y le confirmo")],
        "rec": [_m("6", "rec", False, 0, "Me cobraron doble, exijo mi reembolso")],
        "fin": [_m("7", "fin", False, 0, "precio?"), _m("8", "fin", True, 30, "Son 10,000"),
                _m("9", "fin", False, 90, "Gracias, ya rentamos en otro lado")],
        "pre": [_m("a", "pre", False, 0, "Hola"), _m("b", "pre", True, 30, "Para cuántas personas?")],
    }
    e = _estados(hilos, 30 * H)
    assert e["sin"] == ("sin_atender", "rojo", False)
    assert e["pro"][:2] == ("promesa", "rojo")
    assert e["rec"][:2] == ("reclamo", "rojo")
    assert e["cot"] == ("cotizado", "ambar", True)       # más de 24 h con precio: seguimiento
    assert e["pre"] == ("esperando_cliente", "ambar", True)
    assert e["fin"][:2] == ("cerrada", "gris")


def test_el_seguimiento_espera_un_dia_y_se_enfria_a_las_tres_semanas():
    cot = {"c": [_m("1", "c", False, 0, "Precio para 20?"), _m("2", "c", True, 0, "Son 22,000")]}
    assert _estados(cot, 2 * H)["c"] == ("cotizado", "verde", False)
    assert _estados(cot, (semaforo.DIAS_VIGENCIA * 24 + 1) * H)["c"] == ("cotizado", "gris", False)


def test_la_mas_urgente_primero_y_dentro_del_color_la_que_mas_espera():
    hilos = {"nuevo": [_m("1", "nuevo", False, 10 * H, "Info")], "viejo": [_m("2", "viejo", False, 0, "Info")],
             "cot": [_m("3", "cot", False, 0, "Precio?"), _m("4", "cot", True, 0, "Son 5,000")]}
    orden = [f.hilo for f in semaforo.leer(hilos, 12 * H)]
    assert orden == ["viejo", "nuevo", "cot"]


def test_lo_que_nadie_atendio_hace_mas_de_tres_semanas_se_enfrio():
    viejo = {"v": [_m("1", "v", False, 0, "Info por favor")]}
    assert _estados(viejo, (semaforo.DIAS_VIGENCIA * 24 + 1) * H)["v"][:2] == ("sin_atender", "gris")
