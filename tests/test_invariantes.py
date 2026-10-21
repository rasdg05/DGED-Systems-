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
    for ejemplo in sorted(RAIZ.glob("**/.env.example")):
        if ".git" in ejemplo.parts:
            continue
        lineas = ejemplo.read_text(encoding="utf-8").splitlines()
        con_valor = [
            linea for linea in lineas
            if linea.strip() and not linea.lstrip().startswith("#") and "=" in linea and linea.split("=", 1)[1].strip()
        ]
        assert not con_valor, f"{ejemplo.relative_to(RAIZ)} trae valores: {[linea.split('=')[0] for linea in con_valor]}"


# IX — toda variable que declara .env.example llega al contenedor de la API.
# SAKBE_TOKEN estuvo documentada y nunca llegaba: con Docker la ruta no entraba
# al número aunque la clave estuviera en .env.
def test_compose_pasa_cada_variable_del_env_example():
    compose = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
    variables = [
        linea.split("=", 1)[0].strip()
        for linea in (RAIZ / ".env.example").read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.lstrip().startswith("#") and "=" in linea
    ]
    faltan = [v for v in variables if f"${{{v}:-" not in compose]
    assert not faltan, f"docker-compose.yml no pasa: {faltan}"


# X — la base no se publica fuera de la máquina.
def test_postgres_no_se_publica_a_toda_la_red():
    compose = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
    assert '"5432:5432"' not in compose


# XVIII — ninguna marca de conflicto de git llega a un commit. Pasó el
# 2026-10-12 con MEMORY/ESTADO.md al integrar dos agentes: la memoria decía dos
# estados a la vez y ningún test lo veía.
def test_sin_marcas_de_conflicto():
    marca = re.compile(r"^(<{7}|>{7}) ", re.MULTILINE)
    sufijos = {".md", ".py", ".js", ".mjs", ".html", ".css", ".json", ".yml", ".yaml", ".sql", ".toml", ".txt"}
    hallados = []
    for archivo in RAIZ.rglob("*"):
        if ".git" in archivo.parts or archivo.suffix not in sufijos or archivo.name in VENDIDOS:
            continue
        if marca.search(archivo.read_text(encoding="utf-8", errors="replace")):
            hallados.append(str(archivo.relative_to(RAIZ)))
    assert not hallados, f"marcas de conflicto en: {hallados}"


# XXIX — ningún artefacto generado vive en git. `.coverage` estuvo versionado
# del 2026-10-12 al 13 (un `git add -A` tras medir cobertura) y chocó al
# integrar el satélite.
def test_sin_artefactos_generados_en_git():
    import subprocess

    rastreados = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    prohibidos = re.compile(r"(^|/)(\.coverage(\..*)?|\.pytest_cache/.*|\.ruff_cache/.*|__pycache__/.*|.*\.pyc)$")
    hallados = [r for r in rastreados if prohibidos.search(r)]
    assert not hallados, f"artefactos generados en git: {hallados}"


# XXX — sin GitHub Actions (D-015), verificar.sh corre lo mismo que el CI.
# Si alguien agrega un paso al CI y no a verificar.sh, la revisión local
# dejaría pasar lo que el CI habría frenado.
def test_verificar_corre_lo_mismo_que_el_ci():
    ci = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    local = (RAIZ / "herramientas" / "verificar.sh").read_text(encoding="utf-8")
    for paso in ("ruff check .", "--cov-fail-under", "node --test packages/score/score.test.mjs",
                 "import atlas.score, atlas.main, atlas.access, atlas.oracle",
                 "import agente.app, agente.mcp, agente.simbiosis", "docker compose config -q"):
        assert paso in ci and paso in local, f"paso que no está en los dos: {paso}"
    gancho = (RAIZ / ".githooks" / "pre-push").read_text(encoding="utf-8")
    assert "herramientas/verificar.sh" in gancho


# XXXI — la nube asigna el puerto. Railway pasa $PORT y revisa /api/health:
# un puerto fijo arranca "sano" en local y en la nube nunca recibe tráfico.
def test_contenedor_escucha_en_el_puerto_que_asigna_la_nube():
    docker = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
    assert "${PORT:-8080}" in docker
    railway = json.loads((RAIZ / "railway.json").read_text(encoding="utf-8"))
    assert railway["deploy"]["healthcheckPath"] == "/api/health"
