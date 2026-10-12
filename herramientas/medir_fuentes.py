#!/usr/bin/env python3
"""Vuelve a medir las fuentes de datos candidatas de Atlas (solo stdlib).

La regla (CLAUDE.md): una fuente se MIDE antes de escribir su código.
¿Responde desde un servidor? ¿Trae dato de verdad para un punto de México?
Este script hace la petición real, guarda código HTTP, latencia y el valor
observado, y da un veredicto por fuente. El catálogo escrito vive en
`MEMORY/FUENTES.md`; las muertas, en `MEMORY/CEMENTERIO.md`.

Uso:
    python3 herramientas/medir_fuentes.py                    # Apodaca y Silao
    python3 herramientas/medir_fuentes.py --punto 25.78,-100.19
    python3 herramientas/medir_fuentes.py --salida medicion.json
    python3 herramientas/medir_fuentes.py --solo usgs.sismos,osm.overpass

Claves opcionales (de entorno; nunca en el repo, Constitución VIII):
    BANXICO_TOKEN, INEGI_BIE_TOKEN, FIRMS_MAP_KEY

Veredictos:
    VIVA        respondió desde este servidor con dato útil para el punto.
    CON CLAVE   respondió, pero exige una clave que no tenemos.
    CUOTA       respondió 429: existe, pero la cuota (por IP o por día) se agotó.
    MUERTA      respondió sin dato (403, página de error con HTTP 200, redirección
                a "Loading") o no hay dato utilizable.
    NO CONCLUYE la conexión se cortó antes de una respuesta HTTP (reset, timeout
                o puerto no estándar a través del proxy). "No medido" no es
                "medido y no funcionó".

Un HTTP 200 no es un dato: cada sonda revisa el CONTENIDO (el WAF del SMN
contesta 200 con una página de error de 730 bytes).
"""

import argparse
import json
import math
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

PUNTOS = {
    "apodaca_nl": (25.78, -100.19),
    "silao_gto": (20.95, -101.43),
}
UA = "DGED-Atlas-medir-fuentes/0.1 (+https://github.com/rasdg05)"
TIMEOUT = 20
TIMEOUT_OVERPASS = 45  # Overpass tarda 15-20 s en un espejo sano.

OVERPASS_ESPEJOS = (
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)


class Respuesta:
    def __init__(self, url, status=None, cuerpo=b"", latencia=None, error=None, tipo=""):
        self.url = url
        self.status = status
        self.cuerpo = cuerpo
        self.latencia = latencia
        self.error = error
        self.tipo = tipo

    def json(self):
        return json.loads(self.cuerpo.decode("utf-8"))

    def texto(self, n=300):
        return self.cuerpo[:n].decode("utf-8", "replace")


