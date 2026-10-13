"""Un cliente que contesta con respuestas GRABADAS, sin red ni clave.

Sirve para dos cosas: los tests y la demostración con el cuarto de muestra
ficticio. Lo grabado pasa por los mismos candados que una respuesta en vivo:
una cita grabada que no esté literal en el PDF se descarta igual.

Formato del archivo: {"<documento>": {"tipo": ..., "motivo": ..., "extraccion": {...}}}
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

from .esquemas import OTRO, es_clasificacion

NOMBRE = re.compile(r'<documento nombre="([^"]+)">')


class ClienteGrabado:
    def __init__(self, respuestas: dict, stop_reason: str = "end_turn"):
        self.respuestas = respuestas
        self.stop_reason = stop_reason
        self.llamadas: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    @classmethod
    def desde_archivo(cls, ruta: Path) -> ClienteGrabado:
        return cls(json.loads(Path(ruta).read_text(encoding="utf-8")))

    def _create(self, **kwargs):
        self.llamadas.append(kwargs)
        contenido = kwargs["messages"][-1]["content"]
        m = NOMBRE.search(contenido)
        grabado = self.respuestas.get(m.group(1) if m else "", {})
        esquema = kwargs["output_config"]["format"]["schema"]
        if es_clasificacion(esquema):
            datos = {"tipo": grabado.get("tipo", OTRO), "motivo": grabado.get("motivo", "sin respuesta grabada")}
        else:
            datos = grabado.get("extraccion", {})
        texto = json.dumps(datos, ensure_ascii=False)
        return SimpleNamespace(stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=texto)])
