"""Índices espectrales, máscara de nubes y detección de cambio. Solo numpy, sin red.

Todo lo que decide si "hubo cambio" vive aquí y está fijado por los tests de
`services/satelite/test_satelite.py`. Los umbrales son heurísticos de la
literatura de percepción remota, elegidos ANTES de ver los resultados de los
sitios; no están calibrados contra obras verificadas (n pequeño no calibra).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

# --- Píxel -----------------------------------------------------------------

#: Sentinel-2 en Earth Search: 10 m por píxel → 100 m² → 0.01 ha.
HA_POR_PIXEL_10M = 0.01

# --- Máscara de nubes (SCL de Sen2Cor) --------------------------------------

#: Clases SCL que NO son superficie observada: sin dato, saturado, sombra de
#: nube, nube media, nube alta, cirro y nieve. El resto (2 sombra oscura de
#: terreno, 4 vegetación, 5 suelo, 6 agua, 7 sin clasificar) se acepta.
SCL_INVALIDAS = (0, 1, 3, 8, 9, 10, 11)

#: Más de esta fracción del recorte sin superficie observada → "no concluye".
NUBOSIDAD_MAXIMA = 0.20

# --- Umbrales de cambio -----------------------------------------------------

#: Caída de NDVI que cuenta como pérdida de vegetación (0.20 es el umbral
#: habitual para desmonte en imágenes de 10 m).
DELTA_NDVI_PERDIDA = -0.20
#: NDVI antes por encima del cual el píxel "era vegetación".
NDVI_VEGETACION = 0.30
#: NDVI por debajo del cual el píxel "no es vegetación" (suelo, techo, asfalto).
NDVI_NO_VEGETACION = 0.25
#: Caída de BSI que, con el píxel sin vegetación en las dos fechas, se lee como
#: suelo desnudo sustituido por algo que refleja más azul que SWIR: techo
#: metálico o pavimento.
DELTA_BSI_CONSTRUIDO = -0.10
#: Cambio mínimo de brillo visible (reflectancia media R+G+B) para el caso
#: suelo→construido: sin él, una lluvia que oscurece el suelo pasaría por techo.
DELTA_BRILLO_CONSTRUIDO = 0.04
#: Aclarado fuerte de un píxel sin vegetación que termina con firma de no-suelo
#: (BSI ≤ 0): losa gris o terracería compactada que se vuelve techo claro. Se
#: agregó en la v0.2, DESPUÉS de mirar las dos obras de prueba: no está validado.
DELTA_BRILLO_TECHO = 0.08
#: BSI por debajo del cual el píxel "ya no parece suelo" (el suelo desnudo da BSI > 0).
BSI_NO_SUELO = 0.0
#: Subida de NDVI que se reporta como reverdecimiento (no es obra, se dice).
DELTA_NDVI_GANANCIA = 0.20

#: Área mínima de una zona de cambio, en píxeles de 10 m (50 px = 0.5 ha).
#: Una nave industrial chica ronda 1 ha; menos de 0.5 ha a 10 m es ruido de
#: borde o de co-registro.
AREA_MINIMA_PX = 50

TIPOS = {
    1: "vegetacion_a_suelo",
    2: "suelo_a_construido",
    3: "reverdecimiento",
    4: "vegetacion_a_construido",
}
#: Los tipos que pueden ser obra (el reverdecimiento no).
TIPOS_OBRA = ("vegetacion_a_suelo", "vegetacion_a_construido", "suelo_a_construido")


def reflectancia(dn: np.ndarray, escala: float = 0.0001, offset: float = -0.1, nodata: int = 0) -> np.ndarray:
    """De número digital a reflectancia de superficie; nodata → NaN."""
    dn = np.asarray(dn)
    r = dn.astype(np.float32) * np.float32(escala) + np.float32(offset)
    return np.where(dn == nodata, np.nan, r).astype(np.float32)


def _razon(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        out = a / b
    return np.where(np.isfinite(out), out, np.nan).astype(np.float32)


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    return _razon(nir - red, nir + red)


def ndbi(swir: np.ndarray, nir: np.ndarray) -> np.ndarray:
    return _razon(swir - nir, swir + nir)


def bsi(swir: np.ndarray, red: np.ndarray, nir: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Bare Soil Index: ((SWIR+R) − (NIR+B)) / ((SWIR+R) + (NIR+B))."""
    return _razon((swir + red) - (nir + blue), (swir + red) + (nir + blue))


def brillo(red: np.ndarray, green: np.ndarray, blue: np.ndarray) -> np.ndarray:
    return ((red + green + blue) / 3.0).astype(np.float32)


def mascara_valida(scl: np.ndarray) -> np.ndarray:
    """True donde el SCL dice que se ve la superficie."""
    return ~np.isin(np.asarray(scl), SCL_INVALIDAS)


def nubosidad(scl: np.ndarray, region: np.ndarray | None = None) -> float:
    """Fracción del recorte (o de `region`) sin superficie observada. Vacío → 1.0."""
    invalida = ~mascara_valida(scl)
    if region is not None:
        invalida = invalida[region]
    if invalida.size == 0:
        return 1.0
    return float(invalida.mean())


