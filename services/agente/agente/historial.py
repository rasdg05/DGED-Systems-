"""El historial del negocio, tal como lo manda Meta, guardado en su espacio.

Formato medido el 2026-10-21 contra la documentación de coexistencia
(`MEMORY/FUENTES.md`, "WhatsApp coexistencia"): webhooks `history` con
`threads[].messages[]` y fase/porción/progreso; los mensajes nuevos llegan por
`messages` (del cliente final) y `smb_message_echoes` (lo que el negocio manda
desde su app). Un mensaje es del negocio si `from` es el número del negocio.

Los medios del historial llegan como `media_placeholder` sin contenido: se
guardan sin texto y no pueden ser origen de nada (no hay cita que verificar).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .espacio import Espacio

ARCHIVO = "historial.jsonl"


@dataclass(frozen=True)
class Mensaje:
    id: str
    hilo: str            # el número del cliente final; no sale del espacio
    del_negocio: bool
    ts: int
    tipo: str
    texto: str | None

    def a_dict(self) -> dict:
        return asdict(self)


def _texto(m: dict) -> str | None:
    tipo = m.get("type")
    cuerpo = m.get(tipo) if isinstance(m.get(tipo), dict) else {}
    if tipo == "text":
        return cuerpo.get("body")
    # Una foto o un documento con pie trae texto escrito por una persona.
    return cuerpo.get("caption") if cuerpo else None


def _mensaje(m: dict, hilo: str, negocio: str) -> Mensaje | None:
    if not m.get("id") or not m.get("from"):
        return None
    try:
        ts = int(m.get("timestamp", 0))
    except (TypeError, ValueError):
        ts = 0
    return Mensaje(id=m["id"], hilo=hilo, del_negocio=m["from"] == negocio,
                   ts=ts, tipo=m.get("type", ""), texto=_texto(m))


def de_webhook(carga: dict) -> list[Mensaje]:
    """Todos los mensajes de un webhook de WhatsApp Business (historial o vivo)."""
    salida: list[Mensaje] = []
    for entrada in carga.get("entry", []) or []:
        for cambio in entrada.get("changes", []) or []:
            valor = cambio.get("value", {}) or {}
            negocio = (valor.get("metadata") or {}).get("display_phone_number", "")
            campo = cambio.get("field")
            if campo == "history":
                for bloque in valor.get("history", []) or []:
                    for hilo in bloque.get("threads", []) or []:
                        for m in hilo.get("messages", []) or []:
                            if (msg := _mensaje(m, hilo.get("id", ""), negocio)):
                                salida.append(msg)
            elif campo == "messages":
                for m in valor.get("messages", []) or []:
                    if (msg := _mensaje(m, m.get("from", ""), negocio)):
                        salida.append(msg)
            elif campo == "smb_message_echoes":
                for m in valor.get("message_echoes", []) or []:
                    if (msg := _mensaje(m, m.get("to", ""), negocio)):
                        salida.append(msg)
    return salida


def guardar(espacio: Espacio, mensajes: list[Mensaje]) -> int:
    """Agrega sin duplicar (Meta puede reenviar una porción). Devuelve cuántos entraron."""
    vistos = {m["id"] for m in espacio.leer_lineas(ARCHIVO)}
    nuevos = 0
    for m in mensajes:
        if m.id in vistos:
            continue
        espacio.agregar_linea(ARCHIVO, m.a_dict())
        vistos.add(m.id)
        nuevos += 1
    return nuevos


def cargar(espacio: Espacio) -> list[Mensaje]:
    return sorted((Mensaje(**d) for d in espacio.leer_lineas(ARCHIVO)), key=lambda m: (m.ts, m.id))


def por_id(espacio: Espacio) -> dict[str, Mensaje]:
    return {m.id: m for m in cargar(espacio)}


def hilos(espacio: Espacio) -> dict[str, list[Mensaje]]:
    salida: dict[str, list[Mensaje]] = {}
    for m in cargar(espacio):
        salida.setdefault(m.hilo, []).append(m)
    return salida
