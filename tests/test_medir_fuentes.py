"""Las dos reglas del medidor de fuentes (`herramientas/medir_fuentes.py`), sin red.

1. Un HTTP 200 no es un dato: el WAF del SMN contesta 200 con una página de
   error, y eso es MUERTA, no VIVA.
2. "No medido" no es "medido y no funcionó": sin respuesta HTTP el veredicto es
   NO CONCLUYE, y un 429 es CUOTA. Ninguno de los dos va al cementerio solo.
Ver `MEMORY/FUENTES.md`.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "medir_fuentes", RAIZ / "herramientas" / "medir_fuentes.py"
)
mf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mf)

PAGINA_WAF = (
    b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"><html><head>'
    b"<title>Error</title></head><body><H2>Error</H2>This page can't be displayed. "
    b"Contact support for additional information.</body></html>"
)


def _fijo(monkeypatch, respuesta):
    monkeypatch.setattr(mf, "pedir", lambda url, *a, **k: mf.Respuesta(url, **respuesta))
    monkeypatch.setattr(mf.time, "sleep", lambda s: None)


def test_medidor_200_del_waf_no_es_dato(monkeypatch):
    _fijo(monkeypatch, {"status": 200, "cuerpo": PAGINA_WAF, "latencia": 0.3})
    assert mf.smn_sequia(25.78, -100.19)["veredicto"] == "MUERTA"
    assert mf.smn_webservice(25.78, -100.19)["veredicto"] == "MUERTA"


def test_medidor_xlsx_con_firma_pk_es_viva(monkeypatch):
    _fijo(monkeypatch, {"status": 200, "cuerpo": b"PK\x03\x04resto", "latencia": 0.3})
    res = mf.smn_sequia(25.78, -100.19)
    assert res["veredicto"] == "VIVA"
    assert res["valor"]["con_dato"] == "5/5"


def test_medidor_sin_respuesta_no_concluye(monkeypatch):
    _fijo(monkeypatch, {"status": None, "error": "URLError: reset", "latencia": 7.0})
    for sonda in (mf.cenace_pml, mf.usgs_sismos, mf.nasa_power, mf.smn_sequia):
        assert sonda(25.78, -100.19)["veredicto"] == "NO CONCLUYE", sonda.__name__


def test_medidor_429_es_cuota_no_muerta(monkeypatch):
    _fijo(monkeypatch, {"status": 429, "cuerpo": b'{"error":true}', "latencia": 0.5})
    assert mf.openmeteo_archivo(25.78, -100.19)["veredicto"] == "CUOTA"


def test_medidor_no_publica_la_clave_en_la_url(monkeypatch):
    monkeypatch.setenv("FIRMS_MAP_KEY", "clave-secreta-123")
    monkeypatch.setenv("INEGI_BIE_TOKEN", "token-secreto-456")
    _fijo(monkeypatch, {"status": 400, "cuerpo": b"Invalid MAP_KEY.", "latencia": 0.2})
    firms = mf.nasa_firms(25.78, -100.19)
    bie = mf.inegi_bie(25.78, -100.19)
    assert "clave-secreta-123" not in str(firms)
    assert "token-secreto-456" not in str(bie)
    assert firms["veredicto"] == "CON CLAVE"
