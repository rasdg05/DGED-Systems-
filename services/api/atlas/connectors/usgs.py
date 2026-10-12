"""Sismicidad instrumental: catálogo FDSN de USGS, sin clave.

Medido el 2026-10-12 desde un servidor: responde GeoJSON en menos de un
segundo para los diez sitios de `seed.py` (de 2 a 11 sismos M>=4 en 100 km).

Es un catálogo de sismos registrados, no la regionalización sísmica de CFE ni
un espectro de diseño. Antes de los noventa el catálogo de M4 en el norte de
México está incompleto; eso va en el caveat, no se corrige.
"""
import datetime
import json
import threading
import urllib.parse

from atlas.connectors.http import fetch

BASE = "https://earthquake.usgs.gov/fdsnws/event/1/query"
RADIUS_KM = 100
MIN_MAGNITUDE = 4.0
YEARS = 50

_cache = {}
_lock = threading.Lock()


def query_url(lat, lon, today=None):
    today = today or datetime.date.today()
    start = today.replace(year=today.year - YEARS)
    params = {
        "format": "geojson",
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "maxradiuskm": RADIUS_KM,
        "minmagnitude": MIN_MAGNITUDE,
        "starttime": start.isoformat(),
        "endtime": today.isoformat(),
        "orderby": "magnitude",
    }
    return f"{BASE}?{urllib.parse.urlencode(params)}"


def parse(payload):
    """GeoJSON de FDSN -> resumen. None si no es una respuesta del catálogo."""
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        return None
    features = payload.get("features")
    if not isinstance(features, list):
        return None
    events = []
    for feature in features:
        props = (feature or {}).get("properties") or {}
        mag = props.get("mag")
        if not isinstance(mag, (int, float)):
            continue
        coords = ((feature.get("geometry") or {}).get("coordinates") or [None, None, None]) + [None] * 3
        when = props.get("time")
        date = (
            datetime.datetime.fromtimestamp(when / 1000, tz=datetime.timezone.utc).date().isoformat()
            if isinstance(when, (int, float)) else None
        )
        events.append({
            "id": feature.get("id"),
            "magnitude": float(mag),
            "magType": props.get("magType"),
            "place": props.get("place"),
            "date": date,
            "lon": coords[0],
            "lat": coords[1],
            "depthKm": coords[2],
        })
    events.sort(key=lambda row: row["magnitude"], reverse=True)
    return {
        "count": len(events),
        "maxMagnitude": events[0]["magnitude"] if events else None,
        "strongest": events[0] if events else None,
        "events": events[:5],
    }


def seismicity(lat, lon):
    key = (round(lat, 4), round(lon, 4))
    with _lock:
        cached = _cache.get(key)
    if cached is not None:
        return cached
    url = query_url(lat, lon)
    result = fetch(url, timeout=30)
    summary = None
    if result["ok"]:
        try:
            summary = parse(json.loads(result["body"]))
        except (json.JSONDecodeError, UnicodeDecodeError):
            summary = None
    payload = {
        "ok": summary is not None,
        "url": url,
        "status": result["status"],
        "radiusKm": RADIUS_KM,
        "minMagnitude": MIN_MAGNITUDE,
        "years": YEARS,
        "reason": None if summary is not None else (result.get("error") or "USGS no devolvió un FeatureCollection"),
        **(summary or {"count": None, "maxMagnitude": None, "strongest": None, "events": []}),
    }
    if payload["ok"]:
        with _lock:
            _cache[key] = payload
    return payload


def probe():
    result = seismicity(25.7789, -100.1886)
    return {
        "source": "usgs.fdsn",
        "ok": bool(result["ok"]),
        "url": result["url"],
        "status": result["status"],
        "note": (
            f"Catálogo FDSN de USGS: sismos M>={MIN_MAGNITUDE:g} en {RADIUS_KM} km, últimos {YEARS} años. Sin clave."
            if result["ok"] else "USGS no respondió. El factor sísmico no entra al número."
        ),
    }
