import json
import urllib.parse

from atlas.connectors.http import fetch

BASE = "https://gaia.inegi.org.mx/sakbe_v3.1"
TOKEN_URL = f"{BASE}/genera_token.jsp"

# Puntos públicos de referencia. La ruta es de línea de red a línea de red, no de portón a portón.
REFERENCES = {
    "norte": {"name": "Puente Colombia", "lon": -99.748, "lat": 27.700},
    "bajio": {"name": "Puerto de Altamira", "lon": -97.921, "lat": 22.393},
}


def _post(path, fields):
    url = f"{BASE}/{path}"
    result = fetch(
        url,
        data=urllib.parse.urlencode(fields).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=40,
    )
    text = result["body"].decode("utf-8", "replace") if result["body"] else ""
    if text.startswith("\x1f"):
        text = result["body"].decode("latin-1", "replace")
    payload = None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    return {"ok": result["ok"], "status": result["status"], "url": url, "json": payload, "text": text[:300], "error": result.get("error")}


def _message(payload, fallback):
    if not isinstance(payload, dict):
        return fallback
    response = payload.get("response") or {}
    return response.get("message") or fallback


def _line(lon, lat, token):
    result = _post("buscalinea", {
        "type": "json",
        "key": token,
        "x": lon,
        "y": lat,
        "escala": "100000",
    })
    payload = result["json"] or {}
    data = payload.get("data")
    row = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else None
    if not isinstance(row, dict):
        return None, result
    line = {
        "id": row.get("id") or row.get("ID") or row.get("id_red"),
        "source": row.get("source") or row.get("source_i"),
        "target": row.get("target") or row.get("target_i"),
    }
    if line["id"] is None or line["source"] is None or line["target"] is None:
        return None, result
    return line, result


def _minutes(payload):
    if not isinstance(payload, dict):
        return None, None
    data = payload.get("data")
    row = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else payload
    if not isinstance(row, dict):
        return None, None
    minutes = row.get("tiempo_min")
    kilometers = row.get("long_km")
    try:
        minutes = float(minutes)
    except (TypeError, ValueError):
        minutes = None
    try:
        kilometers = float(kilometers)
    except (TypeError, ValueError):
        kilometers = None
    return minutes, kilometers


def route(lon, lat, corridor, token):
    reference = REFERENCES.get(corridor) or REFERENCES["norte"]
    if not token:
        return {
            "ok": False,
            "configured": False,
            "minutes": None,
            "kilometers": None,
            "reference": reference["name"],
            "reason": "SAKBE_TOKEN ausente",
            "url": TOKEN_URL,
        }
    origin, origin_call = _line(lon, lat, token)
    destination, destination_call = _line(reference["lon"], reference["lat"], token)
    if origin is None or destination is None:
        failed = origin_call if origin is None else destination_call
        return {
            "ok": False,
            "configured": True,
            "minutes": None,
            "kilometers": None,
            "reference": reference["name"],
            "reason": _message(failed.get("json"), failed.get("text") or failed.get("error") or "sin línea de red"),
            "url": failed.get("url"),
        }
    result = _post("optima", {
        "type": "json",
        "key": token,
        "id_i": origin["id"],
        "source_i": origin["source"],
        "target_i": origin["target"],
        "id_f": destination["id"],
        "source_f": destination["source"],
        "target_f": destination["target"],
        "v": "1",
    })
    minutes, kilometers = _minutes(result["json"])
    success = bool((result["json"] or {}).get("response", {}).get("success", minutes is not None))
    if minutes is None:
        success = False
    public = dict(result)
    return {
        "ok": success,
        "configured": True,
        "minutes": minutes,
        "kilometers": kilometers,
        "reference": reference["name"],
        "vehicle": "automóvil",
        "reason": None if success else _message(result["json"], result["text"] or "sin tiempo de ruta"),
        "url": result["url"],
    }


def probe():
    result = _post("optima", {"type": "json", "key": "", "v": "1"})
    message = _message(result["json"], result["text"])
    alive = result["ok"] and "autorizada" in (message or "").lower() or (result["json"] or {}).get("response", {}).get("success") is False
    return {
        "source": "inegi.sakbe",
        "ok": bool(result["ok"]),
        "configured": False,
        "url": TOKEN_URL,
        "endpoint": f"{BASE}/optima",
        "reason": message,
        "note": "El endpoint responde. Sin SAKBE_TOKEN la ruta no entra al número." if alive else "SAKBÉ no entregó una respuesta usable.",
    }
