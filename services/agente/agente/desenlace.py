"""Qué pasó con cada ronda: la métrica que manda (Gestor, corrida 7: el tiempo al número).

Corrida GM del 2026-10-29: la ronda del 27-oct salió completa (128 de 128) y nadie
medía lo que vino después. Medido a mano: contestaron 26 de 138; una persona
contestó a 8 (mediana 0.8 h) y **18 seguían sin respuesta a las 26 h**. La
alineación con la casa no dice eso; esto sí.

Por ronda, contado sobre el historial (lo enviado entra con su id, D-046):

- `enviados`: salidas de la ronda, aprobadas, que están en el historial.
- `contestaron` (y `en_24h`): el cliente escribió después del envío.
- `cerraron`: lo primero que contestó es un cierre (*"ya tenemos opción"*).
- `no_piden`: contestó con un acuse o un aplazamiento (*"lo platico y le aviso"*),
  con la misma lectura que `pendientes`.
- `esperan_respuesta`: contestó algo que pide (o un audio o foto que alguien
  tiene que ver), y nadie del negocio le ha escrito
  después. Es el trabajo de hoy: el semáforo los pone primero (`contesto_ronda`).
- `atendidos` y `horas_a_persona` (mediana y p90): una persona contestó después
  de la respuesta del cliente, y en cuánto.
- `con_cifra`: después de la respuesta del cliente, la casa dio un monto.

n < 30 enviados no concluye. Sin red ni modelo; no sale del espacio.
"""
from __future__ import annotations

import re
import statistics
from collections import defaultdict

from . import conversacion, historial, jugadas
from .espacio import Espacio

_NOMBRE = re.compile(r"^ronda ([a-z0-9][a-z0-9-]{2,59}):")
MINIMO = 30


def nombre_de_ronda(motivo: str) -> str:
    m = _NOMBRE.match(motivo or "")
    return m.group(1) if m else "sin nombre"


def _p(valores: list[float], q: float) -> float | None:
    if not valores:
        return None
    orden = sorted(valores)
    return round(orden[min(len(orden) - 1, int(q * len(orden)))], 1)


def de_rondas(espacio: Espacio, hilos: dict | None = None) -> list[dict]:
    """Una fila por ronda, la más reciente primero."""
    from . import agente

    hilos = hilos if hilos is not None else historial.hilos(espacio)
    por_ronda: dict[str, list] = defaultdict(list)
    for s in agente.salidas(espacio):
        if s.via == "ronda" and s.aprobada_por and s.texto:
            por_ronda[nombre_de_ronda(s.motivo)].append(s)
    filas = []
    for nombre, salidas in por_ronda.items():
        c = defaultdict(int)
        horas: list[float] = []
        primero = None
        for s in salidas:
            ms = hilos.get(s.hilo, [])
            enviado = next((m for m in ms if m.del_negocio and (m.texto or "").strip() == s.texto.strip()), None)
            if enviado is None:
                continue
            c["enviados"] += 1
            primero = min(primero or enviado.ts, enviado.ts)
            despues = [m for m in ms if (m.ts, m.id) > (enviado.ts, enviado.id)]
            del_cliente = [m for m in despues if not m.del_negocio]
            if not del_cliente:
                continue
            r = del_cliente[0]
            c["contestaron"] += 1
            c["en_24h"] += r.ts - enviado.ts <= 86400
            negocio = [m for m in despues if m.del_negocio and m.ts >= r.ts]
            if negocio:   # lo primero que contestó, antes de que el negocio volviera a escribir
                k = despues.index(r)
                seguidos = []
                while k < len(despues) and not despues[k].del_negocio:
                    seguidos.append(despues[k])
                    k += 1
                rafaga = conversacion.rafaga(seguidos) or (r.texto or "")
            else:         # nadie le ha contestado: lo último que dejó (la misma vara que `pendientes`)
                rafaga = conversacion.rafaga(despues) or "\n".join(m.texto for m in del_cliente if m.texto)
            if conversacion.es_cierre(rafaga):
                c["cerraron"] += 1
                continue
            if rafaga.strip() and conversacion.nada_que_contestar(rafaga):
                c["no_piden"] += 1  # gracias, lo platico, le aviso
                continue
            if not negocio:
                c["esperan_respuesta"] += 1
                continue
            c["atendidos"] += 1
            horas.append((negocio[0].ts - r.ts) / 3600)
            c["con_cifra"] += any(jugadas.es_monto(m.texto or "") for m in negocio)
        if not c["enviados"]:
            continue
        filas.append({
            "ronda": nombre, "enviados": c["enviados"], "desde": primero,
            "contestaron": c["contestaron"], "en_24h": c["en_24h"],
            "pct_contestaron": round(100 * c["contestaron"] / c["enviados"], 1),
            "cerraron": c["cerraron"], "no_piden": c["no_piden"], "esperan_respuesta": c["esperan_respuesta"],
            "atendidos": c["atendidos"], "con_cifra": c["con_cifra"],
            "horas_a_persona": {"n": len(horas), "mediana": round(statistics.median(horas), 1) if horas else None,
                                "p90": _p(horas, 0.9)},
            "concluye": c["enviados"] >= MINIMO,
        })
    return sorted(filas, key=lambda f: -(f["desde"] or 0))


def linea(fila: dict) -> str:
    """Para el reporte de la mesa, sin teléfonos."""
    txt = (f"Ronda {fila['ronda']}: contestaron {fila['contestaron']} de {fila['enviados']}"
           f" (cerraron {fila['cerraron']}, sin pedir nada {fila['no_piden']}), esperan respuesta {fila['esperan_respuesta']}")
    if fila["horas_a_persona"]["n"]:
        txt += f", a los atendidos se les contestó en {fila['horas_a_persona']['mediana']} h (mediana)"
    return txt + "."
