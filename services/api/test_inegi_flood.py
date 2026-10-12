"""Inundación: solo "Search returned no results" en las dos capas es "sin inundación".

Medido 2026-10-12 (docs/verificacion-2026-10-12.md): el WMS de INEGI contesta
texto plano "Search returned no results." o "Layer 'c424' / Feature 1691"
(Tlacotalpan). Cualquier otra cosa con HTTP 200 —el mismo día el SMN devolvió
una página de error de WAF con 200— caía al final y salía como "no inundable",
84 puntos inventados.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from atlas.connectors import inegi
from atlas.score import score_observation

SIN_RESULTADOS = "GetFeatureInfo results:\n\n  Search returned no results.\n"
CON_FEATURE = "GetFeatureInfo results:\n\nLayer 'c424'\n  Feature 1691: \n"
PAGINA_DE_ERROR = "<html><body><H2>Error</H2>This page can't be displayed.</body></html>"


def _wms(respuestas):
    cola = list(respuestas)

    def fake(layer_id, lat, lon, info_format="text/html"):
        return {"ok": True, "status": 200, "text": cola.pop(0), "requested_url": f"wms?{layer_id}"}

    return fake


def test_dos_capas_sin_resultados_es_sin_inundacion(monkeypatch):
    monkeypatch.setattr(inegi, "feature_info", _wms([SIN_RESULTADOS, SIN_RESULTADOS]))
    flood = inegi.flood_at(18.61, -95.66)
    assert flood["known"] is True and flood["hit"] is False


def test_feature_en_la_segunda_capa_es_inundable(monkeypatch):
    monkeypatch.setattr(inegi, "feature_info", _wms([SIN_RESULTADOS, CON_FEATURE]))
    flood = inegi.flood_at(18.61, -95.66)
    assert flood["known"] is True and flood["hit"] is True and flood["layer"] == "c424"


def test_respuesta_rara_con_200_no_es_sin_inundacion(monkeypatch):
    monkeypatch.setattr(inegi, "feature_info", _wms([PAGINA_DE_ERROR, SIN_RESULTADOS]))
    flood = inegi.flood_at(25.7789, -100.1886)
    assert flood["known"] is False
    score = score_observation({
        "drought": "D0",
        "flood_known": flood["known"],
        "flood_hit": bool(flood.get("hit")),
        "land_known": True,
        "land_name": "ASENTAMIENTOS HUMANOS",
    })
    inundacion = next(f for f in score["factors"] if f["key"] == "flood")
    assert inundacion["score"] is None and inundacion["missing"] is True
    assert score["publishable"] is False