def pedir(url, datos=None, cabeceras=None, timeout=TIMEOUT):
    """Una petición real. Nunca levanta: devuelve status/error y latencia."""
    h = {"User-Agent": UA, "Accept": "*/*"}
    h.update(cabeceras or {})
    req = urllib.request.Request(url, data=datos, headers=h)
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cuerpo = r.read()
            return Respuesta(url, r.status, cuerpo, round(time.monotonic() - t0, 3),
                             tipo=r.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as e:
        try:
            cuerpo = e.read()
        except Exception:
            cuerpo = b""
        return Respuesta(url, e.code, cuerpo, round(time.monotonic() - t0, 3),
                         tipo=e.headers.get("Content-Type", "") if e.headers else "")
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
        razon = getattr(e, "reason", e)
        return Respuesta(url, None, b"", round(time.monotonic() - t0, 3),
                         error=f"{type(e).__name__}: {razon}")


def km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def resultado(clave, r, veredicto, valor=None, requiere_clave=False, nota=""):
    return {
        "clave": clave,
        "url": r.url if r else None,
        "http": r.status if r else None,
        "latencia_s": r.latencia if r else None,
        "error_red": r.error if r else None,
        "requiere_clave": requiere_clave,
        "valor": valor,
        "veredicto": veredicto,
        "nota": nota,
    }


def sin_respuesta(clave, r, nota=""):
    """Sin HTTP no se concluye; con HTTP de error, muere."""
    if r.status is None:
        return resultado(clave, r, "NO CONCLUYE", nota=nota or r.error)
    if r.status == 429:
        return resultado(clave, r, "CUOTA", nota=nota or r.texto(200))
    return resultado(clave, r, "MUERTA", nota=nota or r.texto(200))


# ---------------------------------------------------------------- sondas


def usgs_sismos(lat, lon):
    clave = "usgs.sismos"
    q = urllib.parse.urlencode({
        "format": "geojson", "latitude": lat, "longitude": lon,
        "maxradiuskm": 200, "starttime": "1976-01-01", "minmagnitude": 4,
        "orderby": "magnitude", "limit": 5,
    })
    url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?{q}"
    r = pedir(url)
    if r.status != 200:
        return sin_respuesta(clave, r)
    try:
        d = r.json()
    except ValueError:
        return resultado(clave, r, "MUERTA", nota="no es JSON")
    feats = d.get("features", [])
    top = [
        {"mag": f["properties"]["mag"], "lugar": f["properties"]["place"],
         "fecha": datetime.fromtimestamp(f["properties"]["time"] / 1000, timezone.utc).date().isoformat(),
         "dist_km": km(lat, lon, f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0])}
        for f in feats
    ]
    # El conteo total (el query trae limit=5) sale de /count.
    qc = urllib.parse.urlencode({
        "format": "geojson", "latitude": lat, "longitude": lon,
        "maxradiuskm": 200, "starttime": "1976-01-01", "minmagnitude": 4,
    })
    rc = pedir(f"https://earthquake.usgs.gov/fdsnws/event/1/count?{qc}")
    total = None
    if rc.status == 200:
        try:
            total = rc.json().get("count")
        except ValueError:
            total = None
    valor = {"radio_km": 200, "desde": "1976-01-01", "mag_min": 4,
             "eventos": total, "mayores": top}
    return resultado(clave, r, "VIVA", valor,
                     nota="Catálogo ComCat; 0 eventos también es dato. Dominio público (USGS).")


def openmeteo_pronostico(lat, lon):
    clave = "openmeteo.pronostico"
    q = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon, "forecast_days": 3, "timezone": "America/Mexico_City",
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
    })
    r = pedir(f"https://api.open-meteo.com/v1/forecast?{q}")
    if r.status != 200:
        return sin_respuesta(clave, r)
    d = r.json()
    return resultado(clave, r, "VIVA",
                     {"elevacion_m": d.get("elevation"), "diario": d.get("daily")},
                     nota="API gratuita SOLO para uso no comercial (open-meteo.com/en/terms); CC BY 4.0.")


def openmeteo_archivo(lat, lon):
    clave = "openmeteo.archivo"
    anio = date.today().year - 1
    q = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon, "start_date": f"{anio}-01-01",
        "end_date": f"{anio}-12-31", "daily": "precipitation_sum,temperature_2m_max",
        "timezone": "America/Mexico_City",
    })
    r = pedir(f"https://archive-api.open-meteo.com/v1/archive?{q}")
    if r.status != 200:
        return sin_respuesta(clave, r)
    d = r.json().get("daily", {})
    lluvia = [x for x in d.get("precipitation_sum", []) if x is not None]
    tmax = [x for x in d.get("temperature_2m_max", []) if x is not None]
    valor = {
        "anio": anio,
        "lluvia_anual_mm": round(sum(lluvia), 1) if lluvia else None,
        "dias_con_dato": len(lluvia),
        "tmax_max_c": max(tmax) if tmax else None,
        "dias_tmax_ge_40c": sum(1 for x in tmax if x >= 40),
    }
    return resultado(clave, r, "VIVA", valor,
                     nota="Reanálisis (ERA5 y otros). Uso no comercial en la API gratuita.")


def openmeteo_elevacion(lat, lon):
    clave = "openmeteo.elevacion"
    r = pedir(f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}")
    if r.status != 200:
        return sin_respuesta(clave, r)
    return resultado(clave, r, "VIVA", {"elevacion_m": r.json().get("elevation")},
                     nota="Copernicus DEM GLO-90 servido por Open-Meteo. Uso no comercial.")


