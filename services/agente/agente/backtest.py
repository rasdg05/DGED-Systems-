"""El backtest: el agente de HOY contra los últimos 14 días reales, en cada despliegue.

Gestor, `app/services/backtest.py` (*"igual podría reportar backtests"*): si el
último despliegue empeoró al agente, se sabe el mismo día y no cuando un
cliente se queja. Aquí, sobre los mismos momentos:

· Corre `vara.simular` (el mismo código del turno, sin modelo: donde iría al
  modelo la jugada es `ia`) sobre los momentos de los últimos `DIAS` días del
  historial —contados desde el último mensaje, no desde el reloj—.
· Compara contra las predicciones del backtest anterior **en los mismos
  momentos**: cuántos mejoraron, cuántos empeoraron y la diferencia de puntaje.
· `regresion` = con n ≥ 30 momentos comunes, el puntaje cae más de
  `MARGEN_PUNTAJE`, la alineación por política cae más de `MARGEN_A_POL` puntos
  o suben los errores caros. n < 30 no concluye.

Lo que queda en el espacio: `vara/backtest.json` (los agregados, con el commit)
y `vara/backtest_predicciones.json` (id → jugada, para la siguiente vez). No
llama a ninguna IA ni manda nada.
"""
from __future__ import annotations

import logging
import os
import time
from collections import Counter
from datetime import datetime, timezone

from . import perfil, vara
from .espacio import Espacio

DIAS = 14
N_MINIMA = vara.MINIMO
MARGEN_PUNTAJE = 0.05
MARGEN_A_POL = 5.0
HORAS_ENTRE_BACKTESTS = 24
ESTADO = "vara/backtest.json"
PREDICCIONES = "vara/backtest_predicciones.json"


def commit() -> str:
    return (os.environ.get("RAILWAY_GIT_COMMIT_SHA") or os.environ.get("GIT_COMMIT") or "")[:7]


def leer(espacio: Espacio) -> dict:
    return espacio.leer_json(ESTADO, {}) or {}


def backtest(espacio: Espacio, dias: int = DIAS) -> tuple[dict, dict[str, dict]]:
    """(informe, predicciones de hoy por id de momento)."""
    _, moms = vara.universo(espacio)
    if not moms:
        return {"n": 0, "nota": "sin momentos"}, {}
    hasta = max(m["ts"] for m in moms)
    ventana = [m for m in moms if m["ts"] >= hasta - dias * 86400]
    activo = perfil.activo(espacio)
    por_id = vara.historial.por_id(espacio)
    for m in ventana:
        m.update(vara.simular(m["_m"], activo, por_id))
    vara.calificar(ventana)
    hoy = {m["id"]: {"bot": m["bot"], "via": m["via"], "texto": m.get("texto") or ""} for m in ventana}
    informe = {"n": len(ventana), "desde": vara._fecha(hasta - dias * 86400), "hasta": vara._fecha(hasta),
               "agente": vara.huella_del_agente(activo), "perfil_activo": perfil.version_activa(espacio),
               "clasificador": vara.jugadas.CLASIFICADOR_VERSION, "costos_version": vara.COSTOS_VERSION,
               "metricas": vara.metricas(ventana), "por_jugada": vara.por_jugada(ventana)[:10],
               "nota": "n < 30 no concluye" if len(ventana) < N_MINIMA else ""}
    antes = espacio.leer_json(PREDICCIONES, {}) or {}
    comunes = [m for m in ventana if m["id"] in antes]
    if comunes:
        previos = [{**m, **antes[m["id"]]} for m in comunes]
        vara.calificar(previos)
        ma, mh = vara.metricas(previos), vara.metricas(comunes)
        cambios = Counter()
        mejoraron = empeoraron = 0
        for a, h in zip(previos, comunes, strict=True):
            if h["score"] > a["score"]:
                mejoraron += 1
            elif h["score"] < a["score"]:
                empeoraron += 1
            if a["bot"] != h["bot"]:
                cambios[f'{h["casa"]}: {a["bot"]} → {h["bot"]}'] += 1
        informe["contra_el_anterior"] = {
            "n": len(comunes), "puntaje_antes": ma["puntaje"], "puntaje_hoy": mh["puntaje"],
            "A_pol_antes": ma["A_pol"], "A_pol_hoy": mh["A_pol"], "caros_antes": ma["errores_caros"],
            "caros_hoy": mh["errores_caros"], "mejoraron": mejoraron, "empeoraron": empeoraron,
            "cambios": cambios.most_common(8),
            "regresion": bool(len(comunes) >= N_MINIMA and (
                mh["puntaje"] < ma["puntaje"] - MARGEN_PUNTAJE or mh["A_pol"] < ma["A_pol"] - MARGEN_A_POL
                or mh["errores_caros"] > ma["errores_caros"])),
        }
    return informe, hoy


def correr(espacio: Espacio, motivo: str = "a mano") -> dict:
    informe, hoy = backtest(espacio)
    informe.update(fecha=datetime.now(timezone.utc).isoformat(timespec="seconds"), commit=commit(), motivo=motivo)
    estado = leer(espacio)
    estado["ultimo"] = informe
    estado["historial"] = (estado.get("historial", []) + [{
        k: informe.get(k) for k in ("fecha", "commit", "motivo", "n", "agente")} | {
        "puntaje": (informe.get("metricas") or {}).get("puntaje"),
        "regresion": (informe.get("contra_el_anterior") or {}).get("regresion", False)}])[-30:]
    espacio.escribir_json(ESTADO, estado)
    espacio.escribir_json(PREDICCIONES, hoy)
    return informe


def correr_si_toca(espacio: Espacio, ahora: float | None = None) -> dict | None:
    """Cuando cambia el commit (un despliegue) o pasaron 24 h. Nunca lanza."""
    ultimo = leer(espacio).get("ultimo") or {}
    try:
        if ultimo.get("commit") == commit() and ultimo.get("fecha") and (
                (ahora or time.time()) - datetime.fromisoformat(ultimo["fecha"]).timestamp()
                < HORAS_ENTRE_BACKTESTS * 3600):
            return None
        return correr(espacio, "despliegue nuevo" if ultimo.get("commit") != commit() else "diario")
    except Exception:                                   # noqa: BLE001 — el backtest no tumba el servicio
        logging.getLogger("backtest").exception("el backtest de %s falló", espacio.cliente_id)
        return None


def correr_todos(raiz=None) -> int:
    """Al arrancar el servicio (cada despliegue): un backtest por espacio con historial."""
    from .espacio import EspacioInvalido, raiz_por_defecto

    raiz = raiz or raiz_por_defecto()
    n = 0
    if not raiz.exists():
        return 0
    for carpeta in sorted(p for p in raiz.iterdir() if p.is_dir()):
        try:
            espacio = Espacio(carpeta.name, raiz)
        except EspacioInvalido:
            continue
        if espacio.existe("historial.jsonl") and correr_si_toca(espacio) is not None:
            n += 1
    return n
