"""Sombra y vara: el agente redacta, no envía, y se compara contra lo que la persona contestó.

La vara es la de fq-bot (vía `herramientas/vara.py` de Gestor), recortada a lo
que P1 promete medir:

- **% que la persona habría enviado sin editar**: el borrador que sí iba a
  salir se parece (≥ `PARECIDO`) a lo que la persona mandó de verdad.
- **Cobertura junto al acierto**: qué fracción el agente sí contestó. Un agente
  que todo lo pasa a la persona tiene acierto perfecto y no sirve.
- **Errores de cifra**: salidas con un número que no puso el cotizador. Deben
  ser 0 por construcción; se cuentan igual, porque "por construcción" es lo
  que se rompe sin avisar.
- **Tiempo hasta la respuesta y hasta la cotización** de la persona: la línea
  base que el agente tiene que bajar.
- **Holdout fuera de tiempo**: el 25% más nuevo no se mira al afinar; se abre
  una vez con `abrir_holdout=True`.
- **Placebo**: las respuestas reales barajadas entre momentos. El acierto debe
  caer; si no cae, la vara no mide nada.
- **n < 30 no concluye**, ni para encender ni para apagar.
"""
from __future__ import annotations

import random
import statistics
import unicodedata
from difflib import SequenceMatcher

from . import agente, guardia, historial
from .espacio import Espacio
from .perfil import numeros

MINIMO = 30
PARECIDO = 0.8
FRACCION_HOLDOUT = 0.25


def _normal(t: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")
    return " ".join(sin.split())


def parecido(a: str, b: str) -> float:
    return SequenceMatcher(None, _normal(a), _normal(b)).ratio()


def error_de_cifra(s: agente.Salida) -> bool:
    if s.via == "persona":
        return False
    if s.via == "guardada":
        return guardia.trae_dinero(s.texto)
    permitidas = numeros((s.cotizacion or {}).get("texto", "")) if s.via == "cotizador" else set()
    return bool(guardia.cifras_no_permitidas(s.texto, permitidas))


def repasar(espacio: Espacio, client=None) -> int:
    """Corre el agente sobre cada mensaje del cliente final que la persona contestó.
    Cada borrador ve solo lo anterior a su mensaje. Devuelve cuántos redactó."""
    hechos = {s.responde_a for s in agente.salidas(espacio)}
    n = 0
    for mensajes in historial.hilos(espacio).values():
        for i, m in enumerate(mensajes):
            if m.del_negocio or m.id in hechos or not m.texto:
                continue
            siguiente = mensajes[i + 1] if i + 1 < len(mensajes) else None
            if siguiente is None or not siguiente.del_negocio:
                continue  # solo el último mensaje de una ráfaga, y solo si la persona contestó
            espacio.agregar_linea(agente.ARCHIVO, agente.decidir(espacio, m, client=client).a_dict())
            n += 1
    return n


def _pares(espacio: Espacio) -> list[dict]:
    hilos = historial.hilos(espacio)
    por_id = historial.por_id(espacio)
    pares = []
    for s in agente.salidas(espacio):
        entrante = por_id.get(s.responde_a)
        if entrante is None:
            continue
        real = next((m for m in hilos.get(entrante.hilo, []) if m.del_negocio and m.ts >= entrante.ts and m.texto), None)
        pares.append({"salida": s, "entrante": entrante, "real": real})
    return sorted(pares, key=lambda p: (p["entrante"].ts, p["entrante"].id))


def _acierto(pares: list[dict], reales: list[str | None]) -> tuple[int, int]:
    """(contestadas por el agente con respuesta real, de esas las que se parecen)."""
    base = aciertos = 0
    for p, real in zip(pares, reales, strict=True):
        if p["salida"].via in ("persona", "silencio") or real is None:
            continue
        base += 1
        aciertos += parecido(p["salida"].texto, real) >= PARECIDO
    return base, aciertos


def _tiempo_hasta_cotizacion(espacio: Espacio) -> list[int]:
    tiempos = []
    for mensajes in historial.hilos(espacio).values():
        primero = next((m for m in mensajes if not m.del_negocio), None)
        cot = next((m for m in mensajes if m.del_negocio and guardia.trae_dinero(m.texto)), None)
        if primero and cot and cot.ts >= primero.ts:
            tiempos.append(cot.ts - primero.ts)
    return tiempos


def metricas(pares: list[dict], semilla: int = 11) -> dict:
    n = len(pares)
    reales = [p["real"].texto if p["real"] else None for p in pares]
    base, aciertos = _acierto(pares, reales)
    barajadas = reales[:]
    random.Random(semilla).shuffle(barajadas)
    base_p, aciertos_p = _acierto(pares, barajadas)
    contestadas = sum(p["salida"].via not in ("persona", "silencio") for p in pares)
    tiempos = [p["real"].ts - p["entrante"].ts for p in pares if p["real"]]
    return {
        "n": n,
        "concluye": n >= MINIMO,
        "cobertura": contestadas / n if n else None,
        "habria_enviado_sin_editar": aciertos / base if base else None,
        "con_respuesta_real": base,
        "placebo": aciertos_p / base_p if base_p else None,
        "errores_de_cifra": sum(error_de_cifra(p["salida"]) for p in pares),
        "callo": sum(p["salida"].via == "silencio" for p in pares),
        # Calló y la persona sí contestó: o el detector se equivocó o la persona contestó un acuse.
        "callo_y_la_persona_contesto": sum(p["salida"].via == "silencio" and p["real"] is not None for p in pares),
        "cotizaciones_esperando_aprobacion": sum(p["salida"].requiere_aprobacion for p in pares),
        "mediana_segundos_respuesta_persona": statistics.median(tiempos) if tiempos else None,
    }


def medir(espacio: Espacio, abrir_holdout: bool = False) -> dict:
    pares = _pares(espacio)
    corte = len(pares) - int(len(pares) * FRACCION_HOLDOUT)
    desarrollo, holdout = pares[:corte], pares[corte:]
    tiempos_cot = _tiempo_hasta_cotizacion(espacio)
    informe = {
        "desarrollo": metricas(desarrollo),
        "holdout": metricas(holdout) if abrir_holdout else {"n": len(holdout), "sellado": True},
        "mediana_segundos_hasta_cotizacion_persona": statistics.median(tiempos_cot) if tiempos_cot else None,
        "regla": f"n < {MINIMO} no concluye, ni a favor ni en contra",
    }
    if abrir_holdout:
        espacio.agregar_linea("vara_aperturas.jsonl", {"n_holdout": len(holdout)})
    return informe
