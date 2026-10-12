import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from atlas import access, oracle
from atlas.connectors import catgeo, conagua, datosgob, inegi, osm, power, sakbe, usgs
from atlas.db import ensure as ensure_db
from atlas.db import save_score
from atlas.score import score_observation
from atlas.seed import CORRIDORS, SITES

ROOT = Path(__file__).resolve()
ONTOLOGY_PATH = Path(os.environ.get("ONTOLOGY_PATH", ""))
if not ONTOLOGY_PATH.is_file():
    for parent in ROOT.parents:
        candidate = parent / "ontology" / "atlas.ontology.json"
        if candidate.is_file():
            ONTOLOGY_PATH = candidate
            break
STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="DGED Atlas", version="0.1.0")

_state = {
    "drought": None,
    "sources": {},
    "scores": {},
    "examples": [],
}
_lock = threading.Lock()
_tile_cache = {}
_tile_lock = threading.Lock()


def _remember(example):
    with _lock:
        _state["examples"] = ([example] + _state["examples"])[:12]


def _ontology():
    return json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))


_pool = ThreadPoolExecutor(max_workers=6)


def observe(site, drought_table):
    # Las tres capas sin clave van en paralelo: Overpass sola tarda de 10 a 50 s.
    seismic_job = _pool.submit(usgs.seismicity, site["lat"], site["lon"])
    climate_job = _pool.submit(power.climate, site["lat"], site["lon"])
    infra_job = _pool.submit(osm.infrastructure, site["lat"], site["lon"])
    municipality = catgeo.locate(site["lat"], site["lon"])
    if not municipality.get("hit"):
        fallback = inegi.municipality_at(site["lat"], site["lon"])
        fallback["fallback"] = True
        municipality = fallback
    land = inegi.land_use_at(site["lat"], site["lon"])
    flood = inegi.flood_at(site["lat"], site["lon"])
    token = os.environ.get("INEGI_TOKEN", "").strip()
    denue = inegi.denue_search(site["lat"], site["lon"], token)
    route = sakbe.route(site["lon"], site["lat"], site["corridor"], os.environ.get("SAKBE_TOKEN", "").strip())
    seismic = seismic_job.result()
    climate = climate_job.result()
    infra = infra_job.result()
    substation = infra.get("substation") or {}
    rail = infra.get("rail") or {}
    cvegeo = municipality.get("cvegeo")
    drought_row = drought_table.get(cvegeo) if cvegeo else None
    examples = [
        {"label": "INEGI municipio", "url": municipality.get("url"), "ok": municipality.get("ok")},
        {"label": "INEGI uso de suelo", "url": land.get("url"), "ok": land.get("ok")},
        {"label": "INEGI inundación", "url": flood.get("url"), "ok": flood.get("ok")},
        {"label": "DENUE", "url": denue.get("url"), "ok": denue.get("ok")},
        {"label": "SAKBÉ", "url": route.get("url"), "ok": route.get("ok")},
        {"label": "USGS sismos", "url": seismic.get("url"), "ok": seismic.get("ok")},
        {"label": "NASA POWER clima", "url": climate.get("url"), "ok": climate.get("ok")},
        {"label": "OSM Overpass", "url": infra.get("url"), "ok": infra.get("ok")},
    ]
    for example in examples:
        if example.get("url"):
            _remember(example)
    observation = {
        "drought": (drought_row or {}).get("category"),
        "drought_as_of": (drought_row or {}).get("as_of") or (_state["drought"] or {}).get("as_of"),
        "municipality": municipality.get("name") or (drought_row or {}).get("name"),
        "state": (drought_row or {}).get("state"),
        "cvegeo": cvegeo,
        "population": municipality.get("population"),
        "dwellings": municipality.get("dwellings"),
        "marco": municipality.get("marco"),
        "flood_hit": bool(flood.get("hit")),
        "flood_known": bool(flood.get("known")),
        "flood_layer": flood.get("layer"),
        "land_known": bool(land.get("ok") and land.get("hit")),
        "land_name": land.get("name"),
        "denue_count": denue.get("count"),
        "denue_mode": denue.get("mode"),
        "denue_reason": denue.get("reason"),
        "denue_radius_m": denue.get("radius_m") or 1500,
        "denue_sample": denue.get("sample") or [],
        "route_minutes": route.get("minutes"),
        "route_kilometers": route.get("kilometers"),
        "route_reference": route.get("reference"),
        "route_reason": route.get("reason"),
        "route_vehicle": route.get("vehicle"),
        "seismic_known": bool(seismic.get("ok")),
        "seismic_count": seismic.get("count"),
        "seismic_max_magnitude": seismic.get("maxMagnitude"),
        "seismic_strongest": seismic.get("strongest"),
        "seismic_radius_km": seismic.get("radiusKm"),
        "seismic_years": seismic.get("years"),
        "seismic_reason": seismic.get("reason"),
        "climate_known": bool(climate.get("ok")),
        "climate_precip_mm": climate.get("annualPrecipitationMm"),
        "climate_hot_days": climate.get("hotDaysPerYear"),
        "climate_period": climate.get("period"),
        "climate_years": climate.get("years") or [],
        "climate_reason": climate.get("reason"),
        "osm_known": bool(infra.get("ok")),
        "osm_endpoint": infra.get("url") if infra.get("ok") else None,
        "osm_base": infra.get("osmBase"),
        "osm_reason": infra.get("reason"),
        "substation_name": substation.get("name"),
        "substation_voltage_kv": substation.get("voltageKv"),
        "substation_voltages_kv": substation.get("voltagesKv") or [],
        "substation_distance_km": substation.get("distanceKm"),
        "substation_kind": substation.get("kind"),
        "substation_operator": substation.get("operator"),
        "substation_osm_id": substation.get("osmId"),
        "substation_radius_km": infra.get("substationRadiusKm"),
        "rail_known": bool(infra.get("ok")),
        "rail_distance_km": rail.get("distanceKm"),
        "rail_name": rail.get("name"),
        "rail_operator": rail.get("operator"),
        "rail_service": rail.get("service"),
        "rail_osm_id": rail.get("osmId"),
        "rail_radius_km": infra.get("railRadiusKm"),
        "rail_reason": infra.get("reason"),
    }
    return observation, {
        "municipality": municipality,
        "land": land,
        "flood": flood,
        "denue": {key: value for key, value in denue.items() if key != "sample"} | {"sample": denue.get("sample") or []},
        "route": {key: value for key, value in route.items() if key != "text"},
        "drought": drought_row,
        "seismic": seismic,
        "climate": climate,
        "infrastructure": {key: value for key, value in infra.items() if key != "query"},
    }


