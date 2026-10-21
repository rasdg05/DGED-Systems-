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


def cifras_no_permitidas(texto: str, permitidas: set[str] | frozenset[str] = frozenset()) -> list[str]:
    return sorted(numeros(texto) - set(permitidas))


def trae_dinero(texto: str) -> bool:
    return bool(DINERO.search(texto or ""))
