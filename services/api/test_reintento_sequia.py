"""Si el arranque cayó en la página de error del SMN, calificar reintenta.

Medido 2026-10-12 (docs/verificacion-2026-10-12.md): en el contenedor el SMN
devolvió la página de WAF al arrancar y POST /score quedaba en 503 hasta
reiniciar, aunque el SMN sirvió el libro 3 de 12 veces en el minuto siguiente.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import pytest
from atlas import main

TABLA = {"11007": {"cvegeo": "11007", "category": "NONE", "as_of": "2026-09-30", "name": "Celaya"}}


def test_sin_tabla_al_arrancar_se_reintenta_al_calificar(monkeypatch):
    monkeypatch.setitem(main._state, "drought", {"ok": False, "table": {}, "error": "WAF"})
    monkeypatch.setitem(main._state, "sources", {"conagua_smn": {"ok": False}})
    llamadas = []

    def libro():
        llamadas.append(1)
        return {"ok": True, "table": TABLA, "as_of": "2026-09-30", "rows": 1, "url": "smn"}

    monkeypatch.setattr(main.conagua, "load_drought", libro)
    drought = main._drought_loaded()
    assert drought["table"] == TABLA
    assert main._state["sources"]["conagua_smn"]["ok"] is True
    # Ya cargada, no se vuelve a pedir.
    main._drought_loaded()
    assert len(llamadas) == 1


def test_si_el_reintento_tambien_falla_se_califica_con_la_sequia_ausente(monkeypatch):
    # D-009: sin libro del SMN el sitio se califica con la sequía ausente, en vez
    # de quedarse en 503. Que entonces no publique lo prueba test_capas.py.
    monkeypatch.setitem(main._state, "drought", {"ok": False, "table": {}})
    monkeypatch.setitem(main._state, "sources", {})
    monkeypatch.setitem(main._state, "scores", {})
    intentos = []

    def libro():
        intentos.append(1)
        return {"ok": False, "table": {}, "error": "WAF"}

    monkeypatch.setattr(main.conagua, "load_drought", libro)
    tablas = []
    def observe(site, table):
        tablas.append(table)
        raise _Alto

    monkeypatch.setattr(main, "observe", observe)
    with pytest.raises(_Alto):
        main.score_site("celaya")
    assert intentos == [1]
    assert tablas == [{}]


class _Alto(Exception):
    """Corta antes de salir a la red: lo que se prueba es qué tabla llega."""