def materialize(site, observation, score):
    drought = observation
    objects = [
        {
            "type": "Sitio",
            "id": site["id"],
            "name": site["name"],
            "corridor": site["corridor"],
            "lat": site["lat"],
            "lon": site["lon"],
            "cvegeo": observation.get("cvegeo"),
            "municipality": observation.get("municipality"),
            "population": observation.get("population"),
            "marco": observation.get("marco"),
            "railDistanceKm": observation.get("rail_distance_km"),
            "railName": observation.get("rail_name"),
            "railOperator": observation.get("rail_operator"),
            "railKnown": observation.get("rail_known"),
            "railSource": "osm.overpass" if observation.get("rail_known") else None,
        },
        {
            "type": "CorredorLogistico",
            **CORRIDORS[site["corridor"]],
        },
    ]
    links = [{"rel": "dentro_de", "from": site["id"], "to": site["corridor"]}]
    if observation.get("cvegeo"):
        hid = f"sequia-{observation['cvegeo']}"
        objects.append({
            "type": "RiesgoHidrico",
            "id": hid,
            "cvegeo": observation.get("cvegeo"),
            "category": (observation.get("drought") or None),
            "asOf": observation.get("drought_as_of"),
            "source": "smn.conagua.municipios-sequia",
        })
        links.append({"rel": "expuesto_a_sequia", "from": site["id"], "to": hid})
    clima = f"clima-{site['id']}"
    objects.append({
        "type": "RiesgoClimatico",
        "id": clima,
        "floodHit": observation.get("flood_hit"),
        "floodLayer": observation.get("flood_layer"),
        "landClass": observation.get("land_name"),
        "annualPrecipitationMm": observation.get("climate_precip_mm"),
        "hotDaysPerYear": observation.get("climate_hot_days"),
        "hotDayThresholdC": 35,
        "climatePeriod": observation.get("climate_period"),
        "source": "inegi.wms",
        "climateSource": "nasa.power" if observation.get("climate_known") else None,
    })
    links.append({"rel": "expuesto_a_clima", "from": site["id"], "to": clima})
    sismo = f"sismo-{site['id']}"
    objects.append({
        "type": "RiesgoSismico",
        "id": sismo,
        "count": observation.get("seismic_count"),
        "maxMagnitude": observation.get("seismic_max_magnitude"),
        "strongest": observation.get("seismic_strongest"),
        "radiusKm": observation.get("seismic_radius_km"),
        "years": observation.get("seismic_years"),
        "known": observation.get("seismic_known"),
        "source": "usgs.fdsn",
        "reason": None if observation.get("seismic_known") else observation.get("seismic_reason"),
    })
    links.append({"rel": "expuesto_a_sismo", "from": site["id"], "to": sismo})
    for index, row in enumerate(observation.get("denue_sample") or []):
        eid = f"{site['id']}-denue-{index}"
        objects.append({"type": "Establecimiento", "id": eid, **row})
        links.append({"rel": "tiene_establecimiento", "from": site["id"], "to": eid})
    sub_id = f"sub-{site['id']}"
    found = observation.get("osm_known") and observation.get("substation_distance_km") is not None
    if found:
        reason = osm.NOTE + " Solo nombre, voltaje del tag y distancia en línea recta; nada sobre lo que la subestación pueda entregar."
    elif observation.get("osm_known"):
        reason = f"OSM no tiene subestación pública mapeada en {observation.get('substation_radius_km') or 25:g} km. " + osm.NOTE
    else:
        reason = observation.get("osm_reason") or "Overpass no respondió."
    objects.append({
        "type": "SubestacionAprox",
        "id": sub_id,
        "name": observation.get("substation_name") if found else None,
        "voltageKv": observation.get("substation_voltage_kv") if found else None,
        "distanceKm": observation.get("substation_distance_km") if found else None,
        "kind": observation.get("substation_kind") if found else None,
        "operator": observation.get("substation_operator") if found else None,
        "osmId": observation.get("substation_osm_id") if found else None,
        "source": "osm" if found else None,
        "empty": not found,
        "reason": reason,
    })
    links.append({"rel": "subestacion_mas_cercana", "from": site["id"], "to": sub_id})
    return {"objects": objects, "links": links, "score": score, "unused": drought}


