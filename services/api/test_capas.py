"""Capas sin clave de atlas-live-0.2.0 (D-009): sismicidad, clima, subestación y vía férrea.

Sin red: los fixtures son respuestas reales recortadas del 2026-10-12
(`fixtures/`, cada uno dice qué se le quitó).
"""
import itertools
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from atlas.connectors import osm, power, usgs
from atlas.score import EXTRA_WEIGHTS, MODEL_VERSION, _base_weights, _weights, score_observation

FIXTURES = Path(__file__).resolve().parent / "fixtures"
APODACA = (25.7789, -100.1886)
MARQUES = (20.5950, -100.3120)

CORE = {
    "drought": "D0",
    "flood_hit": False,
    "flood_known": True,
    "land_known": True,
    "land_name": "ASENTAMIENTOS HUMANOS",
}


def _fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _fake_fetch(body, ok=True, status=200):
    def fake(url, timeout=25, headers=None, data=None):
        return {"ok": ok, "status": status, "url": url, "content_type": "application/json", "body": body}
    return fake


# --- conectores contra respuestas reales -------------------------------------------------

def test_usgs_parses_real_catalog():
    apodaca = usgs.parse(_fixture("usgs_apodaca-industrial.json"))
    marques = usgs.parse(_fixture("usgs_el-marques.json"))
    assert apodaca["count"] == 10 and apodaca["maxMagnitude"] == 4.6
    assert marques["count"] == 5 and marques["maxMagnitude"] == 5.3
    assert marques["strongest"]["date"] == "1979-02-22"
    assert usgs.parse({"error": "x"}) is None


def test_usgs_empty_catalog_is_an_answer():
    summary = usgs.parse({"type": "FeatureCollection", "features": []})
    assert summary["count"] == 0 and summary["maxMagnitude"] is None
    scored = score_observation({**CORE, "seismic_known": True, "seismic_max_magnitude": None})
    seismic = next(f for f in scored["factors"] if f["key"] == "seismic")
    assert seismic["score"] == 90 and "seismic" in scored["weights"]


def test_power_parses_five_complete_years():
    apodaca = power.parse(_fixture("power_apodaca-industrial.json"))
    marques = power.parse(_fixture("power_el-marques.json"))
    assert apodaca["yearsComplete"] == 5 and apodaca["period"] == "2021-2025"
    assert apodaca["annualPrecipitationMm"] == 536.9
    assert apodaca["hotDaysPerYear"] == 118.0
    assert marques["hotDaysPerYear"] == 2.0


def test_power_drops_a_year_with_fill_values():
    payload = _fixture("power_el-marques.json")
    payload["properties"]["parameter"]["T2M_MAX"]["20230615"] = -999.0
    parsed = power.parse(payload)
    assert [row["year"] for row in parsed["years"]] == [2021, 2022, 2024, 2025]
    assert power.window(__import__("datetime").date(2026, 10, 12)) == (2021, 2025)


def test_overpass_nearest_substation_and_rail():
    apodaca = osm.parse(_fixture("overpass_apodaca-industrial.json"), *APODACA)
    assert apodaca["substation"]["kind"] == "transmission"
    assert apodaca["substation"]["voltageKv"] == 115.0
    assert apodaca["substation"]["distanceKm"] == 2.38
    assert apodaca["privateSkipped"] > 0  # las de planta (substation=industrial) no cuentan
    assert apodaca["rail"]["distanceKm"] == 0.93
    marques = osm.parse(_fixture("overpass_el-marques.json"), *MARQUES)
    assert marques["substation"]["name"] == "Conín"
    assert marques["substation"]["voltagesKv"] == [230.0, 115.0]
    assert marques["rail"]["operator"] == "Ferromex"
    assert marques["rail"]["distanceKm"] == 2.51


def test_unknown_voltage_is_null():
    element = {"type": "way", "id": 1, "center": {"lat": 25.78, "lon": -100.19}, "tags": {"power": "substation"}}
    best, _, _ = osm.nearest_substation([element], *APODACA)
    assert best["voltageKv"] is None and best["voltagesKv"] == []
    assert osm.parse_voltage_kv("medium") == []
    assert osm.parse_voltage_kv("400000;115000") == [400.0, 115.0]


