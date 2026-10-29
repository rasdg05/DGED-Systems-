"""El tiempo al número (`tiempos.py`, corrida GM del 2026-10-29), como el de Gestor (corrida 7)."""
from __future__ import annotations

from agente import tiempos
from agente.historial import Mensaje

H = 3600
T0 = 1790000000


def _m(i, hilo, de_negocio, ts, texto, tipo="text"):
    return Mensaje(i, hilo, de_negocio, ts, tipo, texto)


def test_tiempos_cuenta_al_que_nunca_recibio_numero_y_aparte_la_foto():
    hilos = {
        "a": [_m("1", "a", False, T0, "Precio para 20?"), _m("2", "a", True, T0 + H, "Son 22,000 el fin de semana")],
        "b": [_m("3", "b", False, T0, "Costo?"), _m("4", "b", True, T0 + 60, "Para cuántas personas?")],
        "c": [_m("5", "c", False, T0, "Cuánto cuesta?"), _m("6", "c", True, T0 + 60, None, tipo="image")],
        "d": [_m("7", "d", False, T0 + 100 * H - 60, "precio?")],              # recién pedido: abierto
    }
    r = tiempos.al_numero(hilos, ahora_ts=T0 + 100 * H)["total"]
    assert (r["pedidos"], r["con_numero"], r["sin_numero"], r["con_imagen"], r["abiertos"]) == (4, 1, 1, 1, 1)
    assert r["mediana_h"] == 1.0 and r["pct_en_24h"] == 33.3 and not r["concluye"]


def test_tiempos_catorce_dias_de_silencio_abren_otro_pedido():
    hilo = [_m("1", "a", False, T0, "precio?"), _m("2", "a", False, T0 + 15 * 86400, "Hola, cuánto cuesta en diciembre?"),
            _m("3", "a", True, T0 + 15 * 86400 + 2 * H, "En diciembre 30,000")]
    lista = tiempos.pedidos({"a": hilo}, ahora_ts=T0 + 20 * 86400)
    assert [p["horas"] for p in lista] == [None, 2.0]


def test_tiempos_la_linea_del_reporte_no_lleva_telefonos():
    hilos = {"5217770001234": [_m("1", "5217770001234", False, T0, "Precio?"),
                               _m("2", "5217770001234", True, T0 + H, "Son 12,000")]}
    linea = tiempos.linea(tiempos.al_numero(hilos, ahora_ts=T0 + 2 * H))
    assert "con número 1" in linea and "1234" not in linea