def nasa_power(lat, lon):
    clave = "nasa.power"
    q = urllib.parse.urlencode({
        "parameters": "T2M,T2M_MAX,PRECTOTCORR,ALLSKY_SFC_SW_DWN,WS10M",
        "community": "RE", "longitude": lon, "latitude": lat, "format": "JSON",
    })
    r = pedir(f"https://power.larc.nasa.gov/api/temporal/climatology/point?{q}")
    if r.status != 200:
        return sin_respuesta(clave, r)
    d = r.json()
    par = d.get("properties", {}).get("parameter", {})
    anual = {k: v.get("ANN") for k, v in par.items()}
    if not anual or all(v in (None, -999.0) for v in anual.values()):
        return resultado(clave, r, "MUERTA", nota="sin valores")
    return resultado(clave, r, "VIVA",
                     {"anual": anual, "periodo": d.get("header", {}).get("range")},
                     nota="T2M °C, PRECTOTCORR mm/día, ALLSKY kWh/m²/día, WS10M m/s. Sin clave.")


def osm_overpass(lat, lon):
    clave = "osm.overpass"
    q = (
        "[out:json][timeout:30];("
        f'nwr(around:10000,{lat},{lon})["power"="substation"];'
        f'way(around:5000,{lat},{lon})["power"="line"];'
        f'way(around:10000,{lat},{lon})["railway"="rail"];'
        f'nwr(around:30000,{lat},{lon})["aeroway"="aerodrome"];'
        ");out tags center;"
    )
    datos = urllib.parse.urlencode({"data": q}).encode()
    intentos = []
    for espejo in OVERPASS_ESPEJOS:
        r = pedir(espejo, datos=datos, timeout=TIMEOUT_OVERPASS)
        intentos.append({"espejo": espejo, "http": r.status, "latencia_s": r.latencia, "error": r.error})
        if r.status != 200:
            continue
        try:
            d = r.json()
        except ValueError:
            continue
        subs, lineas, rieles, aeros = [], {}, 0, []
        for e in d.get("elements", []):
            t = e.get("tags", {})
            c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
            if t.get("power") == "substation":
                dist = km(lat, lon, c["lat"], c["lon"]) if c.get("lat") is not None else None
                subs.append({"dist_km": dist, "voltage": t.get("voltage"), "nombre": t.get("name")})
            elif t.get("power") == "line":
                v = t.get("voltage") or "sin_etiqueta"
                lineas[v] = lineas.get(v, 0) + 1
            elif t.get("railway") == "rail":
                rieles += 1
            elif t.get("aeroway") == "aerodrome":
                dist = km(lat, lon, c["lat"], c["lon"]) if c.get("lat") is not None else None
                aeros.append({"nombre": t.get("name"), "iata": t.get("iata"), "dist_km": dist})
        lejos = lambda x: x["dist_km"] if x["dist_km"] is not None else 1e9  # noqa: E731
        subs.sort(key=lejos)
        aeros.sort(key=lejos)
        valor = {
            "osm_base": d.get("osm3s", {}).get("timestamp_osm_base"),
            "subestaciones_10km": len(subs),
            "subestaciones_con_voltage": sum(1 for s in subs if s["voltage"]),
            "subestacion_mas_cercana": subs[0] if subs else None,
            "tramos_linea_5km_por_voltage": lineas,
            "tramos_via_ferrea_10km": rieles,
            "aerodromos_30km": aeros[:5],
        }
        res = resultado(clave, r, "VIVA", valor,
                        nota="ODbL. Candidatos, no capacidad (D-003). Respondió: " + espejo)
        res["intentos"] = intentos
        return res
    res = resultado(clave, None, "NO CONCLUYE", nota="ningún espejo respondió")
    res["intentos"] = intentos
    return res


def _stac(clave, endpoint, coleccion, lat, lon, ordenar=True):
    cuerpo = {"collections": [coleccion],
              "intersects": {"type": "Point", "coordinates": [lon, lat]}, "limit": 1}
    if ordenar:
        cuerpo["sortby"] = [{"field": "properties.datetime", "direction": "desc"}]
    r = pedir(endpoint, datos=json.dumps(cuerpo).encode(),
              cabeceras={"Content-Type": "application/json"})
    if r.status != 200:
        return sin_respuesta(clave, r), None
    feats = r.json().get("features", [])
    if not feats:
        return resultado(clave, r, "MUERTA", nota="sin escenas sobre el punto"), None
    return None, (r, feats[0])


