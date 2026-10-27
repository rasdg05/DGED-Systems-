"""Envío por el dispositivo vinculado (D-037): lo que ya pasó los candados sale por el
WhatsApp del negocio, como el worker de Gestor Morelos.

Decisión del dueño, 2026-10-27: *"quiero hacerlo así directo como en Gestor
Morelos. No me importa que no haya conectado oficialmente Meta"*. Es el canal
no oficial: WhatsApp puede **suspender el número** si lo lee como envío masivo.
Por eso aquí no se decide *qué* sale (eso es `canal.motivo_para_no_enviar`,
el mismo para la vía oficial) sino *cómo*:

- **Una cola en el espacio** (`vinculado/cola.jsonl`). El servidor web encola;
  el proceso del lector vinculado (mismo contenedor, mismo volumen) la vacía.
- **Al paso de una persona**: uno a la vez, con espera al azar entre
  `PAUSA_MIN` y `PAUSA_MAX` segundos, solo de `HORA_DESDE` a `HORA_HASTA`
  (hora de México) y a lo más `TOPE_DIA` por día. Configurable por espacio
  (`config.json`, `envio`), nunca por arriba de los topes de aquí.
- **Se revisa otra vez justo antes de mandar** (la plática se movió, la fecha
  se apartó, se quitó la aprobación): lo que ya no pasa, no sale, y queda
  escrito por qué.
- **Una plática no recibe dos envíos de rondas en `HORAS_ENTRE_RONDAS`.**

Este módulo no importa neonize: `turno(...)` recibe la función que manda.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .espacio import Espacio

logger = logging.getLogger("agente.enviador")

COLA = "vinculado/cola.jsonl"
ENVIADOS = "enviados.jsonl"
ZONA = ZoneInfo("America/Mexico_City")
PAUSA_MIN, PAUSA_MAX = 40, 50    # segundos entre envíos (dueño, 2026-10-27: "1 cada 40 segundos")
HORA_DESDE, HORA_HASTA = 9, 20   # de 9:00 a 20:59, hora de México
TOPE_DIA = 100                   # envíos por día y número, como techo (dueño, 2026-10-27: de 60 a 100)
HORAS_ENTRE_RONDAS = 24


@dataclass
class Ritmo:
    pausa_min: int = PAUSA_MIN
    pausa_max: int = PAUSA_MAX
    hora_desde: int = HORA_DESDE
    hora_hasta: int = HORA_HASTA
    tope_dia: int = TOPE_DIA

    @classmethod
    def de(cls, espacio: Espacio) -> Ritmo:
        """El del espacio, sin pasar los techos de aquí (más rápido, no)."""
        c = espacio.config().get("envio", {}) or {}
        r = cls()
        r.pausa_min = max(PAUSA_MIN, int(c.get("pausa_min", PAUSA_MIN)))
        r.pausa_max = max(r.pausa_min, int(c.get("pausa_max", PAUSA_MAX)))
        r.hora_desde = max(HORA_DESDE - 1, min(23, int(c.get("hora_desde", HORA_DESDE))))
        r.hora_hasta = min(HORA_HASTA + 1, max(r.hora_desde, int(c.get("hora_hasta", HORA_HASTA))))
        r.tope_dia = min(TOPE_DIA, max(0, int(c.get("tope_dia", TOPE_DIA))))
        return r


def encolar(espacio: Espacio, salida_id: str, ahora: datetime | None = None) -> None:
    ya = {e["salida"] for e in espacio.leer_lineas(COLA)}
    if salida_id in ya:
        return
    espacio.agregar_linea(COLA, {"salida": salida_id,
                                 "encolada": (ahora or datetime.now(timezone.utc)).isoformat(timespec="seconds")})


def _hechos(espacio: Espacio) -> dict[str, dict]:
    """Lo que ya se resolvió de la cola (enviado o descartado), por salida."""
    return {e["salida"]: e for e in espacio.leer_lineas(ENVIADOS) if e.get("salida")}


def pendientes(espacio: Espacio) -> list[str]:
    hechos = _hechos(espacio)
    return [e["salida"] for e in espacio.leer_lineas(COLA) if e["salida"] not in hechos]


def _enviados_hoy(espacio: Espacio, ahora: datetime) -> list[dict]:
    hoy = ahora.astimezone(ZONA).date()
    return [e for e in espacio.leer_lineas(ENVIADOS) if e.get("enviado")
            and datetime.fromisoformat(e["cuando"]).astimezone(ZONA).date() == hoy]


def por_que_esperar(espacio: Espacio, ritmo: Ritmo, ahora: datetime) -> str:
    """'' si toca mandar ahora; si no, por qué se espera."""
    local = ahora.astimezone(ZONA)
    if not (ritmo.hora_desde <= local.hour <= ritmo.hora_hasta):
        return f"fuera de horario ({ritmo.hora_desde}:00 a {ritmo.hora_hasta}:59)"
    hoy = _enviados_hoy(espacio, ahora)
    if len(hoy) >= ritmo.tope_dia:
        return f"tope del día ({ritmo.tope_dia})"
    if hoy:
        ultimo = max(datetime.fromisoformat(e["cuando"]) for e in hoy)
        if ahora - ultimo < timedelta(seconds=ritmo.pausa_min):
            return "pausa entre envíos"
    return ""


def _ronda_reciente(espacio: Espacio, hilo: str, ahora: datetime) -> bool:
    limite = ahora - timedelta(hours=HORAS_ENTRE_RONDAS)
    return any(e.get("enviado") and e.get("hilo") == hilo and e.get("via") == "ronda"
               and datetime.fromisoformat(e["cuando"]) >= limite for e in espacio.leer_lineas(ENVIADOS))


def turno(espacio: Espacio, mandar, ahora: datetime | None = None) -> dict | None:
    """Manda a lo más UNA salida de la cola, si toca. Devuelve lo que pasó (o None
    si no había nada o había que esperar). `mandar(hilo, texto)` hace el envío."""
    from . import agente, canal

    ahora = ahora or datetime.now(timezone.utc)
    cola = pendientes(espacio)
    if not cola:
        return None
    if (espera := por_que_esperar(espacio, Ritmo.de(espacio), ahora)):
        return {"espera": espera}
    salidas = {s.id: s for s in agente.salidas(espacio)}
    for salida_id in cola:
        salida = salidas.get(salida_id)
        registro = {"salida": salida_id, "cuando": ahora.isoformat(timespec="seconds"), "canal": "vinculado"}
        if salida is None:
            espacio.agregar_linea(ENVIADOS, {**registro, "enviado": False, "motivo": "la salida no existe"})
            continue
        registro.update(hilo=salida.hilo, via=salida.via)
        motivo = canal.motivo_para_no_enviar(espacio, salida)
        if not motivo and salida.via == "ronda" and _ronda_reciente(espacio, salida.hilo, ahora):
            motivo = f"esa plática ya recibió una ronda en las últimas {HORAS_ENTRE_RONDAS} h"
        if motivo:
            espacio.agregar_linea(ENVIADOS, {**registro, "enviado": False, "motivo": motivo})
            continue
        try:
            mandar(salida.hilo, salida.texto)
        except Exception as error:  # noqa: BLE001 - lo que diga WhatsApp queda escrito y no se reintenta solo
            espacio.agregar_linea(ENVIADOS, {**registro, "enviado": False, "motivo": f"falló: {type(error).__name__}"})
            return {"salida": salida_id, "enviado": False}
        espacio.agregar_linea(ENVIADOS, {**registro, "enviado": True})
        return {"salida": salida_id, "enviado": True}
    return None


def correr(espacio: Espacio, mandar, listo=lambda: True) -> None:  # pragma: no cover - bucle del proceso
    """El bucle del proceso vinculado: un turno, una pausa al azar, otra vez."""
    from . import mesa

    ritmo = Ritmo.de(espacio)
    while True:
        espera = 15
        try:
            if listo():
                mesa.reporte_si_toca(espacio)
                mesa.despachar(espacio, mandar)  # lo de la mesa no espera turno: es para la dueña
                hecho = turno(espacio, mandar)
                if hecho and "enviado" in hecho:
                    logger.info("envío %s: %s", hecho["salida"], "ok" if hecho["enviado"] else "falló")
                    ritmo = Ritmo.de(espacio)
                    espera = random.uniform(ritmo.pausa_min, ritmo.pausa_max)
        except Exception:
            logger.exception("Error en el turno de envío")
        time.sleep(espera)
