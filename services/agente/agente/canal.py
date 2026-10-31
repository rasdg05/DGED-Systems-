"""El canal: por dónde sale lo que el agente redactó. Dos vías, los mismos candados.

- **Cloud API (oficial)**: `WHATSAPP_TOKEN` en el entorno y `phone_number_id` en el
  `config.json` del espacio.
- **Dispositivo vinculado** (D-037, decisión del dueño): `"canal": "vinculado"` en
  el `config.json` y el lector conectado con el número del negocio. Sale por el
  WhatsApp del negocio, como Gestor Morelos, encolado y al paso de una persona
  (`enviador.py`). Riesgo aceptado por el dueño: WhatsApp puede suspender un
  número que lee como envío masivo (P1, `docs/08-mercado.md` §1.5).

Sin ninguna de las dos el agente no envía nada y lo dice (invariante 7, como el
Oráculo sin clave). Qué sale lo decide `motivo_para_no_enviar`, igual por las dos.

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
from .guardia import trae_dinero

ENCENDIDOS = ("sombra", "sin_cifra")
GRAPH = "https://graph.facebook.com"


class CanalDormido(RuntimeError):
    pass


class EnvioNoPermitido(PermissionError):
    pass


def token() -> str:
    return os.environ.get("WHATSAPP_TOKEN", "").strip()


def oficial(espacio: Espacio) -> bool:
    return bool(token() and espacio.config().get("phone_number_id"))


def vinculado_listo(espacio: Espacio) -> bool:
    """El dueño eligió el vinculado y el lector está conectado con el número del negocio."""
    if espacio.config().get("canal") != "vinculado":
        return False
    from . import vinculado
    return vinculado.leer_estado(espacio).get("estado") == "conectado"


def configurado(espacio: Espacio) -> bool:
    return oficial(espacio) or vinculado_listo(espacio)


def contexto(espacio: Espacio) -> dict:
    """Lo que `motivo_para_no_enviar` lee del disco, leído una vez: para aprobar una ronda
    de 120 sin releer el historial 240 veces (revisión del 2026-10-31: 14 s con el lector
    detenido). Solo vale dentro de una misma orden: lo de afuera puede cambiar después."""
    from . import calendario, capacidades, historial
    return {"aprobadas": aprobadas(espacio), "descartadas": capacidades.descartadas(espacio),
            "marcas": capacidades.marcas(espacio), "configurado": configurado(espacio),
            "hilos": historial.hilos(espacio), "ocupacion": calendario.Ocupacion.de(espacio)}


def motivo_para_no_enviar(espacio: Espacio, salida: Salida, ctx: dict | None = None) -> str:
    """'' si la salida puede enviarse; si no, por qué. `ctx` (de `contexto`) evita releer el disco."""
    if salida.cliente_id != espacio.cliente_id:
        return "la salida es de otro cliente"
    from . import capacidades  # lo que la dueña ordenó por la mesa manda sobre lo aprobado (2026-10-31);
    # va antes que el conector: su decisión es lo que se le explica primero
    if salida.id in (ctx["descartadas"] if ctx else capacidades.descartadas(espacio)):
        return capacidades.DESCARTADA
    if salida.via != "mesa" and (marca := capacidades.no_escribir(espacio, salida.hilo,
                                                                  ctx["marcas"] if ctx else None)):
        return marca  # lo que ella misma dicta sí sale: es su cliente y sus palabras
    if not (ctx["configurado"] if ctx else configurado(espacio)):
        return ("sin conector oficial (WHATSAPP_TOKEN y phone_number_id) ni vinculado conectado "
                "con \"canal\": \"vinculado\": el agente no envía")
    from . import mesa
    if mesa.es_admin(espacio, salida.hilo):
        return "la plática es de una administradora: a ella le escribe la mesa, no la cola"
    ya = ctx["aprobadas"] if ctx else aprobadas(espacio)
    if salida.requiere_aprobacion and salida.id not in ya:
        return "cotización sin aprobación de una persona"
    if trae_dinero(salida.texto) and salida.via != "guardada" and salida.id not in ya:
        # Defensa de fondo: una cifra que no viene de una guardada aprobada sale solo
        # con el sí de una persona, aunque alguien olvide marcar `requiere_aprobacion`.
        return "cifra sin aprobación de una persona"
    if salida.cotizacion:
        from . import calendario
        if (apartada := calendario.apartada(espacio, salida.cotizacion, ctx["ocupacion"] if ctx else None)):
            return apartada
    if salida.via == "ronda":
        from . import rondas  # rondas importa de agente; aquí se llega ya cargado
        if rondas.se_movio(espacio, salida, ctx["hilos"] if ctx else None):
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


def enviar(espacio: Espacio, salida: Salida, transporte=_post, ctx: dict | None = None) -> dict:
    if not (ctx["configurado"] if ctx else configurado(espacio)):
        raise CanalDormido(motivo_para_no_enviar(espacio, salida, ctx))
    if (motivo := motivo_para_no_enviar(espacio, salida, ctx)):
        raise EnvioNoPermitido(motivo)
    if not oficial(espacio):
        # Vinculado: se encola y la manda el proceso del lector, al paso de una
        # persona; justo antes de mandar se revisa todo otra vez (`enviador.turno`).
        from . import enviador
        enviador.encolar(espacio, salida.id)
        return {"encolada": True, "canal": "vinculado"}
    version = os.environ.get("WHATSAPP_GRAPH_VERSION", "").strip() or "v23.0"
    url = f"{GRAPH}/{version}/{espacio.config()['phone_number_id']}/messages"
    respuesta = transporte(url, {"messaging_product": "whatsapp", "to": salida.hilo, "type": "text",
                                 "text": {"body": salida.texto}})
    espacio.agregar_linea("enviados.jsonl", {"salida": salida.id, "respuesta": respuesta})
    return respuesta
