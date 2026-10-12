"""El Oráculo: preguntas en lenguaje natural contestadas SOLO con el propio Atlas.

El modelo no sabe nada de los sitios: todo lo que dice sale de herramientas que
llaman a las mismas funciones que la API (`POST /api/sites/{id}/score` incluida).
Lo que el modelo escribe pasa por tres candados antes de salir:

1. **Toda cifra viene de un resultado de herramienta de esta conversación.**
   Cada número de la respuesta se busca entre los números de los resultados; el
   que no aparece se reemplaza por un aviso y se reporta en `unverified`.
2. **Nunca afirma megawatts ni capacidad eléctrica** (D-003). La frase que lo
   haga se quita entera y se dice por qué.
3. **Lista sus fuentes y lo que no respondió**: las URLs que devolvieron las
   herramientas y los factores marcados `missing`, escritos por el sistema, no
   por el modelo.

Dormido por defecto: sin `ANTHROPIC_API_KEY` el endpoint responde 503.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable

DEFAULT_MODEL = "claude-opus-5-5"
MAX_STEPS = 8
MAX_TOKENS = 16000
FALLBACK_BETA = "server-side-fallback-2026-07-01"

AVISO_CIFRA = "[cifra sin verificar]"
AVISO_MW = (
    "[Se retiró una afirmación de capacidad eléctrica: Atlas no afirma megawatts "
    "ni capacidad eléctrica en el predio.]"
)
AVISO_TOPE = (
    "El Oráculo llegó a su tope de pasos sin cerrar una respuesta. "
    "Lo consultado está en los pasos de abajo."
)
AVISO_RECHAZO = "El modelo declinó contestar esta pregunta. No se inventa una respuesta en su lugar."

# Misma familia que tests/test_invariantes.py::AFIRMACION_MW, más las unidades
# vecinas: una cifra con unidad eléctrica o una "capacidad disponible" es afirmar.
AFIRMACION_MW = re.compile(
    r"\d[\d.,]*\s*(MW|MVA|kVA|kW|megawatts?|megavatios?)\b"
    r"|MW\s+disponibles"
    r"|capacidad\s+(el[eé]ctrica\s+)?disponible"
    r"|capacidad\s+el[eé]ctrica\s+(de|es|del\s+predio)\b",
    re.IGNORECASE,
)

# Un número suelto: no pegado a letras ("D2", "c463" no son cifras), con
# separadores de miles o decimales en cualquiera de las dos convenciones.
NUMERO = re.compile(r"(?<!\w)\d+(?:[.,]\d+)*")

SYSTEM_PROMPT = """Eres el Oráculo de Atlas, de DGED Systems: contestas preguntas sobre sitios industriales candidatos en el norte y el Bajío de México.

Todo lo que sabes de los sitios sale de las herramientas de esta conversación, que llaman al propio Atlas (INEGI, SMN/CONAGUA). Antes de afirmar algo de un sitio, consúltalo: lista los sitios, califícalo o abre su ficha. Si una herramienta no trae el dato, dilo así.

