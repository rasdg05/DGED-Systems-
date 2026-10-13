"""rent_roll.csv, hallazgos.json y memo.md.

Todo lo que se escribe aquí sale de valores ya verificados o de los cruces.
El memo siempre trae "Lo que no se revisó": un memo sin esa sección se lee como
si hubiera cubierto todo.
"""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from .cruces import ALTA, MEDIA
from .esquemas import TIPOS
from .extraccion import Resultado
from .textos import Carpeta

FUERA_DE_ALCANCE = [
    "Opinión legal sobre validez, exigibilidad o firmas de los contratos.",
    "Superficies contra catastro o contra levantamiento físico: solo se cruzó escritura contra contrato.",
    "Gravámenes contra el Registro Público de la Propiedad: solo se transcribe lo que la escritura menciona.",
    "Anexos, convenios modificatorios y cartas laterales que no venían en la carpeta.",
    "Inspección física (ASTM E2018), ambiental fase I (ASTM E1527) y valuación.",
    "Capacidad eléctrica: de un oficio de suministro solo se transcribe lo que dice el papel (D-003).",
    "Renta contra mercado, conversión de moneda y recálculo de incrementos.",
]


def _rent_roll(resultados: list[Resultado], destino: Path) -> int:
    campos = [c.nombre for c in TIPOS["contrato_renta"].campos]
    encabezado = ["documento"]
    for campo in campos:
        encabezado += [campo, f"{campo}_pagina"]
    filas = 0
    with destino.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(encabezado)
        for contrato in (r for r in resultados if r.tipo == "contrato_renta"):
            fila = [contrato.documento]
            for campo in campos:
                valor = contrato.campos.get(campo)
                fila += [valor.valor, valor.pagina] if valor else ["", ""]
            escritor.writerow(fila)
            filas += 1
    return filas


def no_revisado(carpeta: Carpeta, resultados: list[Resultado]) -> list[dict]:
    salida = []
    for doc in carpeta.documentos:
        if doc.error:
            salida.append({"documento": doc.nombre, "motivo": doc.error})
        elif doc.requiere_ocr:
            salida.append({"documento": doc.nombre, "motivo": "requiere OCR: el PDF no trae capa de texto; no se leyó ni se infirió nada"})
        elif doc.paginas_sin_texto:
            paginas = ", ".join(str(p) for p in doc.paginas_sin_texto)
            salida.append({"documento": doc.nombre, "motivo": f"páginas sin texto (requieren OCR): {paginas}"})
    for resultado in resultados:
        if resultado.error:
            salida.append({"documento": resultado.documento, "motivo": f"no se extrajo: {resultado.error}"})
        elif resultado.tipo == "otro":
            salida.append({"documento": resultado.documento, "motivo": f"tipo sin esquema ({resultado.motivo_tipo or 'no clasificado'})"})
    for nombre in carpeta.no_soportados:
        salida.append({"documento": nombre, "motivo": "formato no soportado (solo PDF)"})
    return salida


def _documentos(carpeta: Carpeta, resultados: list[Resultado]) -> list[dict]:
    por_nombre = {r.documento: r for r in resultados}
    filas = []
    for doc in carpeta.documentos:
        r = por_nombre.get(doc.nombre)
        verificados = (len(r.campos) + sum(len(x) for x in r.renglones)) if r else 0
        filas.append({
            "documento": doc.nombre,
            "tipo": r.tipo if r else ("requiere_ocr" if doc.requiere_ocr else "no_leido"),
            "paginas": len(doc.paginas),
            "valores_verificados": verificados,
            "descartados": len(r.descartados) if r else 0,
        })
    return filas


def _evidencia_md(ev: dict) -> str:
    if ev.get("cita"):
        return f"{ev['documento']}, p. {ev['pagina']}: «{ev['cita']}»"
    return f"{ev['documento']}: {ev.get('nota', 'sin cita')}"