def test_overpass_falls_back_to_the_next_instance(monkeypatch):
    osm._cache.clear()
    body = (FIXTURES / "overpass_el-marques.json").read_bytes()
    calls = []

    def fake(url, timeout=25, headers=None, data=None):
        calls.append(url)
        if url == osm.ENDPOINTS[0]:
            return {"ok": False, "status": 0, "url": url, "body": b"", "error": "Connection reset by peer"}
        return {"ok": True, "status": 200, "url": url, "body": body}

    monkeypatch.setattr(osm, "fetch", fake)
    result = osm.infrastructure(*MARQUES)
    assert result["ok"] and result["url"] == osm.ENDPOINTS[1]
    assert calls == osm.ENDPOINTS[:2]
    assert result["attempts"][0]["error"] == "Connection reset by peer"
    osm._cache.clear()


def test_failed_sources_report_not_ok(monkeypatch):
    for module in (osm, power, usgs):
        module._cache.clear()
        monkeypatch.setattr(module, "fetch", _fake_fetch(b'{"reason":"Daily API request limit exceeded"}', ok=False, status=429))
    assert usgs.seismicity(*APODACA)["ok"] is False
    assert power.climate(*APODACA)["ok"] is False
    infra = osm.infrastructure(*APODACA)
    assert infra["ok"] is False and infra["substation"] is None and infra["rail"] is None
    assert not osm._cache and not power._cache and not usgs._cache  # lo que falló no se recuerda


# --- (a) sin respuesta no mueve el número ------------------------------------------------

def test_unanswered_layers_do_not_move_the_number():
    base = score_observation(dict(CORE))
    silent = score_observation({
        **CORE,
        "seismic_known": False,
        "seismic_max_magnitude": 7.9,  # un dato suelto sin respuesta de la fuente no cuenta
        "rail_known": False,
        "rail_distance_km": 0.1,
    })
    assert silent["composite"] == base["composite"]
    assert silent["weights"] == base["weights"] == {"drought": 0.40, "flood": 0.30, "land": 0.30}
    assert silent["coverage"] == base["coverage"]
    missing = {f["key"]: f["missing"] for f in silent["factors"]}
    assert missing["seismic"] is True and missing["rail"] is True
    assert MODEL_VERSION == "atlas-live-0.2.0"


def test_answered_layers_enter_the_number():
    base = score_observation(dict(CORE))
    near = score_observation({**CORE, "rail_known": True, "rail_distance_km": 0.9})
    quiet = score_observation({**CORE, "seismic_known": True, "seismic_max_magnitude": 6.8})
    assert near["weights"]["rail"] == 0.10 and near["composite"] > base["composite"]
    assert quiet["weights"]["seismic"] == 0.08 and quiet["composite"] < base["composite"]
    nothing_mapped = score_observation({**CORE, "rail_known": True, "rail_distance_km": None})
    rail = next(f for f in nothing_mapped["factors"] if f["key"] == "rail")
    assert rail["score"] == 36 and rail["missing"] is False


def test_layers_are_not_publish_gates():
    result = score_observation({**CORE, "land_known": False, "seismic_known": True, "rail_known": True, "rail_distance_km": 1})
    assert result["publishable"] is False


# --- (b) los pesos suman 1 en cada combinación ----------------------------------------

def test_weights_sum_to_one_in_every_combination():
    for denue, route, seismic, rail in itertools.product([False, True], repeat=4):
        weights = _weights(denue, route, seismic, rail)
        assert abs(sum(weights.values()) - 1) < 1e-9, (denue, route, seismic, rail, weights)
        assert ("seismic" in weights) is seismic and ("rail" in weights) is rail
        if not seismic and not rail:
            assert weights == _base_weights(denue, route)
        for key in ("seismic", "rail"):
            if key in weights:
                assert weights[key] == EXTRA_WEIGHTS[key]


def test_full_observation_weights_sum_to_one():
    result = score_observation({
        **CORE,
        "denue_count": 12,
        "route_minutes": 80,
        "seismic_known": True,
        "seismic_max_magnitude": 4.6,
        "rail_known": True,
        "rail_distance_km": 0.93,
    })
    assert abs(sum(result["weights"].values()) - 1) < 1e-9
    assert result["coverage"] == 1


# --- (c) la subestación nunca afirma capacidad ----------------------------------------

