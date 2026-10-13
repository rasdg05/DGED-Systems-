"""Detección de cambio entre dos ventanas de fecha para un punto y un radio.

    python -m satelite.cambios --lat 25.7789 --lon -100.1886 \\
        --antes 2024-01-01:2024-03-31 --despues 2026-07-01:2026-09-30

Imprime el JSON del resultado y, con `--salida`, deja `<nombre>.json` y
`<nombre>.png` (antes / después / mapa de cambio).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .indices import AREA_MINIMA_PX, HA_POR_PIXEL_10M, clasificar, disco, filtrar_por_area
from .render import dibujar
from .resultado import construir, motivo_para_no_concluir


def _ventana(texto: str) -> tuple[str, str]:
    a, b = texto.split(":")
    return a.strip(), b.strip()


def analizar(
    lat: float,
    lon: float,
    ventana_antes: tuple[str, str],
    ventana_despues: tuple[str, str],
    radio_m: float = 1500.0,
    nombre: str | None = None,
    salida: Path | None = None,
    log=None,
) -> dict:
    from . import stac

    stac.configurar_proxy_ca()
    log = log or (lambda *_: None)
    recorte, sel_a, sel_d = stac.elegir_par(lat, lon, radio_m, ventana_antes, ventana_despues, log=log)

    esc_a = stac.a_escena(sel_a[0], sel_a[1]) if sel_a else None
    esc_d = stac.a_escena(sel_d[0], sel_d[1]) if sel_d else None
    region = disco(recorte.n, recorte.n) if recorte else None
    area_ha = round(float(region.sum()) * HA_POR_PIXEL_10M, 2) if region is not None else None

    bandas_a = bandas_d = cambio = None
    latlon = None
    motivo = motivo_para_no_concluir(esc_a, esc_d)
    # Solo se leen las bandas si el par se puede concluir (o para dibujarlo).
    if esc_a and esc_d:
        bandas_a = stac.leer_bandas(sel_a[0], recorte, sel_a[2])
        bandas_d = stac.leer_bandas(sel_d[0], recorte, sel_d[2])
        if motivo is None:
            cambio = filtrar_por_area(clasificar(bandas_a, bandas_d, region))
            latlon = [recorte.a_latlon(z.fila, z.columna) for z in cambio.zonas]

    png = None
    if salida is not None:
        salida.mkdir(parents=True, exist_ok=True)
        base = nombre or f"{lat:.4f}_{lon:.4f}"
        png = str(salida / f"{base}.png")
        ta = f"ANTES {esc_a.fecha[:10]}  nubes {esc_a.nubosidad_recorte:.0%}\n{esc_a.id}" if esc_a else "ANTES: sin escena"
        td = f"DESPUES {esc_d.fecha[:10]}  nubes {esc_d.nubosidad_recorte:.0%}\n{esc_d.id}" if esc_d else "DESPUES: sin escena"
        if cambio is not None:
            tc = f"CAMBIO {cambio.hectareas():.1f} ha (min {AREA_MINIMA_PX * HA_POR_PIXEL_10M:.1f} ha)\nradio {radio_m:.0f} m · {nombre or ''}"
        else:
            tc = f"NO CONCLUYE\n{(motivo or '')[:60]}"
        dibujar(bandas_a, bandas_d, cambio.mapa if cambio else None, (ta, td, tc), png)

    resultado = construir(
        lat=lat, lon=lon, radio_m=radio_m, ventana_antes=ventana_antes, ventana_despues=ventana_despues,
        antes=esc_a, despues=esc_d, cambio=cambio, zonas_latlon=latlon, area_disco_ha=area_ha,
        nombre=nombre, png=png,
    )
    if salida is not None:
        (salida / f"{nombre or f'{lat:.4f}_{lon:.4f}'}.json").write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return resultado


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m satelite.cambios", description=__doc__.split("\n")[0])
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--antes", type=_ventana, required=True, help="AAAA-MM-DD:AAAA-MM-DD")
    p.add_argument("--despues", type=_ventana, required=True, help="AAAA-MM-DD:AAAA-MM-DD")
    p.add_argument("--radio", type=float, default=1500.0, help="metros (1500 por defecto)")
    p.add_argument("--nombre", default=None)
    p.add_argument("--salida", type=Path, default=None, help="carpeta para el JSON y el PNG")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    log = (lambda m: print(m, file=sys.stderr)) if a.verbose else None
    r = analizar(a.lat, a.lon, a.antes, a.despues, a.radio, a.nombre, a.salida, log=log)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