def _memo(hallazgos: dict) -> str:
    lineas = [
        "# Memo de banderas rojas — cuarto de datos",
        "",
        f"- Fecha de corte: {hallazgos['fecha_corte']} (horizonte de vencimientos: {hallazgos['meses']} meses)",
        f"- Modelo: {hallazgos['modelo']}" + (" (respuestas grabadas, sin llamar a la API)" if hallazgos["modo"] == "grabado" else ""),
        f"- Documentos en la carpeta: {len(hallazgos['documentos'])}",
        "",
        "> Apoyo a la decisión. Cada dato trae documento, página y cita literal; lo que no se pudo citar",
        "> no se reporta. No es opinión legal, inspección física, ambiental, valuación ni capacidad eléctrica.",
        "",
        f"## Banderas rojas ({len(hallazgos['banderas'])})",
        "",
    ]
    if not hallazgos["banderas"]:
        lineas += ["Ninguna con los cruces de este lector. Revise \"Lo que no se revisó\" antes de leerlo como limpio.", ""]
    for severidad in (ALTA, MEDIA):
        grupo = [b for b in hallazgos["banderas"] if b["severidad"] == severidad]
        if not grupo:
            continue
        lineas += [f"### Severidad {severidad} ({len(grupo)})", ""]
        for b in grupo:
            lineas.append(f"- **{b['bandera']}** — {b['detalle']}")
            lineas += [f"  - {_evidencia_md(ev)}" for ev in b["evidencia"]]
        lineas.append("")

    lineas += ["## Lo que dicen los oficios de suministro", ""]
    if hallazgos["transcripciones_suministro"]:
        lineas += [f"- {t['texto']}" for t in hallazgos["transcripciones_suministro"]]
        lineas += ["", "Transcripción del papel. DGED no afirma capacidad eléctrica ni megawatts (D-003)."]
    else:
        lineas.append("- No se leyó ningún oficio de suministro.")
    lineas.append("")

    lineas += ["## Documentos leídos", "", "| Documento | Tipo | Páginas | Valores verificados | Descartados |", "|---|---|---|---|---|"]
    lineas += [
        f"| {d['documento']} | {d['tipo']} | {d['paginas']} | {d['valores_verificados']} | {d['descartados']} |"
        for d in hallazgos["documentos"]
    ]
    lineas.append("")

    lineas += ["## Lo que no se revisó", ""]
    lineas += [f"- {n['documento']}: {n['motivo']}" for n in hallazgos["no_revisado"]]
    if hallazgos["descartados"]:
        lineas.append("- Valores propuestos por el modelo y descartados (no entran a ningún cruce):")
        lineas += [
            f"  - {d['documento']} · {d['campo']}: \"{d['valor']}\" — {d['motivo']}"
            for d in hallazgos["descartados"]
        ]
    lineas += [f"- {texto}" for texto in FUERA_DE_ALCANCE]
    lineas.append("")
    return "\n".join(lineas)


def escribir(
    destino: Path,
    carpeta: Carpeta,
    resultados: list[Resultado],
    banderas: list[dict],
    transcripciones: list[dict],
    fecha_corte: date,
    meses: int,
    modelo: str,
    modo: str,
) -> dict:
    destino.mkdir(parents=True, exist_ok=True)
    filas = _rent_roll(resultados, destino / "rent_roll.csv")
    hallazgos = {
        "fecha_corte": fecha_corte.isoformat(),
        "meses": meses,
        "modelo": modelo,
        "modo": modo,
        "banderas": banderas,
        # El rent roll con su evidencia: el CSV lleva la página; aquí va también la cita.
        "rent_roll": [
            {"documento": r.documento, "campos": {k: {"valor": v.valor, **v.evidencia()} for k, v in r.campos.items()}}
            for r in resultados if r.tipo == "contrato_renta"
        ],
        "transcripciones_suministro": transcripciones,
        "descartados": [d.como_dict() for r in resultados for d in r.descartados],
        "no_revisado": no_revisado(carpeta, resultados),
        "documentos": _documentos(carpeta, resultados),
    }
    (destino / "hallazgos.json").write_text(json.dumps(hallazgos, ensure_ascii=False, indent=2), encoding="utf-8")
    (destino / "memo.md").write_text(_memo(hallazgos), encoding="utf-8")
    hallazgos["rent_roll_filas"] = filas
    return hallazgos
