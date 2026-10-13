"""CLI: python -m dataroom.leer CARPETA --salida DIR

Lee los PDF de la carpeta, extrae con Claude, verifica cada cita, cruza y
escribe rent_roll.csv, hallazgos.json y memo.md en DIR.

Dormido sin ANTHROPIC_API_KEY: sale con código 2 y un mensaje claro, sin leer
nada. Con --respuestas-grabadas no llama a la API (muestra y pruebas).
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from . import cruces, extraccion, salida
from .grabado import ClienteGrabado
from .textos import leer_carpeta

SIN_CLAVE = 2


def correr(carpeta: Path, destino: Path, client, modelo: str, fecha_corte: date, meses: int, modo: str) -> dict:
    leida = leer_carpeta(carpeta)
    resultados = [extraccion.leer_documento(client, modelo, doc) for doc in leida.documentos if doc.legible]
    paginas = {doc.nombre: len(doc.paginas) for doc in leida.documentos}
    banderas = cruces.cruzar(resultados, paginas, fecha_corte, meses)
    transcripciones = cruces.transcripciones_de_suministro(resultados)
    return salida.escribir(destino, leida, resultados, banderas, transcripciones, fecha_corte, meses, modelo, modo)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m dataroom.leer", description="Lector del cuarto de datos (DGED).")
    parser.add_argument("carpeta", type=Path, help="Carpeta con los PDF del cuarto de datos.")
    parser.add_argument("--salida", type=Path, required=True, help="Carpeta donde se escriben rent_roll.csv, hallazgos.json y memo.md.")
    parser.add_argument("--fecha-corte", type=date.fromisoformat, default=None, help="AAAA-MM-DD; por defecto, hoy.")
    parser.add_argument("--meses", type=int, default=12, help="Horizonte para vencimientos (meses). Por defecto 12.")
    parser.add_argument("--modelo", default=None, help="ID del modelo; por defecto DATAROOM_MODEL o claude-opus-5-5.")
    parser.add_argument("--respuestas-grabadas", type=Path, default=None, help="JSON de respuestas grabadas: no llama a la API.")
    args = parser.parse_args(argv)

    if not args.carpeta.is_dir():
        print(f"No existe la carpeta: {args.carpeta}", file=sys.stderr)
        return 1
    if args.respuestas_grabadas:
        client, modo = ClienteGrabado.desde_archivo(args.respuestas_grabadas), "grabado"
    elif not extraccion.is_configured():
        print(extraccion.MENSAJE_SIN_CLAVE, file=sys.stderr)
        return SIN_CLAVE
    else:
        client, modo = extraccion.make_client(), "en_vivo"

    modelo = args.modelo or extraccion.model_name()
    hallazgos = correr(args.carpeta, args.salida, client, modelo, args.fecha_corte or date.today(), args.meses, modo)
    altas = sum(1 for b in hallazgos["banderas"] if b["severidad"] == cruces.ALTA)
    print(
        f"{len(hallazgos['documentos'])} documentos · {hallazgos['rent_roll_filas']} contratos en el rent roll · "
        f"{len(hallazgos['banderas'])} banderas ({altas} altas) · {len(hallazgos['descartados'])} valores descartados · "
        f"{len(hallazgos['no_revisado'])} sin revisar"
    )
    print(f"Salida: {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
