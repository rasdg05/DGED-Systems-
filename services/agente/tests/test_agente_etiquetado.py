"""El etiquetado ciego como comando (`etiquetado.py`, corrida GM del 2026-10-29)."""
from __future__ import annotations

import json

from agente import etiquetado, historial
from agente.historial import Mensaje


def test_etiquetado_lotes_ciegos_sin_telefonos_y_la_medida(espacio):
    hilos = {f"52177700000{i:02d}": ["Precio para 20?", "Gracias ya tenemos opción", "Ok gracias"][i % 3]
             for i in range(9)}
    historial.guardar(espacio, [Mensaje(f"m{i}", h, False, 1790000000 + i, "text", t)
                                for i, (h, t) in enumerate(hilos.items())])
    carpeta = etiquetado.lotes(espacio, n_lotes=2)
    lote = (carpeta / "lote1.json").read_text(encoding="utf-8")
    assert "5217770000" not in lote and "estado" not in lote             # ciego y sin teléfonos
    clave = json.loads((carpeta / "clave.json").read_text(encoding="utf-8"))
    oro = {"espera": "espera", "no_pide": "cierre"}
    for nombre in ("A", "B"):
        etiquetas = {c: {"etiqueta": oro[v["estado"]], "caliente": False, "nota": ""} for c, v in clave.items()}
        (carpeta / f"{nombre}_lote1.json").write_text(json.dumps(etiquetas), encoding="utf-8")
    r = etiquetado.medir(carpeta)
    assert r["kappa"] == 1.0 and r["clasificador"] == 1.0 and r["oro"] == len(clave) and not r["concluye"]


def test_etiquetado_kappa():
    assert etiquetado.kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == (1.0, 1.0)
    assert etiquetado.kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"])[1] == 0.0
