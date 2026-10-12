import html
import math
import re
import urllib.parse

from atlas.connectors.http import fetch

WMS = "https://gaia.inegi.org.mx/NLB/tunnel/wms/wms61"

LAYERS = {
    "municipios": {"id": "c101", "title": "Municipios, marco geoestadístico INEGI"},
    "inundacion": {"id": "c463", "title": "Inundación, área"},
    "inundacion_zona": {"id": "c424", "title": "Zona de inundación"},
    "uso_suelo": {"id": "c783", "title": "Uso de suelo y vegetación serie VII"},
}


def municipality_from_cells(cells):
    for index, cell in enumerate(cells):
        if re.fullmatch(r"\d{5}", cell) and index + 1 < len(cells):
            name = cells[index + 1]
            if name and not name.isdigit():
                return cell, name
    return None, None


def _td_cells(body):
    text = html.unescape(body)
    cells = re.findall(r"<td[^>]*>(.*?)</td>", text, flags=re.I | re.S)
    clean = []
    for cell in cells:
        value = re.sub(r"<[^>]+>", "", cell).strip()
        if value:
            clean.append(value)
    return clean


def feature_info(layer_id, lat, lon, info_format="text/html"):
    delta = 0.02
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": layer_id,
        "QUERY_LAYERS": layer_id,
        "CRS": "EPSG:4326",
        "BBOX": f"{lat - delta},{lon - delta},{lat + delta},{lon + delta}",
        "WIDTH": "101",
        "HEIGHT": "101",
        "I": "50",
        "J": "50",
        "INFO_FORMAT": info_format,
        "FEATURE_COUNT": "1",
    }
    url = f"{WMS}?{urllib.parse.urlencode(params)}"
    result = fetch(url, timeout=30)
    result["requested_url"] = url
    if not result["ok"]:
        return result
    charset = "utf-8"
    match = re.search(r"charset=([\w-]+)", result["content_type"], re.I)
    if match:
        charset = match.group(1)
    try:
        result["text"] = result["body"].decode(charset)
    except LookupError:
        result["text"] = result["body"].decode("utf-8", "replace")
    except UnicodeDecodeError:
        result["text"] = result["body"].decode("latin-1", "replace")
    return result


def municipality_at(lat, lon):
    result = feature_info(LAYERS["municipios"]["id"], lat, lon, "text/html")
    parsed = {
        "source": "inegi.wms.c101",
        "ok": result["ok"],
        "url": result.get("requested_url"),
        "status": result["status"],
        "error": result.get("error"),
    }
    if not result["ok"]:
        return parsed
    cells = _td_cells(result["text"])
    parsed["cells"] = cells
    cvegeo, name = municipality_from_cells(cells)
    if cvegeo:
        parsed["hit"] = True
        parsed["cvegeo"] = cvegeo
        parsed["name"] = name
    else:
        parsed["hit"] = False
    return parsed


def land_use_at(lat, lon):
    result = feature_info(LAYERS["uso_suelo"]["id"], lat, lon, "text/html")
    parsed = {
        "source": "inegi.wms.c783",
        "ok": result["ok"],
        "url": result.get("requested_url"),
        "status": result["status"],
        "error": result.get("error"),
    }
    if not result["ok"]:
        return parsed
    cells = _td_cells(result["text"])
    parsed["cells"] = cells
    if cells:
        parsed["hit"] = True
        parsed["name"] = cells[-1]
    else:
        parsed["hit"] = False
    return parsed


def flood_at(lat, lon):
    for key in ("inundacion", "inundacion_zona"):
        layer = LAYERS[key]
        result = feature_info(layer["id"], lat, lon, "text/plain")
        if not result["ok"]:
            return {
                "source": f"inegi.wms.{layer['id']}",
                "ok": False,
                "known": False,
                "url": result.get("requested_url"),
                "status": result["status"],
                "error": result.get("error"),
            }
        text = result["text"]
        if "no results" in text.lower():
            continue
        if "Feature" in text:
            return {
                "source": f"inegi.wms.{layer['id']}",
                "ok": True,
                "known": True,
                "hit": True,
                "layer": layer["id"],
                "url": result.get("requested_url"),
                "excerpt": text[:400],
            }
    return {
        "source": "inegi.wms.c463",
        "ok": True,
        "known": True,
        "hit": False,
        "layer": "c463",
        "url": result.get("requested_url") if result else None,
    }


