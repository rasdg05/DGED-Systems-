"""El candado de la cifra (invariante 1), heredado de `GUARDRAILS` de Gestor Morelos.

En Gestor la regla vive en el prompt y en `test_blindaje.py`. Aquí se revisa
el texto que sale, por código, porque pedirle al modelo que no ponga números
no es lo mismo que impedirlo:

- Texto redactado por el modelo: no lleva NINGÚN número. Ni monto, ni hora, ni
  fecha con número. Lo que necesita número lo escribe el cotizador.
- Respuesta guardada (frase aprobada del negocio, sin modelo): puede decir "a
  las 3", pero no un monto. Un precio de hace meses en una frase guardada es
  una cifra que no salió del cotizador.
- Cotización: solo las cifras que el cotizador puso en su propio texto.
"""
from __future__ import annotations

import re

from .perfil import numeros

DINERO = re.compile(
    r"\$\s*\d|\d[\d,.]*\s*(?:pesos|mxn|mn|usd|d[oó]lares|%|por ciento|mil\b|k\b)|\d{1,3}(?:,\d{3})+",
    re.IGNORECASE)


# **La cifra con letra también es cifra** (el banco lo cazó, 2026-10-27: el
# adversario escribió *"se la dejo en seis mil"* y pasaba). "Un/una" no cuentan:
# son artículos. El texto del modelo no lleva cantidades de ninguna forma.
NUMERO_ESCRITO = re.compile(
    r"\b(?:dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|"
    r"dieci\w+|veinte|veinti\w+|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|"
    r"cien|ciento|doscient\w+|trescient\w+|cuatrocient\w+|quinient\w+|seiscient\w+|setecient\w+|"
    r"ochocient\w+|novecient\w+|mil(?!\s+gracias)|millon(?:es)?|medio millon)\b", re.IGNORECASE)


def cifras_no_permitidas(texto: str, permitidas: set[str] | frozenset[str] = frozenset()) -> list[str]:
    escritas = [m.group(0).lower() for m in NUMERO_ESCRITO.finditer(texto or "")]
    return sorted(numeros(texto) - set(permitidas)) + escritas


def trae_dinero(texto: str) -> bool:
    return bool(DINERO.search(texto or ""))


#: Nunca dice que es una persona (Gestor: `EN_EL_MOLDE["soy_asistente"]`, regla 6 de `GUARDRAILS`).
SOY_PERSONA = re.compile(r"\b(?:soy|somos) (?:una? )?(?:persona|humano|humana)\b|\bno soy (?:un )?(?:bot|robot)\b",
                         re.IGNORECASE)


def dice_ser_persona(texto: str) -> bool:
    return bool(SOY_PERSONA.search(texto or ""))