def public_site(site, score=None):
    corridor = CORRIDORS[site["corridor"]]
    payload = {
        "id": site["id"],
        "name": site["name"],
        "corridor": site["corridor"],
        "corridorName": corridor["name"],
        "lat": site["lat"],
        "lon": site["lon"],
        "note": site["note"],
    }
    if score:
        payload["score"] = score["score"]
        payload["observation"] = {
            "municipality": score["observation"].get("municipality"),
            "state": score["observation"].get("state"),
            "cvegeo": score["observation"].get("cvegeo"),
            "population": score["observation"].get("population"),
            "marco": score["observation"].get("marco"),
            "landName": score["observation"].get("land_name"),
            "drought": score["observation"].get("drought"),
            "droughtAsOf": score["observation"].get("drought_as_of"),
            "denueMode": score["observation"].get("denue_mode"),
            "routeMinutes": score["observation"].get("route_minutes"),
            "routeReference": score["observation"].get("route_reference"),
            "seismicKnown": score["observation"].get("seismic_known"),
            "seismicCount": score["observation"].get("seismic_count"),
            "seismicMaxMagnitude": score["observation"].get("seismic_max_magnitude"),
            "seismicStrongest": score["observation"].get("seismic_strongest"),
            "climateKnown": score["observation"].get("climate_known"),
            "climatePrecipMm": score["observation"].get("climate_precip_mm"),
            "climateHotDays": score["observation"].get("climate_hot_days"),
            "climatePeriod": score["observation"].get("climate_period"),
            "osmKnown": score["observation"].get("osm_known"),
            "osmEndpoint": score["observation"].get("osm_endpoint"),
            "substationName": score["observation"].get("substation_name"),
            "substationVoltageKv": score["observation"].get("substation_voltage_kv"),
            "substationDistanceKm": score["observation"].get("substation_distance_km"),
            "substationKind": score["observation"].get("substation_kind"),
            "substationOperator": score["observation"].get("substation_operator"),
            "railDistanceKm": score["observation"].get("rail_distance_km"),
            "railRadiusKm": score["observation"].get("rail_radius_km"),
            "railName": score["observation"].get("rail_name"),
            "railOperator": score["observation"].get("rail_operator"),
        }
    return payload