def stac_earthsearch_s2(lat, lon):
    clave = "stac.earthsearch.s2"
    malo, ok = _stac(clave, "https://earth-search.aws.element84.com/v1/search",
                     "sentinel-2-l2a", lat, lon)
    if malo:
        return malo
    r, f = ok
    p = f["properties"]
    return resultado(clave, r, "VIVA",
                     {"escena": f["id"], "fecha": p.get("datetime"),
                      "nubosidad_pct": p.get("eo:cloud_cover"),
                      "bandas": sorted(f.get("assets", {}))[:8]},
                     nota="COG públicos en AWS, sin clave. Licencia Copernicus (libre y abierta).")


def stac_planetary_s2(lat, lon):
    clave = "stac.planetary.s2"
    malo, ok = _stac(clave, "https://planetarycomputer.microsoft.com/api/stac/v1/search",
                     "sentinel-2-l2a", lat, lon)
    if malo:
        return malo
    r, f = ok
    p = f["properties"]
    return resultado(clave, r, "VIVA",
                     {"escena": f["id"], "fecha": p.get("datetime"),
                      "nubosidad_pct": p.get("eo:cloud_cover")},
                     nota="Búsqueda sin clave; los assets se firman con un token SAS gratuito anónimo.")


def stac_copdem(lat, lon):
    clave = "stac.copdem30"
    malo, ok = _stac(clave, "https://earth-search.aws.element84.com/v1/search",
                     "cop-dem-glo-30", lat, lon, ordenar=False)
    if malo:
        return malo
    r, f = ok
    href = f.get("assets", {}).get("data", {}).get("href")
    return resultado(clave, r, "VIVA", {"mosaico": f["id"], "cog": href},
                     nota="COG de 1°x1° (~40 MB). Leer el píxel exige GDAL/rasterio, no stdlib.")


def worldbank(lat, lon):
    clave = "worldbank.mex"
    valores = {}
    r = None
    for ind in ("EG.ELC.ACCS.ZS", "NY.GDP.MKTP.CD", "SL.IND.EMPL.ZS"):
        r = pedir(f"https://api.worldbank.org/v2/country/MEX/indicator/{ind}?format=json&mrnev=1")
        if r.status != 200:
            return sin_respuesta(clave, r)
        try:
            d = r.json()
            fila = d[1][0]
            valores[ind] = {"anio": fila["date"], "valor": fila["value"],
                            "actualizado": d[0].get("lastupdated")}
        except (ValueError, IndexError, KeyError, TypeError):
            valores[ind] = None
    return resultado(clave, r, "VIVA", valores,
                     nota="Nacional, no del punto: contexto del memo, no rankea. CC BY 4.0.")


def cenace_pml(lat, lon):
    clave = "cenace.pml"
    hoy = date.today()
    ini = hoy - timedelta(days=2)
    url = ("https://ws01.cenace.gob.mx:8082/SWPML/SIM/SIN/MDA/04PLD-115/"
           f"{ini:%Y/%m/%d}/{hoy:%Y/%m/%d}/JSON")
    r = pedir(url)
    if r.status != 200:
        return sin_respuesta(clave, r, nota=(r.error or r.texto(200)) +
                             " | puerto 8082: el proxy de este entorno no lo atraviesa")
    try:
        d = r.json()
    except ValueError:
        return resultado(clave, r, "MUERTA", nota="no es JSON: " + r.texto(120))
    return resultado(clave, r, "VIVA", d if len(json.dumps(d)) < 2000 else str(d)[:500],
                     nota="Nodo de ejemplo 04PLD-115; el PML es por nodo, no por punto.")


def _es_waf_smn(r):
    return r.status == 200 and b"This page can't be displayed" in r.cuerpo


def _smn_varias(url, es_dato, intentos=5):
    """El WAF del SMN contesta 200 con una página de error de forma intermitente.
    Se pide varias veces y se cuenta cuántas trajeron dato."""
    buenas, ultima, primera_buena = 0, None, None
    for _ in range(intentos):
        r = pedir(url)
        ultima = r
        if r.status == 200 and es_dato(r.cuerpo):
            buenas += 1
            primera_buena = primera_buena or r
        time.sleep(1)
    return buenas, intentos, primera_buena or ultima


