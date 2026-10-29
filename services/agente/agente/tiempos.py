"""El tiempo al número: la métrica que manda en Gestor desde la corrida 7.

`gestor-morelos/app/services/tiempo_al_numero.py`: *"la cotización es el acto que
produce dinero"* y la restricción no es la demanda sino el tiempo hasta la
cotización. Aquí, por pedido:

- Un **pedido** empieza cuando el cliente pide precio (`lectura.pide_precio`) en
  una plática que no tenía uno abierto; 14 días sin mensajes abren otro.
- Termina en la **primera cifra de la casa** después (`jugadas.es_monto`).
- Las tarifas de Finca Emiliano viajan en **imágenes** (5,421 de 11,463 mensajes): un
  pedido sin cifra escrita pero con una imagen de la casa después cuenta aparte
  (`con_imagen`, el precio pudo ir en la foto: no se sabe), no como "sin número".
- Lo que nunca recibió número **no se tira** (censura): cuenta en `sin_numero`, y
  la mediana se da junto con cuántos estaban abiertos al cortar. Un pedido de las
  últimas 24 h todavía no puede llevar "nunca": va en `abiertos`.

Por semana (lunes, hora de México) de cuando se pidió. n < 30 no concluye. Sin
red ni modelo; solo agregados, sin teléfonos.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import jugadas, lectura
from .historial import Mensaje

ZONA = ZoneInfo("America/Mexico_City")
DIAS_NUEVO_PEDIDO = 14
HORAS_ABIERTO = 24
MINIMO = 30


def pedidos(hilos: dict[str, list[Mensaje]], ahora_ts: int | None = None) -> list[dict]:
    """Un renglón por pedido: cuándo, si recibió número y en cuántas horas."""
    ahora_ts = ahora_ts if ahora_ts is not None else max(
        (m.ts for ms in hilos.values() for m in ms), default=0)
    salida = []
    for ms in hilos.values():
        abierto = None
        ultimo_ts = None
        for m in ms:
            if ultimo_ts is not None and m.ts - ultimo_ts > DIAS_NUEVO_PEDIDO * 86400 and abierto is not None:
                salida.append(abierto)
                abierto = None
            ultimo_ts = m.ts
            if not m.del_negocio and m.texto and abierto is None and lectura.pide_precio(m.texto):
                abierto = {"ts": m.ts, "horas": None, "imagen": False}
            elif m.del_negocio and abierto is not None and m.tipo in jugadas.MEDIOS_QUE_ENSENAN:
                abierto["imagen"] = True
            elif m.del_negocio and m.texto and abierto is not None and jugadas.es_monto(m.texto):
                abierto["horas"] = round((m.ts - abierto["ts"]) / 3600, 2)
                salida.append(abierto)
                abierto = None
        if abierto is not None:
            salida.append(abierto)
    for p in salida:
        p["abierto"] = p["horas"] is None and ahora_ts - p["ts"] < HORAS_ABIERTO * 3600
    return salida


def _semana(ts: int) -> str:
    d = datetime.fromtimestamp(ts, ZONA).date()
    return (d - timedelta(days=d.weekday())).isoformat()


def _p(valores: list[float], q: float) -> float | None:
    if not valores:
        return None
    orden = sorted(valores)
    return round(orden[min(len(orden) - 1, int(q * len(orden)))], 1)


def resumen(lista: list[dict]) -> dict:
    con = [p["horas"] for p in lista if p["horas"] is not None]
    cerrados = [p for p in lista if not p["abierto"]]
    return {"pedidos": len(lista), "con_numero": len(con), "abiertos": sum(p["abierto"] for p in lista),
            "con_imagen": sum(p["horas"] is None and not p["abierto"] and p["imagen"] for p in lista),
            "sin_numero": sum(p["horas"] is None and not p["abierto"] and not p["imagen"] for p in lista),
            "en_1h": sum(h <= 1 for h in con), "en_24h": sum(h <= 24 for h in con),
            "pct_en_24h": round(100 * sum(h <= 24 for h in con) / len(cerrados), 1) if cerrados else None,
            "mediana_h": round(statistics.median(con), 2) if con else None, "p90_h": _p(con, 0.9),
            "concluye": len(cerrados) >= MINIMO}


def al_numero(hilos: dict[str, list[Mensaje]], semanas: int = 8, ahora_ts: int | None = None) -> dict:
    lista = pedidos(hilos, ahora_ts)
    por = {}
    for p in lista:
        por.setdefault(_semana(p["ts"]), []).append(p)
    claves = sorted(por)[-semanas:]
    return {"total": resumen(lista), "por_semana": [{"semana": k, **resumen(por[k])} for k in claves]}


def linea(r: dict) -> str:
    """Para el reporte de la mesa: la semana en curso, o la última con pedidos."""
    if not r["por_semana"]:
        return ""
    s = r["por_semana"][-1]
    txt = (f"Pidieron precio (semana del {s['semana'][8:10]}/{s['semana'][5:7]}): {s['pedidos']}; "
           f"con número {s['con_numero']}")
    if s["mediana_h"] is not None:
        txt += f" (mediana {s['mediana_h']} h)"
    return txt + f", sin número {s['sin_numero']}" + (f", con foto {s['con_imagen']}" if s["con_imagen"] else "") + "."