def _observation_from_fixtures():
    seismic = usgs.parse(_fixture("usgs_apodaca-industrial.json"))
    climate = power.parse(_fixture("power_apodaca-industrial.json"))
    infra = osm.parse(_fixture("overpass_apodaca-industrial.json"), *APODACA)
    sub, rail = infra["substation"], infra["rail"]
    return {
        **CORE,
        "cvegeo": "19006",
        "municipality": "Apodaca",
        "seismic_known": True,
        "seismic_count": seismic["count"],
        "seismic_max_magnitude": seismic["maxMagnitude"],
        "seismic_strongest": seismic["strongest"],
        "seismic_radius_km": 100,
        "seismic_years": 50,
        "climate_known": True,
        "climate_precip_mm": climate["annualPrecipitationMm"],
        "climate_hot_days": climate["hotDaysPerYear"],
        "climate_period": climate["period"],
        "osm_known": True,
        "substation_name": sub["name"],
        "substation_voltage_kv": sub["voltageKv"],
        "substation_distance_km": sub["distanceKm"],
        "substation_kind": sub["kind"],
        "substation_operator": sub["operator"],
        "substation_osm_id": sub["osmId"],
        "substation_radius_km": 25,
        "rail_known": True,
        "rail_distance_km": rail["distanceKm"],
        "rail_radius_km": 10,
    }


CAPACITY_WORDS = ("mw", "megawatt", "capacity", "capacidad", "headroom", "holgura", "disponible", "available")
CAPACITY_CLAIM = re.compile(r"\d[\d.,]*\s*(MW|megawatts?)\b|MW\s+disponibles|capacidad\s+disponible", re.IGNORECASE)


def _substations(observation):
    from atlas.main import materialize
    site = {"id": "apodaca-industrial", "name": "Apodaca", "corridor": "norte", "lat": APODACA[0], "lon": APODACA[1]}
    graph = materialize(site, observation, score_observation(observation))
    return [o for o in graph["objects"] if o["type"] == "SubestacionAprox"], graph


def test_substation_never_claims_capacity():
    for observation in (_observation_from_fixtures(), {**CORE, "osm_known": False}, {**CORE, "osm_known": True}):
        subs, _ = _substations(observation)
        assert len(subs) == 1
        sub = subs[0]
        bad_keys = [key for key in sub if any(word in key.lower() for word in CAPACITY_WORDS)]
        assert not bad_keys, bad_keys
        text = json.dumps(sub, ensure_ascii=False)
        assert not CAPACITY_CLAIM.search(text), text
        assert "disponible" not in text.lower()


def test_substation_is_filled_from_osm():
    subs, graph = _substations(_observation_from_fixtures())
    sub = subs[0]
    assert sub["source"] == "osm" and sub["empty"] is False
    assert sub["voltageKv"] == 115.0 and sub["distanceKm"] == 2.38
    assert "incompleto" in sub["reason"]
    types = {o["type"] for o in graph["objects"]}
    assert {"RiesgoSismico", "RiesgoClimatico", "SubestacionAprox"} <= types
    climate = next(o for o in graph["objects"] if o["type"] == "RiesgoClimatico")
    assert climate["annualPrecipitationMm"] == 536.9 and climate["climateSource"] == "nasa.power"
    site = next(o for o in graph["objects"] if o["type"] == "Sitio")
    assert site["railDistanceKm"] == 0.93 and site["railSource"] == "osm.overpass"


def test_substation_without_answer_stays_empty():
    subs, _ = _substations({**CORE, "osm_known": False, "osm_reason": "Ninguna instancia de Overpass devolvió JSON."})
    sub = subs[0]
    assert sub["empty"] is True and sub["voltageKv"] is None and sub["distanceKm"] is None and sub["source"] is None


# --- el error de al lado: el SMN devolvió HTML con 200 y tumbaba el arranque ------------

def test_smn_html_error_page_is_not_a_workbook(monkeypatch, tmp_path):
    from atlas.connectors import conagua
    monkeypatch.setenv("ATLAS_CACHE", str(tmp_path))
    page = b"<!DOCTYPE html><html><head><title>Error</title></head><body>This page can't be displayed.</body></html>"
    (tmp_path / "MunicipiosSequia.xlsx").write_bytes(page * 20)  # una página de error ya guardada
    monkeypatch.setattr(conagua, "fetch", _fake_fetch(page))
    loaded = conagua.load_drought()
    assert loaded["ok"] is False and loaded["table"] == {}
    assert "no es un xlsx" in loaded["error"]
    assert not (tmp_path / "MunicipiosSequia.xlsx").exists()


def test_without_drought_book_the_site_scores_but_does_not_publish():
    result = score_observation({**CORE, "drought": None, "drought_reason": "HTTP 200: no es un xlsx",
                                "seismic_known": True, "seismic_max_magnitude": 4.6})
    drought = result["factors"][0]
    assert drought["missing"] is True and drought["raw"]["reason"] == "HTTP 200: no es un xlsx"
    assert result["publishable"] is False and result["composite"] is not None
