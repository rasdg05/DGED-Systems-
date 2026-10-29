"""Etiquetado ciego de los pendientes: dos etiquetadores, kappa y el clasificador contra el oro.

Corrida GM del 2026-10-29 (Gestor, B2: *"dos etiquetadores independientes y lo que no
coincide va a la lista para el dueño"*). Se hizo a mano sobre los 268 pendientes de
Finca Emiliano (kappa 0.947; clasificador 92.1% → 96.6%) y aquí queda como comando,
para medir **fuera de muestra** con los pendientes de otro día:

    python -m agente.etiquetado lotes finca-quinta --lotes 4      # lotes ciegos + clave
    # dos agentes por lote escriben A_lote1.json y B_lote1.json (`ETIQUETAS`, abajo)
    python -m agente.etiquetado medir finca-quinta <carpeta>      # kappa, oro y clasificador

Los lotes no dicen qué leyó el clasificador (la clave va aparte) ni traen teléfonos.
Viven en `datos/espacios/<id>/etiquetado/` (fuera de git). Sin red ni modelo.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import historial, pendientes
from .espacio import Espacio

ETIQUETAS = ("espera", "aplaza", "cierre", "acuse", "medio", "otro")
#: Del oro de los etiquetadores al estado de `pendientes`.
A_ESTADO = {"espera": "espera", "medio": "solo_medios", "aplaza": "no_pide", "cierre": "no_pide",
            "acuse": "no_pide", "otro": "otro"}
MENSAJES = 10
GUIA = ("Para cada caso, UNA etiqueta sobre lo que el cliente dejó al final: espera (pide, pregunta o da un dato "
        "que el negocio debe contestar; un saludo solo a media plática también), aplaza (él vuelve, avisa, lo "
        "consulta), cierre (ya no: rentó en otro lado, canceló, no le interesa), acuse (gracias, ok, emoji), medio "
        "(solo foto, audio o documento sin texto), otro (explica). Además caliente: true si pide o trae fechas, "
        "personas o precio. Salida: {\"c000\": {\"etiqueta\": \"...\", \"caliente\": true, \"nota\": \"...\"}}.")


def lotes(espacio: Espacio, n_lotes: int = 4, semilla: int = 29) -> Path:
    from . import mesa
    hilos = mesa.clientes(espacio, historial.hilos(espacio))
    lista = pendientes.leer(hilos)
    random.Random(semilla).shuffle(lista)
    ahora = max((m.ts for ms in hilos.values() for m in ms), default=0)
    carpeta = espacio.ruta(f"etiquetado/{datetime.now(timezone.utc):%Y-%m-%dT%H%M}")
    carpeta.mkdir(parents=True, exist_ok=True)
    casos, clave = [], {}
    for i, p in enumerate(lista):
        caso = f"c{i:03d}"
        casos.append({"caso": caso, "mensajes": [
            {"de": "negocio" if m.del_negocio else "cliente", "hace_horas": round((ahora - m.ts) / 3600, 1),
             "tipo": m.tipo, "texto": (m.texto or "")[:600]} for m in hilos[p.hilo][-MENSAJES:]]})
        clave[caso] = {"hilo": p.hilo, "estado": p.estado, "ultimo_id": p.ultimo_id}
    tam = max(1, -(-len(casos) // max(1, n_lotes)))
    for k in range(0, len(casos), tam):
        (carpeta / f"lote{k // tam + 1}.json").write_text(json.dumps(casos[k:k + tam], ensure_ascii=False, indent=1),
                                                          encoding="utf-8")
    (carpeta / "clave.json").write_text(json.dumps(clave, ensure_ascii=False), encoding="utf-8")
    (carpeta / "GUIA.txt").write_text(GUIA, encoding="utf-8")
    return carpeta


def kappa(x: list[str], y: list[str]) -> tuple[float, float]:
    """(acuerdo, kappa de Cohen)."""
    n = len(x)
    if not n:
        return 0.0, 0.0
    po = sum(a == b for a, b in zip(x, y, strict=True)) / n
    ca, cb = Counter(x), Counter(y)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return round(po, 3), round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def medir(carpeta: Path, estados_hoy: dict[str, tuple[str, str]] | None = None) -> dict:
    """`estados_hoy`: hilo → (estado, ultimo_id) del clasificador de hoy; sin él, el de la clave."""
    clave = json.loads((carpeta / "clave.json").read_text(encoding="utf-8"))
    a, b = {}, {}
    for ruta in sorted(carpeta.glob("A_lote*.json")):
        a.update(json.loads(ruta.read_text(encoding="utf-8")))
    for ruta in sorted(carpeta.glob("B_lote*.json")):
        b.update(json.loads(ruta.read_text(encoding="utf-8")))
    ids = sorted(set(a) & set(b) & set(clave))
    acuerdo, k = kappa([a[i]["etiqueta"] for i in ids], [b[i]["etiqueta"] for i in ids])
    oro = {i: A_ESTADO.get(a[i]["etiqueta"], "otro") for i in ids
           if A_ESTADO.get(a[i]["etiqueta"]) == A_ESTADO.get(b[i]["etiqueta"])}
    if estados_hoy is not None:  # solo los que siguen terminando en el mismo mensaje
        oro = {i: e for i, e in oro.items() if estados_hoy.get(clave[i]["hilo"], ("", ""))[1] == clave[i]["ultimo_id"]}
    cl = {i: (estados_hoy[clave[i]["hilo"]][0] if estados_hoy is not None else clave[i]["estado"]) for i in oro}
    ok = sum(cl[i] == oro[i] for i in oro)
    tp = sum(cl[i] == "espera" == oro[i] for i in oro)
    fp = sum(cl[i] == "espera" != oro[i] for i in oro)
    fn = sum(oro[i] == "espera" != cl[i] for i in oro)
    return {"n": len(ids), "acuerdo": acuerdo, "kappa": k, "oro": len(oro),
            "clasificador": round(ok / len(oro), 3) if oro else None,
            "espera_precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "espera_recall": round(tp / (tp + fn), 3) if tp + fn else None,
            "errores": Counter(f"{cl[i]}→{oro[i]}" for i in oro if cl[i] != oro[i]).most_common(),
            "desacuerdos": [i for i in ids if i not in oro], "concluye": len(oro) >= 30}


def main(argv: list[str] | None = None) -> int:
    from .local import _espacio

    ap = argparse.ArgumentParser(prog="python -m agente.etiquetado", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="orden", required=True)
    lo = sub.add_parser("lotes")
    lo.add_argument("cliente_id"), lo.add_argument("--lotes", type=int, default=4)
    me = sub.add_parser("medir")
    me.add_argument("cliente_id"), me.add_argument("carpeta")
    a = ap.parse_args(argv)
    espacio = _espacio(a.cliente_id)
    if a.orden == "lotes":
        print(lotes(espacio, a.lotes))
        return 0
    from . import mesa
    hoy = {p.hilo: (p.estado, p.ultimo_id) for p in pendientes.leer(mesa.clientes(espacio, historial.hilos(espacio)))}
    print(json.dumps(medir(Path(a.carpeta), hoy), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