def denue_window(lat, lon):
    """Muestra de manufactura bajo una ventana del GeoServer. No es un conteo."""
    delta = 0.03
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": "denue:industrias_manufactureras",
        "QUERY_LAYERS": "denue:industrias_manufactureras",
        "SRS": "EPSG:4326",
        "BBOX": f"{lon - delta},{lat - delta},{lon + delta},{lat + delta}",
        "WIDTH": "101",
        "HEIGHT": "101",
        "X": "50",
        "Y": "50",
        "INFO_FORMAT": "application/json",
        "FEATURE_COUNT": "5",
    }
    url = f"https://gaia.inegi.org.mx/geoserver/wms?{urllib.parse.urlencode(params)}"
    result = fetch(url, timeout=40)
    text = result["body"].decode("utf-8", "replace") if result["body"] else ""
    sample = []
    if result["ok"]:
        try:
            import json
            document = json.loads(text)
        except json.JSONDecodeError:
            document = {}
        for feature in (document.get("features") or [])[:5]:
            props = feature.get("properties") or {}
            sample.append({
                "name": props.get("nom_estab"),
                "activity": props.get("nombre_act"),
                "staff": props.get("per_ocu"),
                "municipality": props.get("municipio"),
            })
    return {
        "ok": result["ok"] and bool(sample),
        "configured": False,
        "count": None,
        "mode": "ventana",
        "sample": sample,
        "reason": (
            "Muestra de la ventana GeoServer, no un conteo de 1.5 km. El conteo espera INEGI_TOKEN."
            if sample
            else (text[:160] or result.get("error") or "sin establecimientos en la ventana")
        ),
        "url": url,
        "radius_m": None,
    }


def denue_search(lat, lon, token, radius_m=1500, condition="manufactura"):
    if not token:
        return denue_window(lat, lon)
    url = (
        "https://www.inegi.org.mx/app/api/denue/v1/consulta/Buscar/"
        f"{urllib.parse.quote(condition)}/{lat},{lon}/{int(radius_m)}/{urllib.parse.quote(token)}"
    )
    result = fetch(url, timeout=30)
    text = result["body"].decode("utf-8", "replace")
    public_url = url.replace(token, "***")
    if not result["ok"] or "No Autorizado" in text or text.strip().startswith("No Autorizado"):
        window = denue_window(lat, lon)
        window["reason"] = (text[:160] or "clave DENUE rechazada") + " " + (window.get("reason") or "")
        window["url"] = public_url
        return window
    try:
        import json
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "configured": True,
            "count": None,
            "mode": "radio",
            "sample": [],
            "reason": text[:180],
            "url": public_url,
            "status": result["status"],
            "radius_m": radius_m,
        }
    rows = payload if isinstance(payload, list) else []
    return {
        "ok": True,
        "configured": True,
        "count": len(rows),
        "mode": "radio",
        "sample": [
            {"name": row.get("Nombre"), "activity": row.get("Clase_actividad")}
            for row in rows[:8]
            if isinstance(row, dict)
        ],
        "url": public_url,
        "radius_m": radius_m,
    }


def mercator_bbox(z, x, y):
    def lon(px):
        return px / (2 ** z) * 360.0 - 180.0

    def lat(py):
        n = math.pi - 2.0 * math.pi * py / (2 ** z)
        return math.degrees(math.atan(math.sinh(n)))

    west, east = lon(x), lon(x + 1)
    north, south = lat(y), lat(y + 1)

    def mx(value):
        return value * 20037508.342789244 / 180.0

    def my(value):
        value = max(min(value, 85.05112878), -85.05112878)
        return math.log(math.tan((90 + value) * math.pi / 360.0)) * 20037508.342789244 / math.pi

    return mx(west), my(south), mx(east), my(north)


def wms_tile(layer_id, z, x, y):
    minx, miny, maxx, maxy = mercator_bbox(z, x, y)
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetMap",
        "LAYERS": layer_id,
        "STYLES": "",
        "FORMAT": "image/png",
        "TRANSPARENT": "true",
        "CRS": "EPSG:3857",
        "WIDTH": "256",
        "HEIGHT": "256",
        "BBOX": f"{minx},{miny},{maxx},{maxy}",
    }
    url = f"{WMS}?{urllib.parse.urlencode(params)}"
    result = fetch(url, timeout=30)
    result["requested_url"] = url
    return result
