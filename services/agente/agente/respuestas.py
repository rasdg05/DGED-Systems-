"""Respuestas guardadas: si la pregunta ya tiene frase aprobada, sale sin llamar al modelo.

Es la palanca de costo más barata (`docs/15-agente-a-la-medida.md`) y la más
segura: la frase es del negocio, aprobada por el dueño. Se compara por palabras
con contenido, no por texto exacto; una frase con un monto no se usa aquí
(`guardia.trae_dinero`): el monto lo pone el cotizador.
"""
from __future__ import annotations

import re
import unicodedata

from .guardia import trae_dinero

UMBRAL = 0.6
VACIAS = {
    "a", "al", "algo", "con", "de", "del", "el", "en", "es", "esta", "hay", "la", "las", "le", "lo",
    "los", "me", "mi", "para", "por", "que", "se", "si", "su", "un", "una", "y", "o", "hola",
    "buenas", "buenos", "dias", "tardes", "noches", "favor", "gracias", "oiga", "disculpe",
}


def palabras(texto: str) -> set[str]:
    sin = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return {p for p in re.findall(r"[a-zñ]+", sin) if p not in VACIAS and len(p) > 2}


def parecido(a: str, b: str) -> float:
    pa, pb = palabras(a), palabras(b)
    if not pa or not pb:
        return 0.0
    return len(pa & pb) / len(pa | pb)


def buscar(perfil: dict | None, pregunta: str) -> dict | None:
    mejor, puntaje = None, 0.0
    for faq in (perfil or {}).get("faq", []) or []:
        if trae_dinero(faq.get("respuesta", "")):
            continue
        p = parecido(pregunta, faq.get("pregunta", ""))
        if p > puntaje:
            mejor, puntaje = faq, p
    return mejor if puntaje >= UMBRAL else None
