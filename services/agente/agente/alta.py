"""El alta (≈5 min): lo que el dueño dice de su negocio antes de conectar nada.

Lo escrito aquí también es origen: un dato del perfil puede citar el alta
(`perfil.py`). El teléfono de quien aprueba vive solo en el espacio.
"""
from __future__ import annotations

from .espacio import Espacio

OBLIGATORIOS = ("giro", "nombre_comercial", "que_vende", "como_cobra", "horario", "aprobador", "aprobador_telefono")
OPCIONALES = ("asesores", "propiedades", "notas")


class AltaIncompleta(ValueError):
    pass


NOMBRES = {"giro": "giro", "nombre_comercial": "nombre comercial", "que_vende": "qué ofrece",
           "como_cobra": "cómo cobra", "horario": "horario", "aprobador": "quién aprueba",
           "aprobador_telefono": "teléfono de quien aprueba"}


def _lista(valor) -> list[str]:
    if isinstance(valor, list):
        return [str(v).strip() for v in valor if str(v).strip()]
    return [p.strip() for p in str(valor or "").replace("\n", ",").split(",") if p.strip()]


def faltan(alta: dict | None) -> list[str]:
    return [NOMBRES[c] for c in OBLIGATORIOS if not str((alta or {}).get(c, "")).strip()]


def registrar(espacio: Espacio, datos: dict, parcial: bool = False) -> dict:
    """Guarda el alta. `parcial=True` (la pantalla) guarda lo que haya: lo que
    solo sabe el negocio (cómo cobra, quién aprueba) puede llegar después. Lo
    que exige quien aprueba sigue exigiéndose al aprobar (`perfil.aprobar`)."""
    limpio = {c: datos[c] for c in OBLIGATORIOS + OPCIONALES if c in datos}
    for c in ("asesores", "propiedades"):
        if c in limpio:
            limpio[c] = _lista(limpio[c])
    limpio = {c: v for c, v in limpio.items() if v not in ("", [], None)}
    if not parcial and (pendientes := faltan(limpio)):
        raise AltaIncompleta(f"faltan: {', '.join(pendientes)}")
    if parcial and not str(limpio.get("nombre_comercial", "")).strip():
        raise AltaIncompleta("falta: nombre comercial")
    espacio.escribir_json("alta.json", limpio)
    config = espacio.config()
    config.setdefault("encendido", "sombra")  # nace sin enviar nada
    espacio.escribir_json("config.json", config)
    return limpio
