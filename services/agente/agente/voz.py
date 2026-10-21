"""La voz del negocio, revisada antes de salir. Tomado de Gestor Morelos (`services/voz.py`).

En Gestor los rasgos salían de las 34 respuestas de una sola casa. Aquí se
separan en dos: lo que ningún negocio escribe desde su celular (frases de
plantilla de chatbot, formato de chat de IA, párrafos de folleto) y lo que
depende de cada negocio, que se lee de SU voz aprobada: si ninguna de sus
frases trae emoji o abre con ¡ o ¿, que el borrador lo traiga es un rasgo
ajeno; si el perfil dice `trato: usted`, tutear también.

`hallazgos` no decide: dice qué encontró. Quien llama manda el borrador a la
persona en vez de al cliente.
"""
from __future__ import annotations

import re
import unicodedata

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿]")

TUTEO = re.compile(
    r"\b(?:tu|tus|te|ti|contigo|tienes|puedes|quieres|necesitas|deseas|"
    r"escribeme|mandame|enviame|avisame|dime|cuentame|dejame|platicame)\b")

PLANTILLA = re.compile(
    r"entiendo (?:tu|su) (?:situacion|preocupacion|frustracion|molestia)|"
    r"desafortunadamente|lamentablemente|"
    r"no dude(?:s)? en|"
    r"(?:estoy|estamos) aqui para (?:ayudar|apoyar|servir)|"
    r"\bcomo (?:asistente|ia|inteligencia artificial|modelo de lenguaje)\b|"
    r"\bsoy (?:un|una) (?:asistente virtual|bot|ia|inteligencia)|"
    r"no tengo (?:acceso|la capacidad)|"
    r"espero que (?:esto|esta informacion|le sirva|te sirva)|"
    r"(?:cabe|es importante) (?:mencionar|destacar|senalar|tener en cuenta)|"
    r"(?:excelente|buena|gran) pregunta|"
    r"hay algo mas en (?:lo|que)|(?:le|te) puedo ayudar con algo mas|"
    r"a continuacion|en resumen")

MARKDOWN = re.compile(r"\*\*|^#{1,3} |^\s*[-*•] \S", re.MULTILINE)
MAX_PALABRAS = 70


def _normalizar(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")
    return " ".join(sin.lower().split())


def rasgos_del_negocio(perfil: dict | None) -> dict:
    frases = [v.get("frase", "") for v in (perfil or {}).get("voz", []) or []]
    return {
        "emoji": any(EMOJI.search(f) for f in frases),
        "apertura": any(("¡" in f or "¿" in f) for f in frases),
        "trato": (perfil or {}).get("trato"),
        "max_palabras": max([MAX_PALABRAS] + [len(f.split()) + 10 for f in frases]),
    }


def hallazgos(texto: str, perfil: dict | None = None) -> list[str]:
    crudo = texto or ""
    if not crudo.strip():
        return []
    rasgos = rasgos_del_negocio(perfil)
    t = _normalizar(crudo)
    salida = []
    if not rasgos["emoji"] and EMOJI.search(crudo):
        salida.append("trae emoji y el negocio no los usa")
    if not rasgos["apertura"] and ("¡" in crudo or "¿" in crudo):
        salida.append("abre con ¡ o ¿ y el negocio no lo hace")
    if rasgos["trato"] == "usted" and (m := TUTEO.search(t)):
        salida.append(f"tutea («{m.group(0)}») y el negocio habla de usted")
    for renglon in crudo.splitlines():
        if (m := PLANTILLA.search(_normalizar(renglon))):
            salida.append(f"frase de chatbot («{m.group(0)}»)")
            break
    if MARKDOWN.search(crudo):
        salida.append("formato de chat de IA (asteriscos, viñetas o títulos)")
    palabras = len(crudo.split())
    if palabras > rasgos["max_palabras"]:
        salida.append(f"{palabras} palabras (el negocio no pasa de {rasgos['max_palabras']})")
    return salida
