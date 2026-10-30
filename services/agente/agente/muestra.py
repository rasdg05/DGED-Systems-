"""La demo de un giro: un espacio sembrado con una muestra FICTICIA, para enseñar la app.

Un servicio de Railway de demostración (uno por prospecto, en su propia rama)
declara `AGENTE_MUESTRA=<carpeta de muestra/>` y `AGENTE_ESPACIO_MUESTRA=<id>`.
Al arrancar, si el espacio no existe, se siembra con el alta, el historial y el
perfil de esa muestra (validado: lo que no prueba su origen cae igual que con
un negocio real), aprobado a nombre de quien aprueba en el alta, y el agente
corre **en sombra** sobre cada plática que espera respuesta: la Cola enseña lo
que haría, y nada sale (nace `encendido: sombra`, sin canal).

Si el espacio ya existe no se toca: lo que el prospecto haya movido en la demo
(o su WhatsApp vinculado) no se pisa en el siguiente despliegue.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from . import agente, alta, historial, perfil
from .espacio import Espacio, EspacioInvalido

RAIZ_MUESTRAS = Path(__file__).resolve().parent.parent / "muestra"
VARIABLE = "AGENTE_MUESTRA"
VARIABLE_ESPACIO = "AGENTE_ESPACIO_MUESTRA"
log = logging.getLogger(__name__)


def carpeta(nombre: str) -> Path:
    destino = (RAIZ_MUESTRAS / nombre).resolve()
    if destino.parent != RAIZ_MUESTRAS.resolve() or not (destino / "alta.json").exists():
        raise ValueError(f"no hay muestra {nombre!r}")
    return destino


def _leer(origen: Path, nombre: str):
    return json.loads((origen / nombre).read_text(encoding="utf-8"))


def sembrar(espacio: Espacio, nombre: str) -> dict:
    """Siembra la muestra en un espacio NUEVO. Devuelve qué entró y qué cayó."""
    if espacio.carpeta.exists():
        return {"sembrado": False, "motivo": "el espacio ya existe"}
    origen = carpeta(nombre)
    datos_alta = _leer(origen, "alta.json")
    alta.registrar(espacio, datos_alta)
    mensajes = historial.de_webhook(_leer(origen, "historial_webhook.json"))
    historial.guardar(espacio, mensajes)
    n, descartados = perfil.proponer(espacio, _leer(origen, "perfil_grabado.json"), autor="muestra", nombre="muestra")
    perfil.aprobar(espacio, n, aprobador=datos_alta["aprobador"])
    salidas = 0
    for hilo in historial.hilos(espacio).values():
        ultimo = hilo[-1] if hilo else None
        if ultimo is None or ultimo.del_negocio or not ultimo.texto:
            continue
        salida = agente.decidir(espacio, ultimo)
        if salida.via == "silencio":  # "ok gracias": no hay nada que enseñar en la Cola
            continue
        espacio.agregar_linea(agente.ARCHIVO, salida.a_dict())
        salidas += 1
    return {"sembrado": True, "mensajes": len(mensajes), "version": n,
            "descartados": len(descartados), "salidas": salidas}


def sembrar_si_toca() -> dict | None:
    """Lo que corre el arranque. Sin las dos variables no hace nada; si falla, no tumba el servicio."""
    nombre = os.environ.get(VARIABLE, "").strip()
    cliente_id = os.environ.get(VARIABLE_ESPACIO, "").strip()
    if not (nombre and cliente_id):
        return None
    try:
        resultado = sembrar(Espacio(cliente_id), nombre)
    except (EspacioInvalido, ValueError, OSError, KeyError) as error:
        log.warning("muestra %s no sembrada en %s: %s", nombre, cliente_id, error)
        return {"sembrado": False, "motivo": str(error)}
    log.info("muestra %s en %s: %s", nombre, cliente_id, resultado)
    return resultado