def smn_webservice(lat, lon):
    clave = "smn.webservices"
    buenas, n, r = _smn_varias("https://smn.conagua.gob.mx/webservices/?method=1",
                               lambda b: len(b) > 1000 and not b.lstrip().startswith(b"<"))
    if buenas:
        return resultado(clave, r, "VIVA", {"bytes": len(r.cuerpo), "con_dato": f"{buenas}/{n}"},
                         nota="Pronóstico por municipio (gzip de JSON). Intermitente.")
    if _es_waf_smn(r):
        return resultado(clave, r, "MUERTA", {"con_dato": f"0/{n}"},
                         nota="HTTP 200 con página de error del WAF (730 B): sin dato desde un servidor")
    return sin_respuesta(clave, r)


def smn_sequia(lat, lon):
    clave = "smn.sequia_xlsx"
    buenas, n, r = _smn_varias(
        "https://smn.conagua.gob.mx/tools/RESOURCES/Monitor%20de%20Sequia%20en%20Mexico/MunicipiosSequia.xlsx",
        lambda b: b.startswith(b"PK"))
    if buenas:
        return resultado(clave, r, "VIVA", {"bytes": len(r.cuerpo), "con_dato": f"{buenas}/{n}"},
                         nota="xlsx (zip) recibido; las demás respuestas fueron la página del WAF con HTTP 200.")
    if _es_waf_smn(r):
        return resultado(clave, r, "MUERTA", {"con_dato": f"0/{n}"},
                         nota="HTTP 200 con página de error del WAF: es la fuente de sequía del score (Inv. I)")
    return sin_respuesta(clave, r)


def banxico_sie(lat, lon):
    clave = "banxico.sie"
    token = os.environ.get("BANXICO_TOKEN", "")
    url = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno"
    r = pedir(url, cabeceras={"Bmx-Token": token} if token else None)
    if r.status == 200:
        try:
            dato = r.json()["bmx"]["series"][0]["datos"][0]
        except (ValueError, KeyError, IndexError):
            dato = r.texto(200)
        return resultado(clave, r, "VIVA", {"SF43718_fix_usd": dato}, requiere_clave=True)
    if r.status in (400, 401, 403) and b"oken" in r.cuerpo:
        return resultado(clave, r, "CON CLAVE", requiere_clave=True, nota=r.texto(220))
    return sin_respuesta(clave, r)


def inegi_bie(lat, lon):
    clave = "inegi.bie"
    token = os.environ.get("INEGI_BIE_TOKEN") or "00000000-0000-0000-0000-000000000000"
    url = ("https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/"
           f"1002000001/es/0700/false/BISE/2.0/{token}?type=json")
    r = pedir(url)
    publico = url.replace(token, "{INEGI_BIE_TOKEN}")
    if r.status == 200:
        try:
            serie = r.json()["Series"][0]
            obs = serie["OBSERVATIONS"][0]
            res = resultado(clave, r, "VIVA",
                            {"indicador": "1002000001 población total nacional",
                             "periodo": obs.get("TIME_PERIOD"), "valor": obs.get("OBS_VALUE")},
                            requiere_clave=True)
            res["url"] = publico
            return res
        except (ValueError, KeyError, IndexError):
            pass
    res = (resultado(clave, r, "CON CLAVE", requiere_clave=True,
                     nota="sin token válido responde: " + r.texto(150))
           if r.status in (400, 401, 403) else sin_respuesta(clave, r))
    res["url"] = publico
    return res


