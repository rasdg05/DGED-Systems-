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
  (`pendientes.py`) y el **seguimiento** que marca el semáforo (cotizado o
  preguntado, sin respuesta del cliente de 24 h a 21 días; D-041).
- **Ninguna cifra en el texto del enjambre** (invariante 1). Si la entrada pide
  cotizar, la cifra la escribe el cotizador con el perfil aprobado y se pega
  al final, igual que en `agente.decidir`.
- **Todo lo de una ronda espera el sí de una persona** (invariante 2, más
  estricta que Gestor: allá lo revisaba el orquestador y salía programado).
- Una ronda cargada es inmutable: otra ronda, otro nombre.
- **Una ronda no ofrece fechas que el calendario no dé por libres** (LXIII): ni
  ocupadas, ni sin saber, ni sin calendario conectado. El turno deja pasar lo
  que no se sabe con nota porque una persona lo lee en caliente; una ronda son
  decenas de borradores a aprobar de golpe, y ahí no se vende una fecha a ciegas.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

from . import calendario, cotizador, guardia, historial, pendientes, perfil, semaforo, voz
from .agente import ARCHIVO, Salida
from .espacio import Espacio

NOMBRE_VALIDO = re.compile(r"^[a-z0-9][a-z0-9-]{2,59}$")
MAX_TEXTOS = 3
SE_MOVIO = "la plática se movió desde que el enjambre la leyó"


#: Preguntar de nuevo lo que el cliente ya dijo (Gestor C5-I: "cada una le confirma al
#: cliente que nadie lo leyó"). Corrida GM, 2026-10-29: la casa lo hace en 15 de 43
#: "¿cuántas personas?" y una ronda aprobada le preguntó las personas a quien dijo 150.
#: Pedir OTRA fecha (la suya ya pasó) no es repetir: solo cuenta si sus fechas siguen por venir.
_PREGUNTA_PERSONAS = re.compile(r"\bcuant[oa]s (?:personas|son|serian|serán|vienen|huespedes|invitados)\b"
                                r"|\bpara cuant[oa]s\b")
_PREGUNTA_FECHAS = re.compile(r"\bque (?:fecha|fechas|dia|dias|mes)\b|\bpara (?:que|cuando) (?:fecha|dia)\b"
                              r"|\bde que mes\b|\bpara cuando\b"
                              # "nos comparte sus fechas" pide; "sigue interesado en sus fechas" confirma.
                              r"|\b(?:comparte|compartes|diga|dice|dime|indique|indica|pasa|pasas|manda|mande)\w*"
                              r"\s+(?:sus|tus|las)\s+fechas\b"
                              r"|\bque dia (?:les|le|te) gustaria\b"
                              r"|\bcuando (?:seria|serian|les gustaria|quieren|vienen|llegarian)\b")


_OCUPADO = re.compile(r"\b(?:ocupad[oa]s?|reservad[oa]s?|apartad[oa]s?|no (?:tenemos|hay) (?:disponib\w*|lugar))\b")


def _ya_no_hay(mensajes: list[historial.Mensaje]) -> bool:
    """La casa ya dijo que esa fecha no se puede: pedir otra no es repetir."""
    from . import conversacion
    return any(m.del_negocio and m.texto and _OCUPADO.search(conversacion.normalizar(m.texto)) for m in mensajes[-12:])


def pregunta_lo_ya_dicho(mensajes: list[historial.Mensaje], texto: str) -> str:
    """'' o qué dato ya había dicho el cliente que el texto vuelve a pedir."""
    from . import conversacion, lectura
    t = conversacion.normalizar(texto)
    if _PREGUNTA_PERSONAS.search(t) and (n := lectura.personas(mensajes)) is not None:
        return f"personas ({n})"
    if _PREGUNTA_FECHAS.search(t) and mensajes and (f := lectura.fechas(mensajes)) is not None \
            and f[1] >= lectura.hoy_de(mensajes[-1]) and not _ya_no_hay(mensajes):
        return f"fechas ({f[0].isoformat()})"
    return ""


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


