"""OpenStreetMap por Overpass, sin clave: subestación más cercana y vía férrea.

Medido el 2026-10-12 desde un servidor:
- `overpass-api.de` corta la conexión (reset) en cada intento, incluso `/api/status`.
- `overpass.kumi.systems` contesta 504 "server is probably too busy" o se agota.
- `maps.mail.ru/osm/tools/overpass` sí entrega JSON (10–50 s), con 504 a ratos.
Por eso se prueban las tres en orden y se anota cuál contestó.

OSM lo editan voluntarios: una subestación o un ramal pueden faltar. Lo que
Overpass devuelve es lo que está mapeado, no el inventario de CFE ni de las
concesionarias ferroviarias. De la subestación sale nombre, voltaje del tag y
distancia; jamás capacidad (D-003).
"""
import json
import math
import threading
import urllib.parse

from atlas.connectors.http import fetch

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
SUBSTATION_RADIUS_M = 25000
RAIL_RADIUS_M = 10000
# Subestaciones particulares de una planta: no son un punto de conexión para el predio.
PRIVATE_KINDS = {"industrial", "minor_distribution"}
NOTE = "OpenStreetMap puede estar incompleto: lo que no está mapeado no aparece."

_cache = {}
_lock = threading.Lock()


def query(lat, lon):
    point = f"{lat:.5f},{lon:.5f}"
    return (
        "[out:json][timeout:40];"
        f'nwr["power"="substation"](around:{SUBSTATION_RADIUS_M},{point});out center tags;'
        f'way["railway"="rail"](around:{RAIL_RADIUS_M},{point});out tags geom;'
    )


def _xy(lat, lon, lat0, lon0):
    """Proyección local en km; basta para distancias de decenas de km."""
    return (
        (lon - lon0) * 111.320 * math.cos(math.radians(lat0)),
        (lat - lat0) * 110.574,
    )


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _segment_km(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def parse_voltage_kv(value):
    """'400000;115000' -> [400.0, 115.0]. Lo que no es número se ignora; sin números, []."""
    if not value:
        return []
    out = []
    for part in str(value).replace(",", ";").split(";"):
        try:
            volts = float(part.strip())
        except ValueError:
            continue
        if volts > 0:
            out.append(round(volts / 1000, 1))
    return sorted(set(out), reverse=True)


def nearest_substation(elements, lat, lon):
    best = None
    skipped = 0
    seen = 0
    for element in elements:
        tags = element.get("tags") or {}
        if tags.get("power") != "substation":
            continue
        center = element.get("center") or {}
        elat = element.get("lat", center.get("lat"))
        elon = element.get("lon", center.get("lon"))
        if elat is None or elon is None:
            continue
        seen += 1
        if tags.get("substation") in PRIVATE_KINDS:
            skipped += 1
            continue
        distance = haversine_km(lat, lon, elat, elon)
        if best is None or distance < best["distanceKm"]:
            voltages = parse_voltage_kv(tags.get("voltage"))
            best = {
                "osmId": f"{element.get('type')}/{element.get('id')}",
                "name": tags.get("name"),
                "operator": tags.get("operator"),
                "kind": tags.get("substation"),
                "voltageKv": voltages[0] if voltages else None,
                "voltagesKv": voltages,
                "voltageTag": tags.get("voltage"),
                "distanceKm": distance,
                "lat": elat,
                "lon": elon,
            }
    if best:
        best["distanceKm"] = round(best["distanceKm"], 2)
    return best, seen, skipped


def nearest_rail(elements, lat, lon):
    best = None
    ways = 0
    px, py = 0.0, 0.0
    for element in elements:
        tags = element.get("tags") or {}
        if element.get("type") != "way" or tags.get("railway") != "rail":
            continue
        geometry = [node for node in (element.get("geometry") or []) if node]
        if len(geometry) < 1:
            continue
        ways += 1
        points = [_xy(node["lat"], node["lon"], lat, lon) for node in geometry]
        if len(points) == 1:
            points = points * 2
        for (ax, ay), (bx, by) in zip(points, points[1:], strict=False):
            distance = _segment_km(px, py, ax, ay, bx, by)
            if best is None or distance < best["distanceKm"]:
                best = {
                    "osmId": f"way/{element.get('id')}",
                    "name": tags.get("name"),
                    "operator": tags.get("operator"),
                    "usage": tags.get("usage"),
                    "service": tags.get("service"),
                    "distanceKm": distance,
                }
    if best:
        best["distanceKm"] = round(best["distanceKm"], 2)
    return best, ways


def parse(payload, lat, lon):
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        return None
    elements = payload["elements"]
    substation, seen, skipped = nearest_substation(elements, lat, lon)
    rail, ways = nearest_rail(elements, lat, lon)
    return {
        "substation": substation,
        "substationsSeen": seen,
        "privateSkipped": skipped,
        "rail": rail,
        "railWays": ways,
        "osmBase": (payload.get("osm3s") or {}).get("timestamp_osm_base"),
    }


def infrastructure(lat, lon):
    key = (round(lat, 4), round(lon, 4))
    with _lock:
        cached = _cache.get(key)
    if cached is not None:
        return cached
    body = urllib.parse.urlencode({"data": query(lat, lon)}).encode()
    attempts = []
    summary = None
    used = None
    for endpoint in ENDPOINTS:
        result = fetch(
            endpoint,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=60,
        )
        attempts.append({"endpoint": endpoint, "status": result["status"], "error": result.get("error")})
        if not result["ok"]:
            continue
        try:
            summary = parse(json.loads(result["body"]), lat, lon)
        except (json.JSONDecodeError, UnicodeDecodeError):
            summary = None
        if summary is not None:
            used = endpoint
            break
    payload = {
        "ok": summary is not None,
        "url": used or ENDPOINTS[0],
        "query": query(lat, lon),
        "attempts": attempts,
        "substationRadiusKm": SUBSTATION_RADIUS_M / 1000,
        "railRadiusKm": RAIL_RADIUS_M / 1000,
        "note": NOTE,
        "reason": None if summary is not None else "Ninguna instancia de Overpass devolvió JSON.",
        **(summary or {"substation": None, "rail": None, "substationsSeen": None, "railWays": None, "osmBase": None}),
    }
    if payload["ok"]:
        with _lock:
            _cache[key] = payload
    return payload


def probe():
    """Sin consulta pesada al arrancar: un `out count` de un radio chico."""
    body = urllib.parse.urlencode({"data": '[out:json][timeout:20];nwr["power"="substation"](around:2000,25.7789,-100.1886);out count;'}).encode()
    attempts = []
    for endpoint in ENDPOINTS:
        result = fetch(endpoint, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
        ok = result["ok"] and result["body"].lstrip().startswith(b"{")
        attempts.append({"endpoint": endpoint, "status": result["status"], "ok": ok})
        if ok:
            return {"source": "osm.overpass", "ok": True, "url": endpoint, "attempts": attempts, "note": NOTE}
    return {
        "source": "osm.overpass",
        "ok": False,
        "url": ENDPOINTS[0],
        "attempts": attempts,
        "note": "Ninguna instancia de Overpass respondió en el arranque. Subestación y vía férrea quedan ausentes. " + NOTE,
    }