def inegi_catgeo(lat, lon):
    """Catálogo Único por estado. Solo sabe el municipio de los dos puntos de
    referencia; para un punto arbitrario mide NL y reporta el conteo."""
    clave = "inegi.catgeo"
    conocidos = {PUNTOS["apodaca_nl"]: ("19", "19006"), PUNTOS["silao_gto"]: ("11", "11037")}
    cve_ent, cvegeo = conocidos.get((lat, lon), ("19", None))
    r = pedir(f"https://gaia.inegi.org.mx/wscatgeo/v2/mgem/{cve_ent}")
    if r.status != 200:
        return sin_respuesta(clave, r)
    try:
        datos = r.json().get("datos", [])
    except ValueError:
        return resultado(clave, r, "MUERTA", nota="no es JSON: " + r.texto(120))
    if not datos:
        return resultado(clave, r, "MUERTA", nota="sin municipios")
    fila = next((m for m in datos if m.get("cvegeo") == cvegeo), None)
    return resultado(clave, r, "VIVA",
                     {"cve_ent": cve_ent, "municipios_del_estado": len(datos),
                      "municipio": fila and {k: fila.get(k) for k in ("cvegeo", "nomgeo", "pob_total")}},
                     nota="Ya en producción (catgeo.py). Población del Censo 2020.")


def nasa_firms(lat, lon):
    clave = "nasa.firms"
    key = os.environ.get("FIRMS_MAP_KEY") or "DEMO_KEY"
    caja = f"{lon - 0.25},{lat - 0.25},{lon + 0.25},{lat + 0.25}"
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{caja}/5"
    r = pedir(url)
    publico = url.replace(key, "{FIRMS_MAP_KEY}")
    if r.status == 200 and r.cuerpo.startswith(b"latitude"):
        filas = r.cuerpo.decode().strip().splitlines()[1:]
        res = resultado(clave, r, "VIVA", {"focos_5_dias_caja_0.5deg": len(filas)}, requiere_clave=True)
    elif b"MAP_KEY" in r.cuerpo:
        res = resultado(clave, r, "CON CLAVE", requiere_clave=True, nota=r.texto(80))
    else:
        res = sin_respuesta(clave, r)
    res["url"] = publico
    return res


def ghsl(lat, lon):
    clave = "jrc.ghsl"
    url = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_BUILT_S_GLOBE_R2023A/"
           "GHS_BUILT_S_E2030_GLOBE_R2023A_54009_100/V1-0/tiles/")
    r = pedir(url)
    if r.status != 200:
        return sin_respuesta(clave, r)
    n = r.cuerpo.count(b".zip\"")
    return resultado(clave, r, "VIVA", {"mosaicos_zip_listados": n},
                     nota="Descarga por mosaico (raster). Valor por punto exige GDAL; CC BY 4.0.")


def conagua_sigagis(lat, lon):
    clave = "conagua.sigagis"
    r = pedir("https://sigagis.conagua.gob.mx/ArcGIS/rest/services?f=pjson")
    try:
        r.json()
        return resultado(clave, r, "VIVA", nota="devolvió JSON: revisar si revive (CEMENTERIO)")
    except ValueError:
        return resultado(clave, r, "MUERTA" if r.status else "NO CONCLUYE",
                         nota="no devuelve JSON: " + (r.error or r.texto(100)))


def datosgob(lat, lon):
    clave = "datosgob.ckan"
    r = pedir("https://datos.gob.mx/api/3/action/package_search?q=acuiferos&rows=1")
    if r.status == 200:
        try:
            return resultado(clave, r, "VIVA", {"count": r.json()["result"]["count"]})
        except (ValueError, KeyError):
            pass
    return sin_respuesta(clave, r)


def atlas_riesgos(lat, lon):
    clave = "cenapred.anr"
    r = pedir("https://www.atlasnacionalderiesgos.gob.mx/")
    if r.status == 200:
        return resultado(clave, r, "VIVA", {"bytes": len(r.cuerpo)},
                         nota="Portada respondió; falta medir las capas (WMS/ArcGIS) por separado.")
    return sin_respuesta(clave, r)


def ssn_unam(lat, lon):
    clave = "ssn.unam"
    r = pedir("http://www2.ssn.unam.mx:8080/catalogo/")
    if r.status == 200:
        return resultado(clave, r, "VIVA", {"bytes": len(r.cuerpo)},
                         nota="Catálogo del Servicio Sismológico Nacional (formulario web).")
    return sin_respuesta(clave, r, nota=(r.error or "") + " | puerto 8080")


