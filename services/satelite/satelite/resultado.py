"""El resultado que se entrega. Sin red: decide si concluye y qué cita.

La regla: **un cambio solo existe si las dos escenas existen, se citan y se ven**.
Sin escena en una ventana, o con el recorte más nublado que `NUBOSIDAD_MAXIMA`,
el resultado es "no_concluye" y las hectáreas son `None` — nunca 0, porque 0
afirmaría que se miró y no hubo cambio.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from . import indices as _ix
from .indices import AREA_MINIMA_PX, NUBOSIDAD_MAXIMA, TIPOS, Cambio

VERSION = "satelite-0.1.0"


@dataclass
class Escena:
    id: str
    fecha: str  # ISO 8601 UTC de la toma
    nubosidad_recorte: float  # fracción 0–1 del disco sin superficie observada (SCL)
    nubosidad_escena: float | None  # % que publica el catálogo para la escena entera
    mosaico: str | None  # MGRS, p. ej. "14RLP"
    epsg: int | None
    fuente: str  # catálogo STAC de donde salió
    enlace: str | None = None  # URL del item STAC


def umbrales() -> dict:
    return {
        "nubosidad_maxima_recorte": NUBOSIDAD_MAXIMA,
        "scl_invalidas": list(_ix.SCL_INVALIDAS),
        "delta_ndvi_perdida": _ix.DELTA_NDVI_PERDIDA,
        "ndvi_vegetacion": _ix.NDVI_VEGETACION,
        "ndvi_no_vegetacion": _ix.NDVI_NO_VEGETACION,
        "delta_bsi_construido": _ix.DELTA_BSI_CONSTRUIDO,
        "delta_brillo_construido": _ix.DELTA_BRILLO_CONSTRUIDO,
        "delta_ndvi_ganancia": _ix.DELTA_NDVI_GANANCIA,
        "area_minima_px": AREA_MINIMA_PX,
        "area_minima_ha": round(AREA_MINIMA_PX * _ix.HA_POR_PIXEL_10M, 2),
    }


def _misma_estacion(antes: tuple[str, str], despues: tuple[str, str]) -> bool:
    """¿Las dos ventanas cubren los mismos meses del año? (aviso de fenología)."""

    def meses(v: tuple[str, str]) -> set[int]:
        y, m = int(v[0][:4]), int(v[0][5:7])
        fin = (int(v[1][:4]), int(v[1][5:7]))
        out: set[int] = set()
        while (y, m) <= fin and len(out) < 12:
            out.add(m)
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        return out

    ma, md = meses(antes), meses(despues)
    return len(ma & md) >= 0.5 * min(len(ma), len(md))


def construir(
    *,
    lat: float,
    lon: float,
    radio_m: float,
    ventana_antes: tuple[str, str],
    ventana_despues: tuple[str, str],
    antes: Escena | None,
    despues: Escena | None,
    cambio: Cambio | None,
    zonas_latlon: list[tuple[float, float]] | None = None,
    area_disco_ha: float | None = None,
    nombre: str | None = None,
    png: str | None = None,
) -> dict:
    """Arma el JSON del resultado. Es el único lugar que decide "concluye"."""
    base = {
        "version": VERSION,
        "nombre": nombre,
        "punto": {"lat": lat, "lon": lon},
        "radio_m": radio_m,
        "area_analizada_ha": area_disco_ha,
        "ventanas": {"antes": list(ventana_antes), "despues": list(ventana_despues)},
        "antes": asdict(antes) if antes else None,
        "despues": asdict(despues) if despues else None,
        "escenas_citadas": [e.id for e in (antes, despues) if e is not None],
        "umbrales": umbrales(),
        "avisos": [],
        "png": png,
    }
    if not _misma_estacion(ventana_antes, ventana_despues):
        base["avisos"].append(
            "Ventanas de distinta estación: la pérdida o ganancia de vegetación puede ser fenología o cultivo, no obra."
        )

    motivo = motivo_para_no_concluir(antes, despues)
    if motivo:
        return _no_concluye(base, motivo)
    if cambio is None:
        return _no_concluye(base, "no se calculó el cambio")

    zonas = []
    for i, z in enumerate(cambio.zonas):
        item = {"tipo": z.tipo, "hectareas": z.hectareas, "pixeles": z.pixeles}
        if zonas_latlon and i < len(zonas_latlon):
            item["centroide"] = {"lat": round(zonas_latlon[i][0], 6), "lon": round(zonas_latlon[i][1], 6)}
        zonas.append(item)

    base.update(
        {
            "estado": "concluye",
            "motivo": None,
            "hectareas_cambiadas": cambio.hectareas(),
            "hectareas_por_tipo": {nombre: cambio.hectareas(nombre) for nombre in TIPOS.values()},
            "zonas": zonas,
        }
    )
    assert_citado(base)
    return base


def motivo_para_no_concluir(antes: Escena | None, despues: Escena | None) -> str | None:
    """Por qué este par de escenas no puede dar un cambio; None si sí puede."""
    faltan = [n for n, e in (("antes", antes), ("despues", despues)) if e is None]
    if faltan:
        return f"sin escena utilizable en la ventana {', '.join(faltan)}"
    nubladas = [
        f"{n} ({e.nubosidad_recorte:.0%})"
        for n, e in (("antes", antes), ("despues", despues))
        if e.nubosidad_recorte > NUBOSIDAD_MAXIMA
    ]
    if nubladas:
        return f"recorte con nubosidad sobre {NUBOSIDAD_MAXIMA:.0%}: {', '.join(nubladas)}"
    return None


def _no_concluye(base: dict, motivo: str) -> dict:
    base.update(
        {
            "estado": "no_concluye",
            "motivo": motivo,
            "hectareas_cambiadas": None,
            "hectareas_por_tipo": None,
            "zonas": [],
        }
    )
    return base


def assert_citado(resultado: dict) -> None:
    """Invariante: hay hectáreas solo si hay dos escenas citadas, con ID y fecha."""
    if resultado.get("hectareas_cambiadas") is None:
        return
    for lado in ("antes", "despues"):
        e = resultado.get(lado)
        if not e or not e.get("id") or not e.get("fecha"):
            raise ValueError(f"cambio sin escena citada ({lado})")
    if len(resultado.get("escenas_citadas", [])) != 2:
        raise ValueError("cambio sin las dos escenas citadas")
