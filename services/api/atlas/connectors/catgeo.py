import json
import os
import threading
from pathlib import Path

from atlas.connectors.http import fetch

BASE = "https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem"
STATES = ("05", "11", "19", "22", "24")
_lock = threading.Lock()
_records = []
_meta = {"ok": False, "loaded": []}


def _cache_dir():
    override = os.environ.get("ATLAS_CACHE")
    if override:
        root = Path(override) / "catgeo"
    else:
        root = Path("/tmp/atlas-cache/catgeo")
        for parent in Path(__file__).resolve().parents:
            if (parent / "ontology").is_dir():
                root = parent / ".cache" / "catgeo"
                break
    root.mkdir(parents=True, exist_ok=True)
    return root


def _bbox(geometry):
    xs = []
    ys = []

    def walk(node):
        if isinstance(node, list) and node and isinstance(node[0], (int, float)):
            xs.append(node[0])
            ys.append(node[1])
            return
        if isinstance(node, list):
            for child in node:
                walk(child)

    walk(geometry.get("coordinates"))
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _in_ring(lon, lat, ring):
    inside = False
    previous = len(ring) - 1
    for index in range(len(ring)):
        xi, yi = ring[index][0], ring[index][1]
        xj, yj = ring[previous][0], ring[previous][1]
        if (yi > lat) != (yj > lat):
            cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < cross:
                inside = not inside
        previous = index
    return inside


def _in_polygon(lon, lat, rings):
    if not rings or not _in_ring(lon, lat, rings[0]):
        return False
    for hole in rings[1:]:
        if hole and _in_ring(lon, lat, hole):
            return False
    return True


def contains(lon, lat, geometry):
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        return _in_polygon(lon, lat, coords)
    if kind == "MultiPolygon":
        return any(_in_polygon(lon, lat, polygon) for polygon in coords)
    return False


def _load_state(code):
    path = _cache_dir() / f"mgem-{code}.json"
    url = f"{BASE}/{code}"
    if not path.exists() or path.stat().st_size < 1000:
        result = fetch(url, timeout=90)
        if not result["ok"]:
            return {"code": code, "ok": False, "url": url, "error": result.get("error")}
        path.write_bytes(result["body"])
    document = json.loads(path.read_text(encoding="utf-8"))
    meta = document.get("metadatos") or {}
    rows = []
    for feature in document.get("features") or []:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        box = _bbox(geometry)
        if not box or not props.get("cvegeo"):
            continue
        rows.append({
            "cvegeo": str(props.get("cvegeo")).zfill(5),
            "name": props.get("nomgeo"),
            "cve_ent": str(props.get("cve_ent") or code).zfill(2),
            "population": _int(props.get("pob_total")),
            "dwellings": _int(props.get("total_viviendas_habitadas")),
            "bbox": box,
            "geometry": geometry,
            "marco": meta.get("Fuente_informacion_vectorial"),
            "census": meta.get("Fuente_informacion_estadistica"),
            "url": url,
        })
    return {"code": code, "ok": True, "url": url, "rows": rows, "marco": meta.get("Fuente_informacion_vectorial")}


def _int(value):
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def preload():
    global _records
    loaded = []
    rows = []
    for code in STATES:
        state = _load_state(code)
        loaded.append({key: state.get(key) for key in ("code", "ok", "url", "error")})
        rows.extend(state.get("rows") or [])
    with _lock:
        _records = rows
        _meta["ok"] = any(item["ok"] for item in loaded)
        _meta["loaded"] = loaded
        _meta["municipalities"] = len(rows)
    return status()


def status():
    with _lock:
        return {
            "source": "inegi.wscatgeo.v2",
            "ok": _meta.get("ok", False),
            "url": BASE,
            "states": list(_meta.get("loaded") or []),
            "municipalities": _meta.get("municipalities", 0),
            "note": "Polígono municipal del Marco Geoestadístico. La población es del Censo 2020.",
        }


def locate(lat, lon):
    with _lock:
        rows = list(_records)
    if not rows:
        preload()
        with _lock:
            rows = list(_records)
    for row in rows:
        minx, miny, maxx, maxy = row["bbox"]
        if not (minx <= lon <= maxx and miny <= lat <= maxy):
            continue
        if contains(lon, lat, row["geometry"]):
            return {
                "ok": True,
                "hit": True,
                "source": "inegi.wscatgeo.v2",
                "url": row["url"],
                "cvegeo": row["cvegeo"],
                "name": row["name"],
                "cve_ent": row["cve_ent"],
                "population": row["population"],
                "dwellings": row["dwellings"],
                "marco": row["marco"],
                "census": row["census"],
            }
    return {
        "ok": bool(rows),
        "hit": False,
        "source": "inegi.wscatgeo.v2",
        "url": BASE,
        "error": "El punto no cayó en los polígonos cargados.",
    }