def _smn_source(drought):
    return {
        "ok": bool(drought.get("ok")),
        "url": drought.get("url"),
        "asOf": drought.get("as_of"),
        "rows": drought.get("rows"),
        "error": drought.get("error"),
    }


def _drought_loaded():
    # El SMN contesta de forma intermitente con una página de error de WAF
    # (medido 2026-10-12: 3 libros en 12 intentos). Si el arranque cayó en una
    # de esas, se reintenta al calificar en vez de quedarse en 503 para siempre.
    drought = _state["drought"] or {}
    if drought.get("table"):
        return drought
    fresh = conagua.load_drought()
    if fresh.get("table"):
        with _lock:
            _state["drought"] = fresh
            _state["sources"]["conagua_smn"] = _smn_source(fresh)
        return fresh
    return drought


@app.on_event("startup")
def startup():
    drought = conagua.load_drought()
    polygons = catgeo.preload()
    arcgis = conagua.probe_arcgis()
    datos = datosgob.probe()
    denue = inegi.denue_search(25.7789, -100.1886, os.environ.get("INEGI_TOKEN", "").strip())
    routing = sakbe.probe()
    seismic = usgs.probe()
    weather = power.probe()
    overpass = osm.probe()
    database = False
    try:
        database = ensure_db()
    except Exception as error:
        database = False
        _state["db_error"] = str(error)
    with _lock:
        _state["drought"] = drought
        _state["sources"] = {
            "inegi_wms": {
                "ok": True,
                "url": inegi.WMS,
                "layers": inegi.LAYERS,
                "note": "Uso de suelo e inundación por GetFeatureInfo. El municipio ya no sale de un pixel: sale del polígono.",
            },
            "inegi_catgeo": polygons,
            "conagua_smn": _smn_source(drought),
            "conagua_arcgis": arcgis,
            "datos_gob_mx": datos,
            "inegi_denue": {
                "ok": bool(denue.get("ok")),
                "configured": bool(denue.get("configured")),
                "mode": denue.get("mode"),
                "url": "https://www.inegi.org.mx/servicios/api_denue.html",
                "reason": denue.get("reason"),
            },
            "inegi_sakbe": routing,
            "usgs_sismos": seismic,
            "nasa_power_clima": weather,
            "osm_overpass": overpass,
            "open_meteo": {
                "ok": False,
                "url": "https://archive-api.open-meteo.com/v1/archive",
                "note": "Medido el 2026-10-12: 429 'Daily API request limit exceeded' desde un servidor. No se usa; el clima sale de NASA POWER (cementerio).",
            },
            "database": {"ok": database, "urlConfigured": bool(os.environ.get("DATABASE_URL"))},
        }


def deployed_commit():
    """El commit que corre. Railway lo inyecta; en otro lado se pasa GIT_COMMIT."""
    for variable in ("RAILWAY_GIT_COMMIT_SHA", "GIT_COMMIT"):
        value = os.environ.get(variable, "").strip()
        if value:
            return value[:12]
    return None


@app.get("/api/health")
def health():
    drought = _state["drought"] or {}
    return {
        "ok": True,
        "service": "dged-atlas",
        "commit": deployed_commit(),
        "oracle": {"configured": oracle.is_configured(), "door": bool(access.access_token())},
        "droughtRows": drought.get("rows"),
        "droughtAsOf": drought.get("as_of"),
    }


@app.get("/api/ontology")
def ontology():
    return _ontology()


@app.get("/api/sources")
def sources():
    return _state["sources"]


@app.get("/api/examples")
def examples():
    return {"calls": _state["examples"]}


@app.get("/api/corridors")
def corridors():
    return list(CORRIDORS.values())


@app.get("/api/sites")
def sites(corridor: str | None = None):
    rows = []
    for site in SITES:
        if corridor and site["corridor"] != corridor:
            continue
        rows.append(public_site(site, _state["scores"].get(site["id"])))
    return {"sites": rows}


@app.get("/api/sites/{site_id}")
def site_detail(site_id: str):
    site = next((item for item in SITES if item["id"] == site_id), None)
    if site is None:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")
    payload = public_site(site, _state["scores"].get(site_id))
    cached = _state["scores"].get(site_id)
    if cached:
        payload["graph"] = cached["graph"]
        payload["evidence"] = cached["evidence"]
    return payload


