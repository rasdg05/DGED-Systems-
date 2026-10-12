"""Clima de los últimos cinco años: NASA POWER (MERRA-2), sin clave.

Se pidió Open-Meteo archive y se midió primero el 2026-10-12: desde un
servidor responde 429 "Daily API request limit exceeded" (cuota por IP
compartida), así que no se escribió y quedó en el cementerio. POWER sí
respondió: 200 en medio segundo, 1,826 días sin valores de relleno.

Es una celda de reanálisis de ~0.5°, no una estación del SMN ni el predio. Se
muestra y no entra al número.
"""
import datetime
import json
import threading
import urllib.parse

from atlas.connectors.http import fetch

BASE = "https://power.larc.nasa.gov/api/temporal/daily/point"
YEARS = 5
HOT_DAY_C = 35.0
FILL = -999.0

_cache = {}
_lock = threading.Lock()


def window(today=None):
    """Los últimos cinco años calendario completos."""
    today = today or datetime.date.today()
    last = today.year - 1
    return last - YEARS + 1, last


def query_url(lat, lon, today=None):
    first, last = window(today)
    params = {
        "parameters": "PRECTOTCORR,T2M_MAX",
        "community": "RE",
        "longitude": round(lon, 4),
        "latitude": round(lat, 4),
        "start": f"{first}0101",
        "end": f"{last}1231",
        "format": "JSON",
    }
    return f"{BASE}?{urllib.parse.urlencode(params)}"


def parse(payload):
    """Respuesta diaria de POWER -> lluvia anual y días calurosos por año.

    Un año entra solo si trae los 365/366 días de ambas variables sin relleno.
    """
    if not isinstance(payload, dict):
        return None
    params = ((payload.get("properties") or {}).get("parameter") or {})
    rain = params.get("PRECTOTCORR")
    tmax = params.get("T2M_MAX")
    if not isinstance(rain, dict) or not isinstance(tmax, dict):
        return None
    fill = (payload.get("header") or {}).get("fill_value", FILL)
    years = {}
    for day, value in rain.items():
        row = years.setdefault(day[:4], {"rainMm": 0.0, "hotDays": 0, "days": 0, "bad": 0})
        hot = tmax.get(day)
        if not isinstance(value, (int, float)) or not isinstance(hot, (int, float)) or value == fill or hot == fill:
            row["bad"] += 1
            continue
        row["days"] += 1
        row["rainMm"] += value
        if hot > HOT_DAY_C:
            row["hotDays"] += 1
    by_year = []
    for year in sorted(years):
        row = years[year]
        expected = 366 if datetime.date(int(year), 12, 31).timetuple().tm_yday == 366 else 365
        if row["bad"] or row["days"] != expected:
            continue
        by_year.append({"year": int(year), "precipitationMm": round(row["rainMm"], 1), "hotDays": row["hotDays"]})
    if not by_year:
        return None
    n = len(by_year)
    return {
        "years": by_year,
        "yearsComplete": n,
        "annualPrecipitationMm": round(sum(row["precipitationMm"] for row in by_year) / n, 1),
        "hotDaysPerYear": round(sum(row["hotDays"] for row in by_year) / n, 1),
        "hotDayThresholdC": HOT_DAY_C,
        "period": f"{by_year[0]['year']}-{by_year[-1]['year']}",
        "cell": (payload.get("geometry") or {}).get("coordinates"),
    }


def climate(lat, lon):
    key = (round(lat, 4), round(lon, 4))
    with _lock:
        cached = _cache.get(key)
    if cached is not None:
        return cached
    url = query_url(lat, lon)
    result = fetch(url, timeout=60)
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
        "reason": None if summary is not None else (result.get("error") or "POWER no devolvió años completos"),
        **(summary or {"annualPrecipitationMm": None, "hotDaysPerYear": None, "years": [], "period": None}),
    }
    if payload["ok"]:
        with _lock:
            _cache[key] = payload
    return payload


def probe():
    result = climate(25.7789, -100.1886)
    return {
        "source": "nasa.power",
        "ok": bool(result["ok"]),
        "url": result["url"],
        "status": result["status"],
        "note": (
            "NASA POWER diario (MERRA-2): lluvia anual y días arriba de 35 °C, últimos cinco años completos. Se muestra, no puntúa."
            if result["ok"] else "POWER no respondió. La ficha enseña el clima como ausente."
        ),
        "replaces": "Open-Meteo archive respondió 429 por cuota desde un servidor (cementerio, 2026-10-12).",
    }