def disco(alto: int, ancho: int) -> np.ndarray:
    """Máscara del círculo inscrito en el recorte: el radio pedido, no el cuadrado."""
    yy, xx = np.mgrid[0:alto, 0:ancho]
    cy, cx = (alto - 1) / 2.0, (ancho - 1) / 2.0
    r = min(alto, ancho) / 2.0
    return (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r


@dataclass
class Bandas:
    """Reflectancias de una fecha, ya en la misma rejilla de 10 m."""

    blue: np.ndarray
    green: np.ndarray
    red: np.ndarray
    nir: np.ndarray
    swir16: np.ndarray
    scl: np.ndarray

    def indices(self) -> dict[str, np.ndarray]:
        return {
            "ndvi": ndvi(self.nir, self.red),
            "ndbi": ndbi(self.swir16, self.nir),
            "bsi": bsi(self.swir16, self.red, self.nir, self.blue),
            "brillo": brillo(self.red, self.green, self.blue),
        }


def clasificar(antes: Bandas, despues: Bandas, region: np.ndarray | None = None) -> np.ndarray:
    """Mapa de tipo de cambio por píxel (0 = sin cambio, ver `TIPOS`).

    Un píxel solo puede cambiar si se ve en las dos fechas (SCL válido) y si
    está dentro de `region`. Antes de filtrar por área.
    """
    a, d = antes.indices(), despues.indices()
    valido = mascara_valida(antes.scl) & mascara_valida(despues.scl)
    for idx in (a, d):
        for v in idx.values():
            valido &= np.isfinite(v)
    if region is not None:
        valido &= region

    dndvi = d["ndvi"] - a["ndvi"]
    dbsi = d["bsi"] - a["bsi"]
    dbrillo = d["brillo"] - a["brillo"]

    perdida = (a["ndvi"] >= NDVI_VEGETACION) & (dndvi <= DELTA_NDVI_PERDIDA) & (d["ndvi"] < NDVI_VEGETACION)
    # Después de perder la vegetación, ¿quedó suelo o algo que ya no es suelo y aclaró (techo)?
    a_techo = (d["bsi"] <= BSI_NO_SUELO) & (dbrillo >= DELTA_BRILLO_CONSTRUIDO)
    sin_veg = (a["ndvi"] < NDVI_NO_VEGETACION) & (d["ndvi"] < NDVI_NO_VEGETACION)
    construido = sin_veg & (
        ((dbsi <= DELTA_BSI_CONSTRUIDO) & (np.abs(dbrillo) >= DELTA_BRILLO_CONSTRUIDO))
        | ((dbrillo >= DELTA_BRILLO_TECHO) & (d["bsi"] <= BSI_NO_SUELO))
    )
    ganancia = dndvi >= DELTA_NDVI_GANANCIA

    tipo = np.zeros(valido.shape, dtype=np.uint8)
    tipo[ganancia & valido] = 3
    tipo[construido & valido] = 2
    tipo[perdida & ~a_techo & valido] = 1
    tipo[perdida & a_techo & valido] = 4
    return tipo


@dataclass
class Zona:
    tipo: str
    pixeles: int
    hectareas: float
    fila: float
    columna: float


def _componentes(mascara: np.ndarray) -> list[np.ndarray]:
    """Componentes 4-conexas de una máscara booleana (índices planos de cada una)."""
    alto, ancho = mascara.shape
    visto = np.zeros_like(mascara, dtype=bool)
    out: list[np.ndarray] = []
    for f0, c0 in zip(*np.nonzero(mascara), strict=True):
        if visto[f0, c0]:
            continue
        cola = deque([(f0, c0)])
        visto[f0, c0] = True
        miembros = []
        while cola:
            f, c = cola.popleft()
            miembros.append(f * ancho + c)
            for df, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nf, nc = f + df, c + dc
                if 0 <= nf < alto and 0 <= nc < ancho and mascara[nf, nc] and not visto[nf, nc]:
                    visto[nf, nc] = True
                    cola.append((nf, nc))
        out.append(np.asarray(miembros, dtype=np.int64))
    return out


@dataclass
class Cambio:
    mapa: np.ndarray  # tipo por píxel, ya filtrado por área mínima
    zonas: list[Zona] = field(default_factory=list)

    def hectareas(self, tipo: str | None = None) -> float:
        return round(sum(z.hectareas for z in self.zonas if tipo is None or z.tipo == tipo), 2)


def filtrar_por_area(tipo: np.ndarray, area_minima_px: int = AREA_MINIMA_PX) -> Cambio:
    """Quita las manchas menores que el área mínima y devuelve las zonas que quedan."""
    filtrado = np.zeros_like(tipo)
    zonas: list[Zona] = []
    ancho = tipo.shape[1]
    for codigo, nombre in TIPOS.items():
        for miembros in _componentes(tipo == codigo):
            if miembros.size < area_minima_px:
                continue
            filas, cols = miembros // ancho, miembros % ancho
            filtrado[filas, cols] = codigo
            zonas.append(
                Zona(
                    tipo=nombre,
                    pixeles=int(miembros.size),
                    hectareas=round(miembros.size * HA_POR_PIXEL_10M, 2),
                    fila=float(filas.mean()),
                    columna=float(cols.mean()),
                )
            )
    zonas.sort(key=lambda z: -z.pixeles)
    return Cambio(mapa=filtrado, zonas=zonas)