@app.post("/api/sites/{site_id}/score", dependencies=[Depends(access.guard_score)])
def score_site(site_id: str, drought_year: bool = False):
    site = next((item for item in SITES if item["id"] == site_id), None)
    if site is None:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")
    drought = _drought_loaded()
    # Sin el libro del SMN la sequía queda ausente y el número no es publicable (I);
    # las demás capas se siguen consultando y se muestran.
    observation, evidence = observe(site, drought.get("table") or {})
    if not drought.get("table"):
        observation["drought_reason"] = drought.get("error") or "El monitor de sequía no está cargado"
    score = score_observation(observation, drought_year=drought_year)
    graph = materialize(site, observation, score)
    cached = {
        "score": score,
        "observation": observation,
        "evidence": {
            "municipalityUrl": (evidence["municipality"] or {}).get("url"),
            "landUrl": (evidence["land"] or {}).get("url"),
            "floodUrl": (evidence["flood"] or {}).get("url"),
            "denueUrl": (evidence["denue"] or {}).get("url"),
            "droughtUrl": drought.get("url"),
            "seismicUrl": (evidence["seismic"] or {}).get("url"),
            "climateUrl": (evidence["climate"] or {}).get("url"),
            "osmUrl": (evidence["infrastructure"] or {}).get("url"),
            "osmAttempts": (evidence["infrastructure"] or {}).get("attempts"),
        },
        "graph": {"objects": graph["objects"], "links": graph["links"]},
    }
    with _lock:
        _state["scores"][site_id] = cached
    try:
        save_score(site_id, {"score": score, "observation": observation, "graph": cached["graph"]})
    except Exception:
        pass
    return public_site(site, cached) | {"graph": cached["graph"], "evidence": cached["evidence"]}


class OracleQuestion(BaseModel):
    question: str


def oracle_api():
    """Las herramientas del Oráculo son estas mismas funciones de la API."""
    return oracle.AtlasApi(
        list_sites=lambda corridor: sites(corridor),
        score_site=lambda site_id, drought_year: score_site(site_id, drought_year=drought_year),
        site_detail=site_detail,
        ontology=ontology,
        sources=sources,
    )


@app.post("/api/oracle", dependencies=[Depends(access.guard_oracle)])
def ask_oracle(body: OracleQuestion):
    if not oracle.is_configured():
        raise HTTPException(
            status_code=503,
            detail="El Oráculo está dormido: el servidor no tiene ANTHROPIC_API_KEY. El resto de Atlas funciona sin él.",
        )
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Escribe una pregunta.")
    if len(question) > 2000:
        raise HTTPException(status_code=400, detail="La pregunta pasa de 2000 caracteres.")
    import anthropic

    try:
        result = oracle.ask(question, oracle_api(), oracle.make_client())
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=503, detail="El Oráculo no pudo autenticarse: revisa ANTHROPIC_API_KEY.") from None
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="El Oráculo está saturado; intenta en un minuto.") from None
    except anthropic.APIStatusError as error:
        raise HTTPException(status_code=502, detail=f"El modelo respondió con error {error.status_code}.") from None
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=502, detail="No hubo conexión con el modelo.") from None
    return {key: result[key] for key in ("answer", "steps", "sources", "unverified", "missing", "model", "stop")}


@app.get("/api/wms/{layer_key}/{z}/{x}/{y}.png")
def wms_tile(layer_key: str, z: int, x: int, y: int):
    layer = inegi.LAYERS.get(layer_key)
    if layer is None or z < 0 or z > 16:
        raise HTTPException(status_code=404, detail="Capa no disponible")
    cache_key = (layer_key, z, x, y)
    with _tile_lock:
        cached = _tile_cache.get(cache_key)
    if cached is None:
        result = inegi.wms_tile(layer["id"], z, x, y)
        if not result["ok"] or not result["body"]:
            raise HTTPException(status_code=502, detail="INEGI no entregó el tile")
        cached = result["body"]
        with _tile_lock:
            if len(_tile_cache) > 240:
                _tile_cache.pop(next(iter(_tile_cache)))
            _tile_cache[cache_key] = cached
    return Response(content=cached, media_type="image/png")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
