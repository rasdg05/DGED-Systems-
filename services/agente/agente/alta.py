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


def registrar(espacio: Espacio, datos: dict) -> dict:
    faltan = [c for c in OBLIGATORIOS if not str(datos.get(c, "")).strip()]
    if faltan:
        raise AltaIncompleta(f"faltan: {', '.join(faltan)}")
    alta = {c: datos[c] for c in OBLIGATORIOS + OPCIONALES if c in datos}
    espacio.escribir_json("alta.json", alta)
    config = espacio.config()
    config.setdefault("encendido", "sombra")  # nace sin enviar nada
    espacio.escribir_json("config.json", config)
    return alta
