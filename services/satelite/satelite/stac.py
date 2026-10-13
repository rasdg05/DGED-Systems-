"""Búsqueda de escenas y lectura del recorte. Esto SÍ usa red.

Fuente: Sentinel-2 L2A en Earth Search (Element84), COG públicos en S3, sin
clave (`MEMORY/FUENTES.md`, `stac.earthsearch.s2`, VIVA). Solo se lee la
ventana del recorte de cada COG, nunca la escena completa.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

from .indices import Bandas, disco, nubosidad, reflectancia
from .resultado import Escena

STAC_URL = "https://earth-search.aws.element84.com/v1"
COLECCION = "sentinel-2-l2a"
#: Escenas con más nubosidad publicada que esto ni se evalúan (el recorte casi
#: nunca sale limpio). El veredicto lo da el SCL del recorte, no este número.
NUBES_ESCENA_MAX = 90.0
#: Cuántas candidatas por mosaico se leen (SCL del recorte) antes de quedarse
#: con la mejor.
CANDIDATAS_POR_MOSAICO = 8

BANDAS = ("blue", "green", "red", "nir", "swir16")

_ENV_GDAL = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "AWS_NO_SIGN_REQUEST": "YES",
    "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    "GDAL_HTTP_MULTIRANGE": "YES",
    "VSI_CACHE": "TRUE",
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_RETRY_DELAY": "2",
}


@dataclass
class Recorte:
    """La caja en la proyección del mosaico: centro ± radio, a 10 m."""

    epsg: int
    x0: float
    y0: float
    x1: float
    y1: float
    n: int  # píxeles por lado

    @classmethod
    def para(cls, lat: float, lon: float, radio_m: float, epsg: int) -> Recorte:
        from rasterio.warp import transform

        xs, ys = transform("EPSG:4326", f"EPSG:{epsg}", [lon], [lat])
        # Alinear a la rejilla de 10 m de Sentinel-2 (origen en múltiplos de 10).
        cx, cy = round(xs[0] / 10) * 10, round(ys[0] / 10) * 10
        n = int(round(2 * radio_m / 10))
        return cls(epsg, cx - n * 5, cy - n * 5, cx + n * 5, cy + n * 5, n)

    def a_latlon(self, fila: float, columna: float) -> tuple[float, float]:
        from rasterio.warp import transform

        x = self.x0 + (columna + 0.5) * 10
        y = self.y1 - (fila + 0.5) * 10
        lons, lats = transform(f"EPSG:{self.epsg}", "EPSG:4326", [x], [y])
        return lats[0], lons[0]


def _epsg(item) -> int | None:
    code = item.properties.get("proj:code") or ""
    if code.startswith("EPSG:"):
        return int(code.split(":")[1])
    return item.properties.get("proj:epsg")


def _mosaico(item) -> str | None:
    g = item.properties.get("grid:code") or ""
    if g.startswith("MGRS-"):
        return g[5:]
    m = [item.properties.get(k) for k in ("mgrs:utm_zone", "mgrs:latitude_band", "mgrs:grid_square")]
    return "".join(str(x) for x in m) if all(m) else None


def buscar(lat: float, lon: float, ventana: tuple[str, str], url: str = STAC_URL) -> list:
    from pystac_client import Client

    cliente = Client.open(url)
    busqueda = cliente.search(
        collections=[COLECCION],
        intersects={"type": "Point", "coordinates": [lon, lat]},
        datetime=f"{ventana[0]}/{ventana[1]}",
        query={"eo:cloud_cover": {"lt": NUBES_ESCENA_MAX}},
        max_items=200,
    )
    items = list(busqueda.items())
    items.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100.0))
    return items


def _leer(href: str, recorte: Recorte) -> np.ndarray:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds

    with rasterio.Env(**_ENV_GDAL), rasterio.open(href) as ds:
        ventana = from_bounds(recorte.x0, recorte.y0, recorte.x1, recorte.y1, ds.transform)
        return ds.read(
            1,
            window=ventana,
            out_shape=(recorte.n, recorte.n),
            resampling=Resampling.nearest,
            boundless=True,
            fill_value=0,
        )


def _escala(item, banda: str) -> tuple[float, float]:
    rb = (item.assets[banda].extra_fields.get("raster:bands") or [{}])[0]
    return float(rb.get("scale", 0.0001)), float(rb.get("offset", 0.0))


def nubosidad_del_recorte(item, recorte: Recorte) -> tuple[float, np.ndarray]:
    scl = _leer(item.assets["scl"].href, recorte)
    return nubosidad(scl, disco(recorte.n, recorte.n)), scl


def leer_bandas(item, recorte: Recorte, scl: np.ndarray | None = None) -> Bandas:
    capas = {}
    for b in BANDAS:
        escala, offset = _escala(item, b)
        capas[b] = reflectancia(_leer(item.assets[b].href, recorte), escala, offset)
    if scl is None:
        scl = _leer(item.assets["scl"].href, recorte)
    return Bandas(scl=scl, **capas)


def a_escena(item, nub_recorte: float) -> Escena:
    enlace = None
    for link in item.links:
        if link.rel == "self":
            enlace = link.href
    return Escena(
        id=item.id,
        fecha=item.properties.get("datetime"),
        nubosidad_recorte=round(float(nub_recorte), 4),
        nubosidad_escena=item.properties.get("eo:cloud_cover"),
        mosaico=_mosaico(item),
        epsg=_epsg(item),
        fuente=STAC_URL,
        enlace=enlace or f"{STAC_URL}/collections/{COLECCION}/items/{item.id}",
    )


def elegir_par(lat: float, lon: float, radio_m: float, ventana_antes, ventana_despues, log=None):
    """Elige, por mosaico MGRS común, la escena con menos nubes EN EL RECORTE de cada ventana.

    Las dos fechas deben salir del mismo mosaico (misma proyección y rejilla),
    si no los píxeles no se corresponden. Devuelve
    `(recorte, (item_a, nub_a, scl_a) | None, (item_d, nub_d, scl_d) | None)`.
    """
    log = log or (lambda *_: None)
    items_a = buscar(lat, lon, ventana_antes)
    items_d = buscar(lat, lon, ventana_despues)
    log(f"candidatas: antes {len(items_a)}, después {len(items_d)}")

    def por_mosaico(items):
        g: dict[str, list] = {}
        for it in items:
            g.setdefault(_mosaico(it) or "?", []).append(it)
        return g

    ga, gd = por_mosaico(items_a), por_mosaico(items_d)
    comunes = [m for m in ga if m in gd] or list(ga or gd)
    mejor = None
    for m in comunes:
        muestra = (ga.get(m) or gd.get(m))[0]
        epsg = _epsg(muestra)
        recorte = Recorte.para(lat, lon, radio_m, epsg)
        elegidas = []
        for grupo in (ga.get(m, []), gd.get(m, [])):
            top = None
            for it in grupo[:CANDIDATAS_POR_MOSAICO]:
                try:
                    nub, scl = nubosidad_del_recorte(it, recorte)
                except Exception as e:  # una lectura fallida no inventa una escena
                    log(f"  {it.id}: no se pudo leer el SCL ({type(e).__name__})")
                    continue
                log(f"  {m} {it.id}: escena {it.properties.get('eo:cloud_cover'):.1f}% · recorte {nub:.1%}")
                if top is None or nub < top[1]:
                    top = (it, nub, scl)
                if nub == 0.0:
                    break
            elegidas.append(top)
        peor = max((e[1] if e else 1.0) for e in elegidas)
        if mejor is None or peor < mejor[0]:
            mejor = (peor, recorte, elegidas[0], elegidas[1])
    if mejor is None:
        return None, None, None
    return mejor[1], mejor[2], mejor[3]


def configurar_proxy_ca() -> None:
    """GDAL/curl usan su propio almacén de CA; si hay un bundle declarado, se le pasa."""
    for var in ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE"):
        if os.environ.get(var):
            os.environ.setdefault("CURL_CA_BUNDLE", os.environ[var])
            break
