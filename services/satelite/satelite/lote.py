"""Corre el detector sobre los 10 sitios de `services/api/atlas/seed.py` y sobre
obras con fecha de construcción pública (`OBRAS`).

    python -m satelite.lote --antes 2024-01-01:2024-04-30 \\
        --despues 2026-01-01:2026-04-30 --salida docs/satelite/estacion-seca

Deja un JSON y un PNG por sitio y un `resumen.json`.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from .cambios import _ventana, analizar

RAIZ = Path(__file__).resolve().parents[3]
SEED = RAIZ / "services" / "api" / "atlas" / "seed.py"

#: Obras con fecha pública. Coordenadas: OpenStreetMap (Nominatim, 2026-10-13),
#: del punto con nombre de la empresa; la nave nueva está DENTRO del radio, no
#: necesariamente en el centro. Fuentes en docs/12-ojo-satelital.md.
OBRAS = [
    {
        "id": "obra-bmw-slp-baterias",
        "name": "BMW SLP, centro de módulos de baterías (81,876 m², obra desde 2024-05-03)",
        "lat": 21.9682649,
        "lon": -100.8491733,
    },
    {
        "id": "obra-lego-cienega",
        "name": "LEGO Ciénega de Flores, nave de 59,000 m² (lista prevista 2025-05)",
        "lat": 25.8924450,
        "lon": -100.2396748,
    },
]


def sitios_seed() -> list[dict]:
    spec = importlib.util.spec_from_file_location("atlas_seed", SEED)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SITES


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m satelite.lote")
    p.add_argument("--antes", type=_ventana, required=True)
    p.add_argument("--despues", type=_ventana, required=True)
    p.add_argument("--radio", type=float, default=1500.0)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--solo", default=None, help="ids separados por coma")
    a = p.parse_args(argv)

    lugares = [{**s, "grupo": "seed"} for s in sitios_seed()] + [{**o, "grupo": "obra"} for o in OBRAS]
    if a.solo:
        quiero = set(a.solo.split(","))
        lugares = [s for s in lugares if s["id"] in quiero]
    resumen = []
    for s in lugares:
        print(f"== {s['id']}", file=sys.stderr)
        try:
            r = analizar(s["lat"], s["lon"], a.antes, a.despues, a.radio, s["id"], a.salida,
                         log=lambda m: print(m, file=sys.stderr))
        except Exception as e:  # la red falla: se reporta, no se inventa
            r = {"estado": "no_concluye", "motivo": f"error de lectura: {type(e).__name__}: {e}",
                 "hectareas_cambiadas": None, "escenas_citadas": []}
        resumen.append({
            "id": s["id"], "grupo": s["grupo"], "nombre": s["name"],
            "estado": r["estado"], "motivo": r.get("motivo"),
            "antes": (r.get("antes") or {}).get("id"), "fecha_antes": ((r.get("antes") or {}).get("fecha") or "")[:10],
            "nub_antes": (r.get("antes") or {}).get("nubosidad_recorte"),
            "despues": (r.get("despues") or {}).get("id"), "fecha_despues": ((r.get("despues") or {}).get("fecha") or "")[:10],
            "nub_despues": (r.get("despues") or {}).get("nubosidad_recorte"),
            "ha_total": r.get("hectareas_cambiadas"), "ha_posible_obra": r.get("hectareas_posible_obra"),
            "ha_por_tipo": r.get("hectareas_por_tipo"),
        })
        print(json.dumps(resumen[-1], ensure_ascii=False), file=sys.stderr)
    a.salida.mkdir(parents=True, exist_ok=True)
    (a.salida / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
