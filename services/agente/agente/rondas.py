"""Rondas del enjambre: lo que agentes de código redactaron en local, con sus candados.

Viene de Gestor (`app/services/rondas.py`, 2026-10-13 a 2026-10-26): un
enjambre de agentes de Claude Code lee cada plática pendiente completa, redacta
con la voz de la casa y el orquestador revisa cada texto contra su plática. No
gasta API: corre en la sesión de código (`.claude/skills/enjambre/SKILL.md`).
Lo que Gestor aprendió y aquí es código, no costumbre:

- **Si la plática se movió desde que se leyó, no sale** (`autonomo._arrancar_dicho`,
  `COLA_CAMBIADA`). Cada entrada cita el `ultimo_id` que leyó; se revisa al
  cargar y otra vez al enviar (`canal.motivo_para_no_enviar`).
- **Reclamos, medios y acuses no los contesta el enjambre**: solo `espera`
  (`pendientes.py`).
- **Ninguna cifra en el texto del enjambre** (invariante 1). Si la entrada pide
  cotizar, la cifra la escribe el cotizador con el perfil aprobado y se pega
  al final, igual que en `agente.decidir`.
- **Todo lo de una ronda espera el sí de una persona** (invariante 2, más
  estricta que Gestor: allá lo revisaba el orquestador y salía programado).
- Una ronda cargada es inmutable: otra ronda, otro nombre.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

from . import cotizador, guardia, historial, pendientes, perfil, voz
from .agente import ARCHIVO, Salida
from .espacio import Espacio

NOMBRE_VALIDO = re.compile(r"^[a-z0-9][a-z0-9-]{2,59}$")
MAX_TEXTOS = 3
SE_MOVIO = "la plática se movió desde que el enjambre la leyó"


class RondaInvalida(ValueError):
    pass


def _ruta(nombre: str) -> str:
    return f"rondas/{nombre}.json"


def _cotizacion(entrada: dict, activo: dict | None) -> tuple[cotizador.Cotizacion | None, str]:
    pedido = entrada.get("cotizacion")
    if not pedido:
        return None, ""
    if activo is None:
        return None, "pide cotizar y no hay perfil aprobado: la cifra no tiene de dónde salir"
    try:
        cot = cotizador.cotizar(activo, str(pedido["propiedad"]), date.fromisoformat(pedido["llegada"]),
                                date.fromisoformat(pedido["salida"]), int(pedido["personas"]),
                                bool(pedido.get("evento")))
    except (KeyError, TypeError, ValueError) as error:
        return None, f"cotización mal pedida: {error}"
    if not cot.completa:
        return None, "cotización incompleta: " + "; ".join(cot.faltan)
    return cot, ""


def motivo_de_rechazo(entrada: dict, hilos: dict, por_hilo: dict, activo: dict | None) -> str:
    """'' si la entrada puede quedar esperando aprobación; si no, por qué no."""
    hilo = str(entrada.get("hilo", ""))
    if hilo not in hilos:
        return "el hilo no existe en el espacio"
    if hilos[hilo][-1].id != entrada.get("ultimo_id"):
        return SE_MOVIO
    pendiente = por_hilo.get(hilo)
    if pendiente is None or pendiente.estado != "espera":
        return f"no espera respuesta ({pendiente.estado if pendiente else 'lo último es del negocio'})"
    textos = entrada.get("textos")
    if not isinstance(textos, list) or not textos or not all(isinstance(t, str) and t.strip() for t in textos):
        return "sin textos"
    if len(textos) > MAX_TEXTOS:
        return f"más de {MAX_TEXTOS} mensajes de golpe"
    for texto in textos:
        if (cifras := guardia.cifras_no_permitidas(texto)):
            return f"cifra en el texto del enjambre (la pone el cotizador): {cifras}"
        if guardia.dice_ser_persona(texto):
            return "el texto dice ser una persona"
        if activo is not None and (rasgos := voz.hallazgos(texto, activo)):
            return "voz ajena: " + "; ".join(rasgos)
    return _cotizacion(entrada, activo)[1]


def validar(espacio: Espacio, ronda: dict) -> tuple[list[dict], list[dict]]:
    """(aceptadas, descartadas con motivo). No escribe nada: sirve para probar en local."""
    nombre = str(ronda.get("nombre", ""))
    if not NOMBRE_VALIDO.match(nombre):
        raise RondaInvalida("la ronda lleva nombre: minúsculas, números y guiones")
    if not str(ronda.get("orden", "")).strip():
        raise RondaInvalida("la ronda dice quién la mandó y qué pidió (`orden`)")
    hilos = historial.hilos(espacio)
    por_hilo = {p.hilo: p for p in pendientes.leer(hilos)}
    activo = perfil.activo(espacio)
    aceptadas, descartadas, vistos = [], [], set()
    for entrada in ronda.get("entradas", []) or []:
        motivo = motivo_de_rechazo(entrada, hilos, por_hilo, activo)
        if not motivo and entrada.get("hilo") in vistos:
            motivo = "el hilo ya va en esta ronda"
        (descartadas if motivo else aceptadas).append(dict(entrada, motivo=motivo) if motivo else entrada)
        vistos.add(entrada.get("hilo"))
    return aceptadas, descartadas


def cargar(espacio: Espacio, ronda: dict) -> tuple[list[Salida], list[dict]]:
    """Las aceptadas quedan como salidas esperando aprobación. Nada se envía aquí."""
    aceptadas, descartadas = validar(espacio, ronda)
    nombre = ronda["nombre"]
    if espacio.ruta(_ruta(nombre)).exists():
        raise RondaInvalida(f"la ronda {nombre} ya se cargó: otra ronda, otro nombre")
    activo = perfil.activo(espacio)
    salidas = []
    for entrada in aceptadas:
        cot, _ = _cotizacion(entrada, activo)
        texto = "\n\n".join(t.strip() for t in entrada["textos"]) + (f"\n\n{cot.texto()}" if cot else "")
        salida = Salida(cliente_id=espacio.cliente_id, hilo=entrada["hilo"], responde_a=entrada["ultimo_id"],
                        via="ronda", texto=texto, motivo=f"ronda {nombre}: {entrada.get('resumen', '')}".strip(),
                        cotizacion=cot.a_dict() if cot else None, requiere_aprobacion=True)
        espacio.agregar_linea(ARCHIVO, salida.a_dict())
        salidas.append(salida)
    espacio.escribir_json(_ruta(nombre), {
        "nombre": nombre, "orden": ronda["orden"], "autor": ronda.get("autor", "enjambre local"),
        "cargada": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "salidas": [s.id for s in salidas], "descartadas": descartadas})
    return salidas, descartadas


def se_movio(espacio: Espacio, salida: Salida) -> bool:
    hilo = historial.hilos(espacio).get(salida.hilo) or []
    return not hilo or hilo[-1].id != salida.responde_a