Reglas de la respuesta:
- Copia cada cifra exactamente como aparece en un resultado de herramienta (mismo número, mismos decimales). No calcules promedios, diferencias, sumas ni porcentajes nuevos: para comparar, di cuál es mayor o menor. El sistema verifica cada cifra contra los resultados y retira las que no encuentra.
- Un factor ausente (missing) no entra al número: dilo ausente y no lo estimes. Un score que no es publicable es un borrador.
- Atlas no mide capacidad eléctrica: el objeto SubestacionAprox viaja vacío. Si preguntan por megawatts, carga o capacidad de la red, contesta que Atlas no lo afirma y que hace falta un estudio de interconexión, sin cifra.
- Atlas es apoyo a la decisión: no sustituye estudio de interconexión, concesión de agua, MIA ni dictamen de seguridad.
- Escribe en español, breve y directo. Para listas usa guiones, no números. Las fuentes y los factores ausentes los agrega el sistema al final; no hace falta copiarlos."""


def _tool(name, description, properties, required):
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


TOOLS = [
    _tool(
        "listar_sitios",
        "Lista los sitios candidatos de Atlas con su corredor y, si ya se calificaron en esta sesión del servidor, su score. "
        "Úsala primero para conocer los id de sitio.",
        {"corredor": {"type": "string", "enum": ["todos", "norte", "bajio"], "description": "Corredor a listar."}},
        ["corredor"],
    ),
    _tool(
        "calificar_sitio",
        "Califica un sitio en vivo con la misma función que POST /api/sites/{id}/score: consulta INEGI y el monitor de sequía, "
        "devuelve composite, riesgo, cobertura, si es publicable, cada factor con su dato crudo (raw) y las URLs de evidencia. "
        "Tarda unos segundos: consulta fuentes públicas.",
        {
            "site_id": {"type": "string", "description": "id del sitio, de listar_sitios."},
            "anio_seco": {"type": "boolean", "description": "Escenario de año seco: la sequía no baja de D2."},
        },
        ["site_id", "anio_seco"],
    ),
    _tool(
        "ficha_sitio",
        "Ficha de un sitio: datos base, último score calificado, grafo de objetos de la ontología y URLs de evidencia. "
        "No consulta fuentes; si el sitio no se ha calificado, no trae score.",
        {"site_id": {"type": "string", "description": "id del sitio."}},
        ["site_id"],
    ),
    _tool(
        "ver_ontologia",
        "La ontología de Atlas: tipos de objeto, ligas y acciones, con sus notas.",
        {},
        [],
    ),
    _tool(
        "estado_fuentes",
        "Estado de las fuentes públicas en esta sesión del servidor: cuáles responden, desde cuándo y con qué URL.",
        {},
        [],
    ),
    _tool(
        "comparar_sitios",
        "Compara el último score calificado de varios sitios: composite, riesgo, cobertura, publicable y factores ausentes. "
        "Un sitio sin calificar sale marcado; califícalo antes si hace falta.",
        {"site_ids": {"type": "array", "items": {"type": "string"}, "description": "Dos o más id de sitio."}},
        ["site_ids"],
    ),
]


@dataclass
class AtlasApi:
    """Las funciones del propio Atlas que el Oráculo puede llamar."""

    list_sites: Callable[[str | None], dict]
    score_site: Callable[[str, bool], dict]
    site_detail: Callable[[str], dict]
    ontology: Callable[[], dict]
    sources: Callable[[], dict]


class ToolError(Exception):
    pass


def _compare(api: AtlasApi, site_ids):
    if not isinstance(site_ids, list) or len(site_ids) < 2:
        raise ToolError("comparar_sitios pide dos o más id de sitio.")
    rows = []
    for site_id in site_ids:
        detail = api.site_detail(site_id)
        score = detail.get("score")
        if not score:
            rows.append({"id": site_id, "name": detail.get("name"), "calificado": False})
            continue
        rows.append({
            "id": site_id,
            "name": detail.get("name"),
            "calificado": True,
            "composite": score.get("composite"),
            "risk": score.get("risk"),
            "coverage": score.get("coverage"),
            "publishable": score.get("publishable"),
            "modelVersion": score.get("modelVersion"),
            "factores": [
                {"key": f.get("key"), "label": f.get("label"), "score": f.get("score"), "missing": f.get("missing")}
                for f in score.get("factors") or []
            ],
            "evidence": detail.get("evidence"),
        })
    return {"sitios": rows}


def execute(api: AtlasApi, name: str, tool_input: dict) -> Any:
    tool_input = tool_input or {}
    if name == "listar_sitios":
        corridor = tool_input.get("corredor")
        listed = api.list_sites(None if corridor in (None, "", "todos") else corridor)
        rows = listed.get("sites") or []
        # El total va escrito: si el modelo lo dice, la cifra tiene de dónde salir.
        return {"total": len(rows), "sites": rows}
    if name == "calificar_sitio":
        return api.score_site(str(tool_input.get("site_id", "")), bool(tool_input.get("anio_seco", False)))
    if name == "ficha_sitio":
        return api.site_detail(str(tool_input.get("site_id", "")))
    if name == "ver_ontologia":
        return api.ontology()
    if name == "estado_fuentes":
        return api.sources()
    if name == "comparar_sitios":
        return _compare(api, tool_input.get("site_ids"))
    raise ToolError(f"Herramienta desconocida: {name}")


def summarize(name: str, result: Any) -> str:
    if not isinstance(result, dict):
        return "sin resultado"
    if name == "listar_sitios":
        return f"{len(result.get('sites') or [])} sitios"
    if name in ("calificar_sitio", "ficha_sitio"):
        score = result.get("score")
        if not score:
            return f"{result.get('name') or result.get('id')}: sin calificar"
        missing = [f.get("label") for f in score.get("factors") or [] if f.get("missing")]
        estado = "publicable" if score.get("publishable") else "borrador"
        texto = f"{result.get('name')}: {score.get('composite')} ({estado})"
        return texto + (f"; ausentes: {', '.join(missing)}" if missing else "")
    if name == "ver_ontologia":
        return f"{len(result.get('objectTypes') or [])} tipos de objeto"
    if name == "estado_fuentes":
        ok = [key for key, value in result.items() if isinstance(value, dict) and value.get("ok") is True]
        return f"{len(ok)} de {len(result)} fuentes responden"
    if name == "comparar_sitios":
        rows = result.get("sitios") or []
        return f"{sum(1 for r in rows if r.get('calificado'))} de {len(rows)} sitios calificados"
    return "ok"


# --- candados -----------------------------------------------------------------

def _interpretations(token: str) -> set[float]:
    """Lecturas posibles de una cifra escrita: '1,500' (miles) o '73,6' (decimal)."""
    values = set()
    for decimal, thousands in ((".", ","), (",", ".")):
        text = token.replace(thousands, "")
        if text.count(decimal) <= 1:
            try:
                values.add(round(float(text.replace(decimal, ".")), 9))
            except ValueError:
                pass
    try:
        values.add(round(float(re.sub(r"[.,]", "", token)), 9))
    except ValueError:
        pass
    return values


def numbers_in(text: str) -> set[float]:
    found = set()
    for match in NUMERO.finditer(text):
        found |= _interpretations(match.group(0))
    return found


def verify_numbers(answer: str, evidence_text: str) -> tuple[str, list[str]]:
    """Reemplaza toda cifra de `answer` que no esté en `evidence_text`."""
    known = numbers_in(evidence_text)
    unverified = []

    def check(match):
        token = match.group(0)
        if _interpretations(token) & known:
            return token
        unverified.append(token)
        return AVISO_CIFRA

    return NUMERO.sub(check, answer), unverified


def strip_capacity_claims(answer: str) -> tuple[str, bool]:
    """Quita la oración que afirme megawatts o capacidad eléctrica."""
    if not AFIRMACION_MW.search(answer):
        return answer, False
    sentences = re.split(r"(?<=[.!?])(?=\s)|(?<=\n)", answer)
    kept = [s for s in sentences if not AFIRMACION_MW.search(s)]
    return ("".join(kept).strip() + "\n\n" + AVISO_MW).strip(), True


def _walk(value):
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def collect_sources(results: list[Any]) -> list[str]:
    urls = []
    for result in results:
        for item in _walk(result):
            if isinstance(item, str) and re.match(r"https?://", item) and item not in urls:
                urls.append(item)
    return urls


def collect_missing(results: list[tuple[str, Any]]) -> list[str]:
    """Factores marcados `missing` en cualquier score devuelto, por sitio."""
    missing = []
    for _name, result in results:
        for item in _walk(result):
            if not isinstance(item, dict):
                continue
            factors = (item.get("score") or {}).get("factors") if isinstance(item.get("score"), dict) else None
            if factors is None and "factores" in item:
                factors = item.get("factores")
            if not factors:
                continue
            site = item.get("name") or item.get("id") or "sitio"
            for factor in factors:
                if isinstance(factor, dict) and factor.get("missing"):
                    line = f"{site}: {factor.get('label') or factor.get('key')}"
                    if line not in missing:
                        missing.append(line)
    return missing


def _footer(sources: list[str], missing: list[str], scored: bool) -> str:
    lines = ["", "Fuentes:"]
    lines += [f"- {url}" for url in sources] or ["- Ninguna herramienta de esta conversación devolvió una URL de fuente."]
    lines.append("")
    if missing:
        lines.append("Factores que no respondieron (no entran al número):")
        lines += [f"- {line}" for line in missing]
    elif scored:
        lines.append("Factores que no respondieron: ninguno en los sitios consultados.")
    else:
        lines.append("Factores que no respondieron: no se consultó el score de ningún sitio en esta conversación.")
    return "\n".join(lines)


# --- el ciclo -------------------------------------------------------------------

def model_name() -> str:
    return os.environ.get("ATLAS_ORACLE_MODEL", "").strip() or DEFAULT_MODEL


def is_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def make_client():
    import anthropic

    return anthropic.Anthropic()


def _text_of(content) -> str:
    return "".join(getattr(block, "text", "") for block in content if getattr(block, "type", None) == "text").strip()


def ask(question: str, api: AtlasApi, client, model: str | None = None, max_steps: int = MAX_STEPS) -> dict:
    """Corre el ciclo de herramientas y devuelve la respuesta ya verificada."""
    model = model or model_name()
    messages: list[dict] = [{"role": "user", "content": question}]
    steps: list[dict] = []
    results: list[tuple[str, Any]] = []
    evidence_chunks: list[str] = []
    answer = ""
    stop = "end_turn"

    while True:
        out_of_steps = len(steps) >= max_steps
        response = client.beta.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            # Agotado el tope, el modelo solo puede contestar con lo que ya tiene.
            tool_choice={"type": "none"} if out_of_steps else {"type": "auto"},
            output_config={"effort": "medium"},
            betas=[FALLBACK_BETA],
            fallbacks="default",
            messages=messages,
        )
        if response.stop_reason == "refusal":
            answer, stop = AVISO_RECHAZO, "refusal"
            break
        tool_uses = [block for block in response.content if getattr(block, "type", None) == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_uses:
            answer = _text_of(response.content)
            stop = "tope" if out_of_steps else (response.stop_reason or "end_turn")
            if not answer:
                answer = AVISO_TOPE if out_of_steps else "El modelo no devolvió texto."
            break
        if out_of_steps:
            answer, stop = AVISO_TOPE, "tope"
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in tool_uses:
            if len(steps) >= max_steps:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Tope de pasos alcanzado: contesta con lo que ya consultaste.",
                    "is_error": True,
                })
                continue
            try:
                result = execute(api, block.name, dict(block.input or {}))
                text = json.dumps(result, ensure_ascii=False, default=str)
                results.append((block.name, result))
                evidence_chunks.append(text)
                steps.append({"tool": block.name, "input": dict(block.input or {}), "summary": summarize(block.name, result)})
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": text})
            except Exception as error:  # HTTPException 404/503 del propio Atlas, ToolError, fuente caída
                detail = getattr(error, "detail", None) or str(error) or type(error).__name__
                steps.append({"tool": block.name, "input": dict(block.input or {}), "summary": f"error: {detail}"})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"Error: {detail}",
                    "is_error": True,
                })
        messages.append({"role": "user", "content": tool_results})

    answer, removed_capacity = strip_capacity_claims(answer)
    answer, unverified = verify_numbers(answer, "\n".join(evidence_chunks))
    sources = collect_sources([result for _name, result in results])
    missing = collect_missing(results)
    scored = any(
        isinstance(item, dict) and isinstance(item.get("score"), dict)
        for _name, result in results
        for item in _walk(result)
    ) or any(name == "comparar_sitios" for name, _ in results)
    return {
        "answer": answer + "\n" + _footer(sources, missing, scored),
        "steps": steps,
        "sources": sources,
        "unverified": unverified,
        "missing": missing,
        "capacityClaimRemoved": removed_capacity,
        "model": model,
        "stop": stop,
    }
