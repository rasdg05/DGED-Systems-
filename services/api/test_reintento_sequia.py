"""Si el arranque cayó en la página de error del SMN, calificar reintenta.

Medido 2026-10-12 (docs/verificacion-2026-10-12.md): en el contenedor el SMN
devolvió la página de WAF al arrancar y POST /score quedaba en 503 hasta
reiniciar, aunque el SMN sirvió el libro 3 de 12 veces en el minuto siguiente.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import pytest
from fastapi import HTTPException

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


def test_si_el_reintento_tambien_falla_sigue_en_503(monkeypatch):
    monkeypatch.setitem(main._state, "drought", {"ok": False, "table": {}})
    monkeypatch.setitem(main._state, "sources", {})
    monkeypatch.setattr(main.conagua, "load_drought", lambda: {"ok": False, "table": {}, "error": "WAF"})
    with pytest.raises(HTTPException) as error:
        main.score_site("celaya")
    assert error.value.status_code == 503