def geofabrik(lat, lon):
    clave = "osm.geofabrik"
    r = pedir("https://download.geofabrik.de/north-america/mexico-updates/state.txt")
    if r.status == 200 and b"sequenceNumber" in r.cuerpo:
        campos = dict(linea.split("=", 1) for linea in r.cuerpo.decode().splitlines() if "=" in linea and not linea.startswith("#"))
        return resultado(clave, r, "VIVA", {"timestamp": campos.get("timestamp", "").replace("\\", ""),
                                            "sequenceNumber": campos.get("sequenceNumber")},
                         nota="Extracto diario de OSM para México (.osm.pbf). ODbL.")
    return sin_respuesta(clave, r)


SONDAS = {
    "usgs.sismos": usgs_sismos,
    "openmeteo.pronostico": openmeteo_pronostico,
    "openmeteo.archivo": openmeteo_archivo,
    "openmeteo.elevacion": openmeteo_elevacion,
    "nasa.power": nasa_power,
    "osm.overpass": osm_overpass,
    "stac.earthsearch.s2": stac_earthsearch_s2,
    "stac.planetary.s2": stac_planetary_s2,
    "stac.copdem30": stac_copdem,
    "worldbank.mex": worldbank,
    "cenace.pml": cenace_pml,
    "smn.webservices": smn_webservice,
    "smn.sequia_xlsx": smn_sequia,
    "banxico.sie": banxico_sie,
    "inegi.bie": inegi_bie,
    "inegi.catgeo": inegi_catgeo,
    "nasa.firms": nasa_firms,
    "jrc.ghsl": ghsl,
    "conagua.sigagis": conagua_sigagis,
    "datosgob.ckan": datosgob,
    "cenapred.anr": atlas_riesgos,
    "ssn.unam": ssn_unam,
    "osm.geofabrik": geofabrik,
}

# Las que no dependen del punto se miden una sola vez.
SIN_PUNTO = {"worldbank.mex", "cenace.pml", "smn.webservices", "smn.sequia_xlsx",
             "banxico.sie", "inegi.bie", "jrc.ghsl", "conagua.sigagis",
             "datosgob.ckan", "cenapred.anr", "ssn.unam", "osm.geofabrik"}


def medir(puntos, solo=None):
    salida = {
        "medido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "timeout_s": TIMEOUT,
        "puntos": {k: {"lat": v[0], "lon": v[1]} for k, v in puntos.items()},
        "fuentes": [],
    }
    nombres = [n for n in SONDAS if not solo or n in solo]
    for nombre in nombres:
        sonda = SONDAS[nombre]
        objetivos = list(puntos.items())[:1] if nombre in SIN_PUNTO else list(puntos.items())
        for etiqueta, (lat, lon) in objetivos:
            try:
                res = sonda(lat, lon)
            except Exception as e:  # una sonda rota no tumba la medición
                res = resultado(nombre, None, "NO CONCLUYE", nota=f"sonda falló: {type(e).__name__}: {e}")
            res["punto"] = None if nombre in SIN_PUNTO else etiqueta
            salida["fuentes"].append(res)
            print(f"{res['veredicto']:<12} {nombre:<22} {str(res['punto'] or '-'):<11} "
                  f"http={res['http']} {res['latencia_s']}s", file=sys.stderr)
    return salida


def _punto(texto):
    lat, lon = (float(x) for x in texto.split(","))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise argparse.ArgumentTypeError("lat,lon fuera de rango")
    return lat, lon


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--punto", type=_punto, help="lat,lon (por defecto: Apodaca NL y Silao Gto)")
    ap.add_argument("--salida", help="archivo JSON de salida (por defecto, stdout)")
    ap.add_argument("--solo", help="claves separadas por coma, p. ej. usgs.sismos,nasa.power")
    a = ap.parse_args(argv)
    puntos = {"punto": a.punto} if a.punto else PUNTOS
    solo = set(a.solo.split(",")) if a.solo else None
    if solo and not solo <= set(SONDAS):
        ap.error("clave desconocida: " + ", ".join(sorted(solo - set(SONDAS))))
    res = medir(puntos, solo)
    texto = json.dumps(res, ensure_ascii=False, indent=2)
    if a.salida:
        with open(a.salida, "w", encoding="utf-8") as f:
            f.write(texto + "\n")
    else:
        print(texto)


if __name__ == "__main__":
    main()
