"""PNG antes / después / mapa de cambio. Sin red."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from .indices import Bandas, disco, mascara_valida

#: Colores del mapa de cambio (RGB).
COLORES = {
    1: (255, 140, 0),  # vegetación → suelo: naranja
    2: (230, 30, 200),  # suelo → construido: magenta
    3: (40, 200, 70),  # reverdecimiento: verde
}
GRIS_NUBE = (150, 150, 160)


def _rgb(b: Bandas, lo: float, hi: float) -> np.ndarray:
    pila = np.stack([b.red, b.green, b.blue], axis=-1)
    pila = np.nan_to_num(pila, nan=0.0)
    out = np.clip((pila - lo) / (hi - lo), 0, 1) ** (1 / 1.4)
    return (out * 255).astype(np.uint8)


def _estiramiento(antes: Bandas, despues: Bandas) -> tuple[float, float]:
    """Mismo estiramiento para las dos fechas: si no, un cambio de color sería del dibujo."""
    vals = []
    for b in (antes, despues):
        ok = mascara_valida(b.scl)
        for c in (b.red, b.green, b.blue):
            v = c[ok & np.isfinite(c)]
            if v.size:
                vals.append(v)
    if not vals:
        return 0.0, 0.3
    todo = np.concatenate(vals)
    lo, hi = np.percentile(todo, [2, 98])
    return float(lo), float(max(hi, lo + 0.01))


def _contorno(img: Image.Image, n: int, escala: int) -> None:
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, n * escala - 1, n * escala - 1], outline=(255, 255, 255), width=max(1, escala))


def dibujar(
    antes: Bandas | None,
    despues: Bandas | None,
    mapa: np.ndarray | None,
    titulos: tuple[str, str, str],
    ruta: str,
    escala: int = 1,
) -> str:
    paneles = []
    n = None
    if antes is not None and despues is not None:
        lo, hi = _estiramiento(antes, despues)
        a, d = _rgb(antes, lo, hi), _rgb(despues, lo, hi)
        n = a.shape[0]
        fondo = (0.6 * d).astype(np.uint8)
        nube = ~(mascara_valida(antes.scl) & mascara_valida(despues.scl))
        fondo[nube] = GRIS_NUBE
        if mapa is not None:
            for codigo, color in COLORES.items():
                fondo[mapa == codigo] = color
        fuera = ~disco(n, n)
        for arr in (a, d, fondo):
            arr[fuera] = (arr[fuera] * 0.35).astype(np.uint8)
        paneles = [a, d, fondo]
    if not paneles:
        n = 200
        paneles = [np.full((n, n, 3), 40, np.uint8)] * 3

    cab = 34
    ancho = n * escala
    lienzo = Image.new("RGB", (3 * ancho + 20, ancho + cab + 18), (18, 18, 22))
    dib = ImageDraw.Draw(lienzo)
    for i, (arr, titulo) in enumerate(zip(paneles, titulos, strict=True)):
        im = Image.fromarray(arr).resize((ancho, ancho), Image.NEAREST)
        _contorno(im, n, escala)
        x = i * (ancho + 10)
        lienzo.paste(im, (x, cab))
        for k, linea in enumerate(titulo.split("\n")[:2]):
            dib.text((x + 2, 2 + 14 * k), linea, fill=(235, 235, 235))
    ley = "naranja: vegetacion->suelo   magenta: suelo->construido   verde: reverdecimiento   gris: nube/sombra"
    dib.text((4, ancho + cab + 3), ley, fill=(200, 200, 200))
    lienzo.save(ruta, optimize=True)
    return ruta
