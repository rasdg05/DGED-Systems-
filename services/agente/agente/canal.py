"""El canal: WhatsApp Cloud API, la vía oficial. Nada sale por otro lado.

Sin conector oficial configurado (`WHATSAPP_TOKEN` en el entorno y
`phone_number_id` en el `config.json` del espacio) el agente no envía nada y lo
dice (invariante 7, como el Oráculo sin clave). No hay respaldo por WhatsApp Web:
ese canal pone en riesgo el número del cliente (P1, `docs/08-mercado.md` §1.5).

Qué puede salir depende del encendido del espacio (`config.json`, `encendido`):

- `sombra` (el de fábrica): nada. El agente redacta y se compara (`sombra.py`).
- `sin_cifra`: salen las respuestas guardadas y las del modelo que no llevan
  cifra; lo que va a la persona no sale.
- Una cotización sale solo con la aprobación de una persona, en cualquier
  encendido (invariante 2).

**No medido contra Meta**: el envío real necesita la app de DGED como Tech
Provider (`MEMORY/FUENTES.md`). La forma de la petición sigue la documentación
de la Cloud API.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import urllib.request

from .agente import Salida, aprobadas
from .espacio import Espacio

ENCENDIDOS = ("sombra", "sin_cifra")
GRAPH = "https://graph.facebook.com"


class CanalDormido(RuntimeError):
    pass


class EnvioNoPermitido(PermissionError):
    pass


def token() -> str:
    return os.environ.get("WHATSAPP_TOKEN", "").strip()


def configurado(espacio: Espacio) -> bool:
    return bool(token() and espacio.config().get("phone_number_id"))


def motivo_para_no_enviar(espacio: Espacio, salida: Salida) -> str:
    """'' si la salida puede enviarse; si no, por qué."""
    if salida.cliente_id != espacio.cliente_id:
        return "la salida es de otro cliente"
    if not configurado(espacio):
        return "sin conector oficial (WHATSAPP_TOKEN y phone_number_id): el agente no envía"
    if salida.requiere_aprobacion and salida.id not in aprobadas(espacio):
        return "cotización sin aprobación de una persona"
    if salida.via == "ronda":
        from . import rondas  # rondas importa de agente; aquí se llega ya cargado
        if rondas.se_movio(espacio, salida):
            return rondas.SE_MOVIO
    encendido = espacio.config().get("encendido", "sombra")
    if encendido not in ENCENDIDOS or encendido == "sombra":
        return "espacio en sombra: el agente redacta y no envía"
    if salida.a_persona:
        return "la contesta la persona"
    if salida.via == "silencio" or not salida.texto.strip():
        return "no hay nada que mandar: el agente calla"
    return ""


def firma_valida(cuerpo: bytes, firma: str | None) -> bool:
    """`X-Hub-Signature-256` de Meta. Sin `WHATSAPP_APP_SECRET` no se acepta nada."""
    secreto = os.environ.get("WHATSAPP_APP_SECRET", "").strip()
    if not secreto or not firma or not firma.startswith("sha256="):
        return False
    esperada = hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, firma.removeprefix("sha256="))


def _post(url: str, cuerpo: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def enviar(espacio: Espacio, salida: Salida, transporte=_post) -> dict:
    if not configurado(espacio):
        raise CanalDormido(motivo_para_no_enviar(espacio, salida))
    if (motivo := motivo_para_no_enviar(espacio, salida)):
        raise EnvioNoPermitido(motivo)
    version = os.environ.get("WHATSAPP_GRAPH_VERSION", "").strip() or "v23.0"
    url = f"{GRAPH}/{version}/{espacio.config()['phone_number_id']}/messages"
    respuesta = transporte(url, {"messaging_product": "whatsapp", "to": salida.hilo, "type": "text",
                                 "text": {"body": salida.texto}})
    espacio.agregar_linea("enviados.jsonl", {"salida": salida.id, "respuesta": respuesta})
    return respuesta
