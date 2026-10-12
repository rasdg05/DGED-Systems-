"""Invariantes de MEMORY/CONSTITUCION.md convertidas en tests.

Regla heredada de fq-bot: un hallazgo sin test que lo haga cumplir es una
nota, no un arreglo. Cada test cita la fila de la constitución que cuida.
"""
from __future__ import annotations

import ast
import json
import re
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
STATIC = RAIZ / "services" / "api" / "static"
VENDIDOS = {"maplibre-gl.js", "maplibre-gl.css"}


def _texto_de_cara_al_usuario():
    for archivo in sorted(STATIC.iterdir()):
        if archivo.is_file() and archivo.name not in VENDIDOS:
            yield archivo, archivo.read_text(encoding="utf-8")
    ontologia = RAIZ / "ontology" / "atlas.ontology.json"
    yield ontologia, ontologia.read_text(encoding="utf-8")


# IV — D-003: "MW disponibles en el predio" queda prohibida. Negarlo
# ("no afirma megawatts") está permitido; afirmarlo con un número, no.
AFIRMACION_MW = re.compile(
    r"\d[\d.,]*\s*(MW|megawatts?)\b|MW\s+disponibles|capacidad\s+disponible",
    re.IGNORECASE,
)


def test_no_se_afirman_megawatts():
    hallazgos = [
        f"{archivo.relative_to(RAIZ)}: {m.group(0)!r}"
        for archivo, texto in _texto_de_cara_al_usuario()
        for m in AFIRMACION_MW.finditer(texto)
    ]
    assert not hallazgos, f"afirmaciones de capacidad eléctrica: {hallazgos}"


# V — SubestacionAprox existe y no trae ninguna propiedad de capacidad.
def test_subestacion_sin_capacidad():
    ontologia = json.loads((RAIZ / "ontology" / "atlas.ontology.json").read_text(encoding="utf-8"))
    tipos = {t["apiName"]: t for t in ontologia["objectTypes"]}
    assert "SubestacionAprox" in tipos
    props = [p.lower() for p in tipos["SubestacionAprox"]["properties"]]
    prohibidas = [p for p in props if any(s in p for s in ("mw", "capacity", "capacidad", "headroom", "holgura", "disponible", "available"))]
    assert not prohibidas, f"SubestacionAprox no puede afirmar capacidad: {prohibidas}"


# VI — el HTML espera MapLibre 5.6.1 en esas rutas; el archivo no viene en el
# parche original y se baja aparte, así que una versión distinta pasaría callada.
def test_maplibre_es_5_6_1():
    js = STATIC / "maplibre-gl.js"
    css = STATIC / "maplibre-gl.css"
    assert js.exists() and css.exists(), "faltan los archivos vendidos de MapLibre"
    encabezado = js.read_text(encoding="utf-8", errors="replace")[:400]
    assert "v5.6.1" in encabezado, f"MapLibre no es 5.6.1: {encabezado[:200]!r}"


# VII — pytest solo recolecta la última definición con un nombre repetido; la
# primera desaparece sin fallar (lección de Gestor-Morelos, 2026-10-05).
def _tapados(cuerpo):
    nombres = Counter(
        n.name for n in cuerpo
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")
    )
    return [n for n, veces in nombres.items() if veces > 1]


def test_ningun_test_tapa_a_otro():
    tapados = []
    for archivo in sorted(RAIZ.rglob("test_*.py")):
        if ".git" in archivo.parts:
            continue
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        tapados += [f"{archivo.name}::{n}" for n in _tapados(arbol.body)]
        for clase in (n for n in arbol.body if isinstance(n, ast.ClassDef)):
            tapados += [f"{archivo.name}::{clase.name}.{n}" for n in _tapados(clase.body)]
    assert not tapados, f"tests que nunca corren (nombre repetido): {tapados}"


# VIII — las claves viven en .env, nunca en el ejemplo versionado.
def test_env_example_sin_claves():
    lineas = (RAIZ / ".env.example").read_text(encoding="utf-8").splitlines()
    con_valor = [
        l for l in lineas
        if l.strip() and not l.lstrip().startswith("#") and "=" in l and l.split("=", 1)[1].strip()
    ]
    assert not con_valor, f".env.example trae valores: {[l.split('=')[0] for l in con_valor]}"