def ya_atendidos(espacio: Espacio) -> frozenset[tuple[str, str]]:
    """(hilo, mensaje) que ya tienen una salida, aprobada o no. Lo que el enviador
    manda por el vinculado no vuelve al historial, así que la plática sigue
    viéndose "sin contestar" aunque ayer recibió su seguimiento (2026-10-28: 85
    de 98 borradores del enjambre iban a quien ya se le escribió)."""
    from . import agente
    return frozenset((s.hilo, s.responde_a) for s in agente.salidas(espacio))


def motivo_de_rechazo(entrada: dict, hilos: dict, por_hilo: dict, activo: dict | None,
                      ocupacion: calendario.Ocupacion | None = None, seguimiento: frozenset = frozenset(),
                      atendidos: frozenset = frozenset()) -> str:
    """'' si la entrada puede quedar esperando aprobación; si no, por qué no."""
    hilo = str(entrada.get("hilo", ""))
    if hilo not in hilos:
        return "el hilo no existe en el espacio"
    if hilos[hilo][-1].id != entrada.get("ultimo_id"):
        return SE_MOVIO
    if (hilo, entrada.get("ultimo_id")) in atendidos:
        return "ese mensaje ya tiene una salida (de otra ronda o de la cola): no se le escribe dos veces"
    pendiente = por_hilo.get(hilo)
    # Seguimiento (D-041): lo último es del negocio (cotizó o preguntó) y el
    # cliente no contesta hace 24 h a 21 días; el semáforo lo marca. Lo demás
    # que termina en el negocio no se persigue en ronda.
    if (pendiente is None or pendiente.estado != "espera") and hilo not in seguimiento:
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
        if (dato := pregunta_lo_ya_dicho(hilos[hilo], texto)):
            return f"pregunta lo que el cliente ya dijo: {dato}"
    cot, motivo = _cotizacion(entrada, activo)
    if cot is not None:
        if ocupacion is None or not ocupacion.configurada:
            return "cotiza fechas sin calendario conectado: no se vende una fecha a ciegas"
        d = ocupacion.disponibilidad(cot.propiedad, cot.llegada, cot.salida)
        if d.estado != calendario.LIBRE:
            return f"el calendario no da libre {cot.propiedad} en esas fechas ({d.estado}: {d.por_que})"
    return motivo


def validar(espacio: Espacio, ronda: dict) -> tuple[list[dict], list[dict]]:
    """(aceptadas, descartadas con motivo). No escribe nada: sirve para probar en local."""
    nombre = str(ronda.get("nombre", ""))
    if not NOMBRE_VALIDO.match(nombre):
        raise RondaInvalida("la ronda lleva nombre: minúsculas, números y guiones")
    if not str(ronda.get("orden", "")).strip():
        raise RondaInvalida("la ronda dice quién la mandó y qué pidió (`orden`)")
    from . import mesa
    hilos = mesa.clientes(espacio, historial.hilos(espacio))  # una administradora no recibe rondas (D-042)
    por_hilo = {p.hilo: p for p in pendientes.leer(hilos)}
    activo = perfil.activo(espacio)
    ocupacion = calendario.Ocupacion.de(espacio)
    seguimiento = frozenset(f.hilo for f in semaforo.leer(hilos) if f.seguimiento)
    atendidos = ya_atendidos(espacio)
    aceptadas, descartadas, vistos = [], [], set()
    for entrada in ronda.get("entradas", []) or []:
        motivo = motivo_de_rechazo(entrada, hilos, por_hilo, activo, ocupacion, seguimiento, atendidos)
        if not motivo:
            from . import capacidades  # "no le escribas" y "lo llevo yo" de la mesa (2026-10-31)
            motivo = capacidades.no_escribir(espacio, str(entrada.get("hilo", "")))
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


def se_movio(espacio: Espacio, salida: Salida, hilos: dict | None = None) -> bool:
    hilo = (hilos if hilos is not None else historial.hilos(espacio)).get(salida.hilo) or []
    return not hilo or hilo[-1].id != salida.responde_a
