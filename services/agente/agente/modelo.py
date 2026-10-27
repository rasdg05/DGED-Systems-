"""La única puerta a la API de Anthropic. Todo lo que gasta pasa por aquí.

- Dormido sin `ANTHROPIC_API_KEY` (como el Oráculo y el lector): `Dormido`.
  Una llave que no es de un espacio de trabajo exige `ANTHROPIC_WORKSPACE_ID`
  (la API contesta 400 sin el encabezado; medido en Railway el 2026-10-27).
- Antes de cada llamada, el tope del cliente (`gasto.exigir_saldo`); después,
  el gasto anotado con el `usage` real. Al tope, cero llamadas (invariante 5).
- El contexto se arma solo con el perfil del espacio que llama (invariante 4).
  El perfil va primero en `system` con `cache_control`, para que la caché lo
  reuse en cada turno de ese cliente; la caché es por prefijo exacto, así que
  dos clientes nunca comparten entrada.
- Turnos de rutina con el modelo chico; el grande solo si el chico lo pide
  (`dificil=si`) y para construir el perfil.
"""
from __future__ import annotations

import json
import os
import re

from . import gasto, voz
from .espacio import Espacio

MODELO_RUTINA = "claude-haiku-5-5"
MODELO_GRANDE = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

INSTRUCCIONES = (
    "Contestas los mensajes de WhatsApp de un negocio, con su voz, como lo haría la persona que "
    "atiende. Abajo está el perfil aprobado del negocio: sus datos, sus frases y sus preguntas "
    "frecuentes. Reglas que no se rompen:\n"
    "1) Nunca escribas una cifra: ni precio, ni monto, ni porcentaje, ni fecha con número, ni "
    "cantidad. Las cifras las pone otro sistema. Si preguntan precio o disponibilidad, pide lo que "
    "falte (fechas, personas, si hay evento) sin números y marca cotizar=si.\n"
    "2) Si no está en el perfil, no lo afirmes: marca persona=si y di que lo confirmas.\n"
    "3) Reclamo, pago, reembolso, cancelación o dato delicado: persona=si.\n"
    "4) Si preguntan si eres una persona, di la verdad: eres el asistente automático del negocio.\n"
    "5) Escribe como el negocio: corto, sin listas, sin asteriscos.\n"
    "Al final agrega EXACTAMENTE una línea que el cliente no ve:\n"
    "[[META cotizar=<si|no> propiedad=<id o vacío> llegada=<AAAA-MM-DD o vacío> "
    "salida=<AAAA-MM-DD o vacío> personas=<entero o vacío> evento=<si|no> persona=<si|no> "
    "dificil=<si|no> duda=<qué hay que confirmar, en una frase>]]"
)

_META = re.compile(r"\[\[\s*META\b(.*?)\]\]", re.IGNORECASE | re.DOTALL)
_CAMPO = re.compile(r"(\w+)=(.*?)(?=\s+\w+=|$)", re.DOTALL)


class Dormido(RuntimeError):
    """Sin clave de API: el agente no llama a nada y todo pasa a la persona."""


class LlamadaFallida(RuntimeError):
    pass


def cliente_real():
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise Dormido("sin ANTHROPIC_API_KEY el agente no redacta: todo pasa a la persona")
    import anthropic

    espacio_de_trabajo = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    if espacio_de_trabajo:
        return anthropic.Anthropic(default_headers={"anthropic-workspace-id": espacio_de_trabajo})
    return anthropic.Anthropic()


def perfil_para_modelo(perfil: dict) -> dict:
    """Lo que el modelo necesita leer: datos, voz y preguntas frecuentes. Las
    reglas de cotización no van: el modelo no calcula, y si no las ve no las copia."""
    return {
        "giro": perfil.get("giro"),
        "nombre_comercial": perfil.get("nombre_comercial"),
        "trato": perfil.get("trato"),
        "datos": [{k: v for k, v in d.items() if k != "origen"} for d in perfil.get("datos", [])],
        "voz": [v["frase"] for v in perfil.get("voz", [])],
        "faq": [{"pregunta": f["pregunta"], "respuesta": f["respuesta"]} for f in perfil.get("faq", [])],
        "escala": [e["caso"] for e in perfil.get("escala", [])],
    }


def system_de(espacio: Espacio, perfil: dict) -> list[dict]:
    contrato = json.dumps(perfil_para_modelo(perfil), ensure_ascii=False, sort_keys=True)
    return [
        {"type": "text", "text": INSTRUCCIONES},
        {"type": "text", "text": f"Negocio: {espacio.cliente_id}\n{voz.reglas_para_redactar(perfil)}\n"
                                 f"Perfil aprobado:\n{contrato}",
         "cache_control": {"type": "ephemeral"}},
    ]


def extraer_meta(texto: str) -> tuple[str, dict]:
    texto = texto or ""
    m = _META.search(texto)
    limpio = _META.sub("", texto).strip()
    if not m:
        return limpio, {}
    return limpio, {k.lower(): v.strip() for k, v in _CAMPO.findall(m.group(1).strip())}


def _texto(contenido) -> str:
    return "".join(getattr(b, "text", "") for b in contenido if getattr(b, "type", "") == "text")


def turno(espacio: Espacio, perfil: dict, conversacion: list[dict], client=None,
          modelo: str | None = None) -> tuple[str, dict]:
    """Un borrador para el último mensaje del cliente final. (texto, meta)."""
    gasto.exigir_saldo(espacio)
    client = client or cliente_real()
    modelo = modelo or os.environ.get("AGENTE_MODELO_RUTINA", "").strip() or MODELO_RUTINA
    pedido = dict(model=modelo, max_tokens=2048, system=system_de(espacio, perfil),
                  output_config={"effort": "low"}, messages=conversacion)
    try:
        if modelo == MODELO_RUTINA:
            respuesta = client.messages.create(**pedido)
        else:
            respuesta = client.beta.messages.create(**pedido, betas=[FALLBACK_BETA], fallbacks="default")
    except Exception as error:  # conexión, 4xx/5xx: el cliente final no se queda sin respuesta, la da la persona
        raise LlamadaFallida(type(error).__name__) from error
    gasto.registrar(espacio, modelo, getattr(respuesta, "usage", None), motivo="turno")
    if getattr(respuesta, "stop_reason", "") == "refusal":
        return "", {"persona": "si", "duda": "el modelo declinó contestar"}
    return extraer_meta(_texto(respuesta.content))
