"""La vara: el agente de hoy contra TODOS los momentos reales del negocio.

    cd services/agente
    python -m agente.vara medir finca-quinta --variante base                 # desarrollo
    python -m agente.vara medir finca-quinta --variante p1 --perfil p.json --contra base
    python -m agente.vara medir finca-quinta --variante p1 --perfil p.json --contra base --abrir-holdout

Es `herramientas/vara.py` de Gestor Morelos (que es la de fq-bot) llevada al
agente a la medida; se copiaron los métodos, no el giro. Lo que hace y por qué:

· **Momentos**: cada respuesta de una persona del negocio a un cliente
  (`jugadas.momentos`), con la jugada de la casa del clasificador de HOY.
· **El agente sobre cada momento**: `agente.antes_del_modelo`, el mismo código
  del turno, con el hilo cortado justo antes de la respuesta (sin reloj de
  pared). Donde iría al modelo, la jugada es `ia`: **la vara no llama a nada**.
· **Holdout sellado out-of-time**: el 25% más nuevo de los momentos. Nadie lo
  lee al escribir reglas ni perfil; se abre con `--abrir-holdout`, **una vez por
  candidato**, y la apertura queda en la bitácora. Un perfil que cita mensajes
  del holdout o del embargo no lo abre.
· **Desarrollo purgado**: lo anterior al corte menos un embargo de 7 días, y
  sin los hilos que también están en el holdout (fuga por plática).
· **CPCV** 6 grupos, 2 de prueba = 15 caminos; **placebo** (la jugada de la casa
  barajada: la alineación debe caer al azar, y con un agente constante NO cae:
  ahí la vara dice que la alineación no es habilidad); **puntaje con `COSTOS`**
  versionado; **DSR** del delta por hilo deflactado por los intentos; **PBO** por
  CSCV entre intentos; **libro sellado** (hash de las predicciones antes de
  calificarlas).
· **Bitácora** `vara/intentos.jsonl`, en git: solo agregados (hashes, n,
  métricas). Ningún teléfono, ningún texto (test). Las predicciones viven en el
  espacio local (`datos/espacios/<id>/vara/`), fuera de git.

n < 30 no concluye, ni a favor ni en contra.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import agente, conversacion, guardia, historial, jugadas, perfil
from .espacio import Espacio

AQUI = Path(__file__).resolve().parent
BITACORA = AQUI.parent / "vara" / "intentos.jsonl"
VARIABLE_BITACORA = "AGENTE_VARA_BITACORA"

#: La tabla de costos. **Se escribe una vez, antes de medir, y se versiona**:
#: cambiarla es un intento más (Gestor, plan §3).
#: v2 (2026-10-27): callar es caro solo si el CLIENTE preguntó; si la casa tomó
#: la iniciativa tras un *"Ok"*, callar es la política (el acuse calla).
COSTOS_VERSION = 2
#: v2: el perfil se purga por plática al simular (una guardada citada de la misma
#: plática es la respuesta del examen).
VARA_VERSION = 2
COSTOS = {
    "igual": 1.0,              # la misma jugada que la casa
    "politica_activa": 0.6,    # otra jugada activa que la política da por buena (confirma por acuse)
    "politica_pasa": 0.3,      # se lo pasa a una persona donde la política lo acepta
    "politica_silencio": 0.3,  # calla donde la política lo acepta (acuse, saludo)
    "neutra": 0.0,             # otra cosa, sin daño
    "caro": -1.0,              # calla cuando el cliente preguntó algo
    "grave": -2.0,             # una cifra que no puso el cotizador, o dice ser una persona
}
#: Qué más, además de la misma jugada, da por bueno la política de hoy (sin
#: perfil de cotización aprobado, XXXIII: la cifra espera a una persona).
_PASA = frozenset({"persona", "espera"})
POLITICA: dict[str, frozenset[str]] = {
    **{j: _PASA for j in jugadas.JUGADAS},
    "acuse": frozenset({"silencio", "persona", "saludo"}),
    "saludo": frozenset({"silencio", "persona", "acuse"}),
    "confirma": frozenset({"persona", "espera", "acuse"}),
}
#: Las jugadas de la casa donde a la política le basta pasarlo o callar: ahí la
#: cobertura no mide nada.
PASA_A_PERSONA = frozenset({"cifra", "disponibilidad", "anticipo", "fotos", "visita", "espera", "otra",
                            "pide:otra", "confirma"})
#: Callar aquí es un error caro: el cliente pidió algo con contenido.
CON_CONTENIDO = frozenset(j for j in jugadas.JUGADAS if j not in ("acuse", "saludo", "medio", "otra"))

MINIMO = 30
EMBARGO_DIAS = 7
FRACCION_HOLDOUT = 0.25
GRUPOS_CPCV = 6
BLOQUES_PBO = 8
HORAS_CONTESTA = 24
DIAS_AVANZA = 7
#: El código que decide: si cambia, cambia el agente medido. La vara no está:
#: editar la regla de medir no hace a un candidato nuevo (ni le reabre el holdout).
MODULOS_DEL_AGENTE = ("agente.py", "conversacion.py", "respuestas.py", "guardia.py", "jugadas.py", "voz.py")


class HoldoutYaAbierto(RuntimeError):
    """El holdout se abre una vez por candidato."""


class PerfilMiraElHoldout(RuntimeError):
    """El perfil cita mensajes del holdout o del embargo: el holdout ya no está sellado para él."""


# --------------------------------------------------------------------------- #
#  Huellas                                                                     #
# --------------------------------------------------------------------------- #
def _sha(*partes: bytes) -> str:
    h = hashlib.sha256()
    for p in partes:
        h.update(p)
    return h.hexdigest()


def huella_del_universo(hilos: dict[str, list[historial.Mensaje]]) -> str:
    h = hashlib.sha256()
    for k in sorted(hilos):
        ms = hilos[k]
        h.update(k.encode())
        h.update(str(len(ms)).encode())
        h.update(str(ms[-1].ts if ms else 0).encode())
    return h.hexdigest()[:16]


def huella_del_agente(activo: dict | None) -> str:
    codigo = b"".join((AQUI / f).read_bytes() for f in MODULOS_DEL_AGENTE)
    datos = json.dumps(activo, ensure_ascii=False, sort_keys=True).encode()
    return _sha(codigo, datos)[:16]


def huella_del_perfil(activo: dict | None) -> str:
    return _sha(json.dumps(activo, ensure_ascii=False, sort_keys=True).encode())[:16]


def _commit() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=AQUI, text=True,
                                      stderr=subprocess.DEVNULL).strip()
        sucio = subprocess.call(["git", "diff", "--quiet", "HEAD", "--", str(AQUI)], cwd=AQUI)
        return sha + ("+" if sucio else "")
    except (OSError, subprocess.CalledProcessError):
        return "?"


# --------------------------------------------------------------------------- #
#  El agente sobre cada momento                                                #
# --------------------------------------------------------------------------- #
def redactado(m: dict, borrador: dict, activo: dict | None) -> dict:
    """Donde el agente iría al modelo y el enjambre redactó: el borrador pasa por
    los mismos candados del turno (`agente.candados`). Si pide cotizar, hoy va a
    una persona: el cotizador no tiene con qué (`corpus.faltaba_al_cotizar`)."""
    texto = "\n".join(t.strip() for t in borrador.get("textos") or [] if t and t.strip())
    if borrador.get("silencio") and not texto and not borrador.get("persona"):
        return {"bot": "silencio", "via": "silencio", "motivo": "el enjambre calló", "texto": ""}
    meta = {"persona": "si" if borrador.get("persona") else "no", "duda": borrador.get("duda") or ""}
    base = {"cliente_id": "vara", "hilo": "", "responde_a": m["id"]}
    detenida = agente.candados(base, texto, meta, activo or {})
    if detenida is not None:
        return {"bot": "persona", "via": "persona", "motivo": "candado: " + detenida.motivo, "texto": "",
                "detenido": not borrador.get("persona")}
    if borrador.get("cotizar"):
        return {"bot": "persona", "via": "persona", "motivo": "cotizar: el cotizador no tiene con qué", "texto": ""}
    return {"bot": jugadas.jugada(texto), "via": "modelo", "motivo": "redactó el enjambre", "texto": texto}


def jugada_del_agente(salida: agente.Salida | None) -> str:
    if salida is None:
        return "ia"
    if salida.via in ("persona", "silencio"):
        return salida.via
    if salida.via == "regla":
        return "soy_asistente"
    return jugadas.jugada(salida.texto)


def sin_la_platica(activo: dict | None, hilo: str, por_id: dict[str, historial.Mensaje]) -> dict | None:
    """El perfil sin los renglones citados de ESTA plática: al medirla, una
    respuesta guardada que salió de ella es la respuesta del examen."""
    if not activo:
        return activo

    def de_aqui(r: dict) -> bool:
        o = r.get("origen") or {}
        return o.get("tipo") == "mensaje" and o.get("id") in por_id and por_id[o["id"]].hilo == hilo

    return {k: ([r for r in v if not de_aqui(r)] if k in perfil.SECCIONES and isinstance(v, list) else v)
            for k, v in activo.items()}


def simular(m: jugadas.Momento, activo: dict | None, por_id: dict | None = None) -> dict:
    """Lo que el agente de hoy habría hecho en ese momento, sin llamar a nada.
    Con `por_id`, el perfil se purga de la plática del momento."""
    if por_id is not None:
        activo = sin_la_platica(activo, m.hilo, por_id)
    hilo = [x for x in m.prefijo if (x.ts, x.id) <= (m.entrante.ts, m.entrante.id)]
    base = {"cliente_id": "vara", "hilo": "", "responde_a": m.entrante.id}
    salida = agente.antes_del_modelo(base, m.entrante, hilo, activo)
    return {"bot": jugada_del_agente(salida), "via": salida.via if salida else "ia",
            "motivo": salida.motivo if salida else "iría al modelo",
            "texto": (salida.texto if salida and salida.via in ("guardada", "regla") else "")}


def rasgos(m: jugadas.Momento, fijas: set[str]) -> dict:
    """`atendia`: en vivo, una persona escribió en las últimas 24 h y el agente
    estaría callado (Gestor: `fiel`; la misma función del turno real).
    `tras_cifra`: la casa ya había dado número."""
    hilo = [x for x in m.prefijo if (x.ts, x.id) <= (m.entrante.ts, m.entrante.id)]
    atendia = agente.lo_lleva_una_persona(hilo, m.entrante, fijas)
    tras_cifra = any(x.del_negocio and jugadas.es_monto(x.texto or "") for x in m.prefijo)
    return {"atendia": "persona" if atendia else "agente", "tras_cifra": tras_cifra}


def desenlace(m: jugadas.Momento, hilo_completo: list[historial.Mensaje]) -> str:
    """Triple barrera (fq-bot, `bt_labeler`): `avanzo` (en 7 días la casa llegó a
    su primera cifra tras una respuesta del cliente, o tras la cifra el cliente
    dijo que sí o la casa pidió el anticipo), `contesto` (escribió en 24 h) o
    `silencio`. La primera barrera que se toca gana."""
    ultimo = max(x.ts for x in m.tanda)
    ya_habia = any(x.del_negocio and jugadas.es_monto(x.texto or "") for x in list(m.prefijo) + list(m.tanda))
    contesto, respondio = False, False
    for x in hilo_completo:
        if x.ts <= ultimo or x.id in {t.id for t in m.tanda}:
            continue
        dt = x.ts - m.ts
        if dt > DIAS_AVANZA * 86400:
            break
        if not x.del_negocio:
            respondio = True
            contesto = contesto or dt <= HORAS_CONTESTA * 3600
            if ya_habia and conversacion.senal_tras_la_cotizacion([x.texto or ""]) == "acepta":
                return "avanzo"
        elif respondio and x.texto:
            j = jugadas.jugada(x.texto)
            if (not ya_habia and j == "cifra") or (ya_habia and j == "anticipo"):
                return "avanzo"
    return "contesto" if contesto else "silencio"


# --------------------------------------------------------------------------- #
#  El puntaje                                                                  #
# --------------------------------------------------------------------------- #
#: El juez de "el cliente pidió algo", independiente de los detectores del agente
#: (si el agente se calificara con su propio `nada_que_contestar`, nunca fallaría).
_PIDE = re.compile(r"\b(?:cuanto|cuanta|cuantas|cuantos|donde|como|cuando|que|cual|tienen|tiene|hay|se puede|"
                   r"puedo|podemos|aceptan|incluye|me (?:pasa|pasas|manda|mandas|envia|envias|das|da|puede)|"
                   r"quiero|quisiera|necesito|informacion|precio|costo|disponib\w*)\b")


def cliente_pide(cliente: str) -> bool:
    return "?" in cliente or "¿" in cliente or bool(_PIDE.search(conversacion.normalizar(cliente)))


def coincide(casa: str, bot: str, politica: bool = True) -> bool:
    return casa == bot or (politica and bot in POLITICA.get(casa, _PASA))


def puntaje(m: dict) -> tuple[float, str]:
    """El "retorno" de lo que el agente hizo ahí."""
    casa, bot, texto = m["casa"], m["bot"], m.get("texto") or ""
    if texto and guardia.trae_dinero(texto):
        return COSTOS["grave"], "cifra"
    if texto and guardia.dice_ser_persona(texto):
        return COSTOS["grave"], "dice_ser_persona"
    if casa == bot:
        return COSTOS["igual"], "igual"
    if coincide(casa, bot):
        if bot == "silencio":
            return COSTOS["politica_silencio"], "politica_silencio"
        if bot in _PASA:
            return COSTOS["politica_pasa"], "politica_pasa"
        return COSTOS["politica_activa"], "politica_activa"
    if bot == "silencio" and casa in CON_CONTENIDO and cliente_pide(m.get("cliente") or ""):
        return COSTOS["caro"], "calla_cuando_pedian"
    return COSTOS["neutra"], "neutra"


def calificar(moms: list[dict]) -> None:
    for m in moms:
        m["lit"] = coincide(m["casa"], m["bot"], politica=False)
        m["pol"] = coincide(m["casa"], m["bot"])
        m["actua"] = m["bot"] not in jugadas.NO_ACTUA
        m["score"], m["porque"] = puntaje(m)


# --------------------------------------------------------------------------- #
#  Particiones                                                                 #
# --------------------------------------------------------------------------- #
def corte_de(moms: list[dict]) -> int:
    ts = sorted(m["ts"] for m in moms)
    return ts[int(len(ts) * (1 - FRACCION_HOLDOUT))] if ts else 0


def partir(moms: list[dict]) -> tuple[list[dict], list[dict], dict]:
    """Holdout = el 25% más nuevo. Desarrollo = lo anterior al corte menos el
    embargo, sin los hilos del holdout."""
    corte = corte_de(moms)
    holdout = [m for m in moms if m["ts"] >= corte]
    del_holdout = {m["hilo"] for m in holdout}
    limite = corte - EMBARGO_DIAS * 86400
    dev = [m for m in moms if m["ts"] < limite and m["hilo"] not in del_holdout]
    return dev, holdout, {"corte": _fecha(corte), "limite_desarrollo": _fecha(limite),
                          "embargo_dias": EMBARGO_DIAS, "purgados": len(moms) - len(holdout) - len(dev)}


def _fecha(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).date().isoformat()


def citas_del_perfil(activo: dict | None) -> set[str]:
    """Los ids de mensaje que el perfil cita."""
    return {r["origen"]["id"] for s in perfil.SECCIONES for r in (activo or {}).get(s, []) or []
            if isinstance(r.get("origen"), dict) and r["origen"].get("tipo") == "mensaje" and r["origen"].get("id")}


def perfil_mira_el_holdout(activo: dict | None, por_id: dict[str, historial.Mensaje], limite_ts: int,
                           hilos_holdout: set[str] = frozenset()) -> list[str]:
    """Los ids citados que caen en el embargo o en el holdout, o en un hilo que
    también está en el holdout (la misma purga por plática que el desarrollo)."""
    return sorted(i for i in citas_del_perfil(activo)
                  if i not in por_id or por_id[i].ts >= limite_ts or por_id[i].hilo in hilos_holdout)


def material_de_desarrollo(espacio: Espacio) -> list[historial.Mensaje]:
    """Lo que el perfil (o el enjambre) puede leer sin mirar el holdout: mensajes
    anteriores al límite del desarrollo y de hilos que no están en el holdout."""
    _, moms = universo(espacio)
    _, holdout, _ = partir(moms)
    limite = corte_de(moms) - EMBARGO_DIAS * 86400
    fuera = {m["hilo"] for m in holdout}
    return [m for m in historial.cargar(espacio) if m.ts < limite and m.hilo not in fuera]


# --------------------------------------------------------------------------- #
#  Métricas                                                                    #
# --------------------------------------------------------------------------- #
def _pct(x: float) -> float:
    return round(100 * x, 1)


def metricas(moms: list[dict]) -> dict:
    n = len(moms)
    if not n:
        return {"n": 0}
    caros = Counter(m["porque"] for m in moms if m["score"] < 0)
    fiel = [m for m in moms if m.get("atendia") == "agente"]
    toca = [m for m in moms if m["casa"] not in PASA_A_PERSONA]
    return {
        "n": n, "hilos": len({m["hilo"] for m in moms}), "concluye": n >= MINIMO,
        "A_lit": _pct(sum(m["lit"] for m in moms) / n),
        "A_pol": _pct(sum(m["pol"] for m in moms) / n),
        "cobertura": _pct(sum(m["actua"] for m in moms) / n),
        "a_la_ia": _pct(sum(m["bot"] == "ia" for m in moms) / n),
        "puntaje": round(sum(m["score"] for m in moms) / n, 4),
        "errores_caros": sum(caros.values()), "por_error": dict(caros),
        "fiel": {"n": len(fiel),
                 "A_pol": _pct(sum(m["pol"] for m in fiel) / len(fiel)) if fiel else None,
                 "cobertura": _pct(sum(m["actua"] for m in fiel) / len(fiel)) if fiel else None},
        "cobertura_donde_toca": _pct(sum(m["actua"] for m in toca) / len(toca)) if toca else None,
    }


def por_jugada(moms: list[dict]) -> list[dict]:
    grupos = defaultdict(list)
    for m in moms:
        grupos[m["casa"]].append(m)
    return sorted(({"casa": k, "n": len(v), "concluye": len(v) >= MINIMO,
                    "A_pol": _pct(sum(x["pol"] for x in v) / len(v)),
                    "cobertura": _pct(sum(x["actua"] for x in v) / len(v)),
                    "puntaje": round(sum(x["score"] for x in v) / len(v), 3),
                    "perdida": round(sum(COSTOS["igual"] - x["score"] for x in v), 1),
                    "bot": dict(Counter(x["bot"] for x in v).most_common(4))}
                   for k, v in grupos.items()), key=lambda r: -r["perdida"])


def por_desenlace(moms: list[dict]) -> dict:
    """¿Con qué jugada gana la casa? (F4 del plan de Gestor)."""
    salida = {d: sum(m["desenlace"] == d for m in moms) for d in ("avanzo", "contesto", "silencio")}
    por = defaultdict(Counter)
    for m in moms:
        por[m["casa"]][m["desenlace"]] += 1
    salida["la_casa_gana_con"] = sorted(
        ({"casa": k, "n": sum(c.values()), "concluye": sum(c.values()) >= MINIMO,
          "contesta_o_avanza": _pct((c["avanzo"] + c["contesto"]) / sum(c.values())),
          "avanza": _pct(c["avanzo"] / sum(c.values()))} for k, c in por.items()),
        key=lambda r: (-r["concluye"], -r["contesta_o_avanza"]))
    return salida


def ic_bootstrap(moms: list[dict], clave: str = "pol", veces: int = 1000, semilla: int = 7) -> tuple:
    """IC95% por hilo (se remuestrean pláticas, no momentos)."""
    por = defaultdict(list)
    for m in moms:
        por[m["hilo"]].append(float(m[clave]))
    hilos = list(por)
    if not hilos:
        return (None, None)
    rnd = random.Random(semilla)
    valores = []
    for _ in range(veces):
        tomados = [rnd.choice(hilos) for _ in hilos]
        valores.append(sum(sum(por[h]) for h in tomados) / sum(len(por[h]) for h in tomados))
    valores.sort()
    escala = 100 if clave in ("pol", "lit", "actua") else 1
    return (round(escala * valores[int(0.025 * veces)], 3), round(escala * valores[int(0.975 * veces) - 1], 3))


def placebo(moms: list[dict], veces: int = 50, semilla: int = 11, bot: str = "bot") -> dict:
    """La jugada de la casa barajada: si la alineación no cae, no es habilidad."""
    rnd = random.Random(semilla)
    casas = [m["casa"] for m in moms]
    valores = []
    for _ in range(veces):
        rnd.shuffle(casas)
        valores.append(sum(coincide(c, m[bot]) for c, m in zip(casas, moms, strict=True)) / max(1, len(moms)))
    real = sum(coincide(m["casa"], m[bot]) for m in moms) / max(1, len(moms))
    media = statistics.mean(valores) if valores else 0.0
    return {"A_pol_real": _pct(real), "A_pol_placebo": _pct(media), "colapsa": bool(real - media >= 0.05)}


def cpcv(moms: list[dict], grupos: int = GRUPOS_CPCV, prueba: int = 2) -> dict:
    """Combinatorial purged CV: grupos cronológicos, `prueba` de prueba → la distribución."""
    if len(moms) < grupos * 5:
        return {"caminos": 0}
    tam = len(moms) // grupos
    bloques = [moms[k * tam:(k + 1) * tam if k < grupos - 1 else len(moms)] for k in range(grupos)]
    pol, pun = [], []
    for combo in itertools.combinations(range(grupos), prueba):
        sel = [m for k in combo for m in bloques[k]]
        pol.append(100 * sum(m["pol"] for m in sel) / len(sel))
        pun.append(sum(m["score"] for m in sel) / len(sel))
    return {"caminos": len(pol), "A_pol_media": round(statistics.mean(pol), 1), "A_pol_min": round(min(pol), 1),
            "A_pol_max": round(max(pol), 1), "puntaje_media": round(statistics.mean(pun), 4),
            "puntaje_min": round(min(pun), 4), "puntaje_max": round(max(pun), 4)}


def por_bloque(moms: list[dict], bloques: int = BLOQUES_PBO) -> list[float]:
    if len(moms) < bloques:
        return []
    tam = len(moms) // bloques
    return [round(statistics.mean(m["score"] for m in moms[k * tam:(k + 1) * tam if k < bloques - 1 else None]), 4)
            for k in range(bloques)]


# --------------------------------------------------------------------------- #
#  DSR y PBO (Bailey y López de Prado)                                         #
# --------------------------------------------------------------------------- #
def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _phi_inv(p: float) -> float:
    """Inversa de la normal por bisección: sobra para 1/N con N ≤ miles."""
    lo, hi = -10.0, 10.0
    for _ in range(100):
        medio = (lo + hi) / 2
        if _phi(medio) < p:
            lo = medio
        else:
            hi = medio
    return (lo + hi) / 2


def dsr(deltas: list[float], n_intentos: int, var_sr: float | None = None) -> dict:
    """Deflated Sharpe Ratio del delta de puntaje por hilo."""
    n = len(deltas)
    if n < 3:
        return {"n": n, "dsr": None}
    media = statistics.mean(deltas)
    desv = statistics.pstdev(deltas)
    if desv == 0:
        return {"n": n, "sr": None, "dsr": 1.0 if media > 0 else 0.0, "nota": "sin varianza"}
    sr = media / desv
    g3 = sum((x - media) ** 3 for x in deltas) / n / desv ** 3
    g4 = sum((x - media) ** 4 for x in deltas) / n / desv ** 4
    var_sr = var_sr or 1.0 / n
    N = max(1, n_intentos)
    gamma = 0.5772156649
    sr0 = (math.sqrt(var_sr) * ((1 - gamma) * _phi_inv(1 - 1 / N) + gamma * _phi_inv(1 - 1 / (N * math.e)))
           if N > 1 else 0.0)
    den = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
    return {"n": n, "delta_medio": round(media, 4), "sr": round(sr, 4),
            "psr": round(_phi(sr * math.sqrt(n - 1) / den), 4), "sr0": round(sr0, 4), "intentos": N,
            "dsr": round(_phi((sr - sr0) * math.sqrt(n - 1) / den), 4)}


def pbo(matriz: list[list[float]]) -> dict:
    """Probability of Backtest Overfitting por CSCV. `matriz[intento][bloque]`."""
    filas = [r for r in matriz if r]
    if len(filas) < 2:
        return {"pbo": None, "nota": "hace falta más de un intento"}
    S = min(len(r) for r in filas)
    S -= S % 2
    if len({tuple(r[:S]) for r in filas}) < 2:
        return {"pbo": None, "nota": "los intentos puntúan igual en cada bloque: no hay elección que sobreajustar"}
    if S < 2:
        return {"pbo": None}
    logits = []
    for dentro in itertools.combinations(range(S), S // 2):
        fuera = [k for k in range(S) if k not in dentro]
        rend_in = [statistics.mean(r[k] for k in dentro) for r in filas]
        rend_out = [statistics.mean(r[k] for k in fuera) for r in filas]
        mejor = max(range(len(filas)), key=lambda t: rend_in[t])
        w = (sorted(rend_out).index(rend_out[mejor]) + 1) / (len(filas) + 1)
        logits.append(math.log(w / (1 - w)))
    return {"pbo": round(sum(x <= 0 for x in logits) / len(logits), 3), "combinaciones": len(logits),
            "intentos": len(filas)}


# --------------------------------------------------------------------------- #
#  Bitácora y libro sellado                                                    #
# --------------------------------------------------------------------------- #
def ruta_bitacora() -> Path:
    return Path(os.environ.get(VARIABLE_BITACORA, "").strip() or BITACORA)


def leer_intentos(cliente_id: str, universo: str | None = None) -> list[dict]:
    """Los intentos sobre el MISMO universo, clasificador y costos: con otro, los
    puntajes no se comparan (ni DSR ni PBO)."""
    ruta = ruta_bitacora()
    if not ruta.exists():
        return []
    filas = [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip()]
    return [f for f in filas if f.get("cliente_id") == cliente_id
            and (universo is None or f.get("universo") == universo)
            and f.get("clasificador") == jugadas.CLASIFICADOR_VERSION
            and f.get("costos_version") == COSTOS_VERSION]


def sellar(moms: list[dict], destino: Path) -> str:
    """Las predicciones del agente, escritas y con hash ANTES de calificarlas."""
    lineas = [json.dumps({"id": m["id"], "bot": m["bot"], "via": m["via"], "texto": m.get("texto") or ""},
                         ensure_ascii=False, sort_keys=True) for m in sorted(moms, key=lambda x: x["id"])]
    cuerpo = "\n".join(lineas) + "\n"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(cuerpo, encoding="utf-8")
    return hashlib.sha256(cuerpo.encode()).hexdigest()


# --------------------------------------------------------------------------- #
#  La corrida                                                                  #
# --------------------------------------------------------------------------- #
def universo(espacio: Espacio) -> tuple[dict, list[dict]]:
    """Los momentos como diccionarios (lo que la vara califica)."""
    hilos = historial.hilos(espacio)
    fijas = jugadas.plantillas(hilos)
    salida = []
    for m in jugadas.momentos(hilos):
        salida.append({"id": m.id, "hilo": m.hilo, "ts": m.ts, "casa": m.casa, "cliente": m.cliente,
                       "desenlace": desenlace(m, hilos[m.hilo]), **rasgos(m, fijas), "_m": m})
    return hilos, salida


def medir(espacio: Espacio, variante: str, *, activo: dict | None = None, contra: str | None = None,
          abrir_holdout: bool = False, registrar: bool = True, descripcion: str = "",
          redacciones: dict[str, dict] | None = None) -> dict:
    hilos, moms = universo(espacio)
    huella_u = huella_del_universo(hilos)
    previos = leer_intentos(espacio.cliente_id, huella_u)
    dev, holdout, particion = partir(moms)
    limite_ts = corte_de(moms) - EMBARGO_DIAS * 86400
    mira = perfil_mira_el_holdout(activo, historial.por_id(espacio), limite_ts, {m["hilo"] for m in holdout})
    bot = huella_del_agente(activo)
    if abrir_holdout:
        if mira:
            raise PerfilMiraElHoldout(f"el perfil cita {len(mira)} mensajes del embargo o del holdout")
        if any(f.get("holdout_abierto") and f.get("bot") == bot for f in previos):
            raise HoldoutYaAbierto(f"el holdout ya se abrió para este agente ({bot})")
    por_id = historial.por_id(espacio)
    for m in moms:
        m.update(simular(m["_m"], activo, por_id))
        if redacciones and m["bot"] == "ia" and m["id"] in redacciones:
            m.update(redactado(m, redacciones[m["id"]], sin_la_platica(activo, m["hilo"], por_id)), redactado_=True)
    if redacciones and set(redacciones) - {m["id"] for m in dev}:
        raise PerfilMiraElHoldout("hay redacciones fuera del desarrollo (embargo, holdout o plática purgada)")
    sello = sellar(moms, espacio.ruta(f"vara/predicciones_{variante}.jsonl"))
    calificar(moms)
    # El oráculo (el agente que hace lo mismo que la casa): con él el placebo SÍ
    # debe caer. Si no cae, la vara no distingue nada.
    for m in moms:
        m["oraculo"] = m["casa"]
    informe = {
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cliente_id": espacio.cliente_id, "variante": variante, "descripcion": descripcion,
        "commit": _commit(), "bot": bot, "universo": huella_u, "clasificador": jugadas.CLASIFICADOR_VERSION,
        "costos_version": COSTOS_VERSION, "vara_version": VARA_VERSION, "sello": sello,
        "particion": {**particion, "n_total": len(moms), "n_dev": len(dev), "n_holdout": len(holdout)},
        "perfil": {"renglones": sum(len((activo or {}).get(s, []) or []) for s in perfil.SECCIONES),
                   "citas_en_embargo_u_holdout": len(mira), "huella": huella_del_perfil(activo),
                   "aperturas_previas": sum(1 for f in previos if f.get("holdout_abierto")
                                            and (f.get("perfil") or {}).get("huella") == huella_del_perfil(activo))},
        "total": metricas(moms),
        "dev": {**metricas(dev), "IC95_A_pol": ic_bootstrap(dev), "IC95_puntaje": ic_bootstrap(dev, "score")},
        "cpcv": cpcv(dev), "placebo": placebo(dev), "placebo_oraculo": placebo(dev, bot="oraculo"),
        "desenlace_dev": por_desenlace(dev), "por_jugada_dev": por_jugada(dev), "por_bloque": por_bloque(dev),
    }
    if redacciones:
        sub = [m for m in dev if m.get("redactado_")]
        informe["redactados"] = {**metricas(sub), "por_jugada": por_jugada(sub),
                                 "detenidos_por_candado": sum(bool(m.get("detenido")) for m in sub)}
    if contra:
        base = next((f for f in reversed(previos) if f["variante"] == contra), None)
        libro = espacio.ruta(f"vara/predicciones_{contra}.jsonl")
        if base is None or not libro.exists():
            informe["contra"] = {"error": f"no hay intento '{contra}' en este universo"}
        else:
            base_pred = {r["id"]: r for r in (json.loads(x) for x in libro.read_text(encoding="utf-8").splitlines())}
            informe["contra"] = comparar(dev, base_pred, previos, "dev", contra)
            if redacciones:
                informe["contra_redactados"] = comparar([m for m in dev if m.get("redactado_")], base_pred,
                                                        previos, "redactados", contra)
            if abrir_holdout:
                informe["contra_holdout"] = comparar(holdout, base_pred, previos, "holdout", contra)
    if abrir_holdout:
        informe["holdout"] = {**metricas(holdout), "IC95_A_pol": ic_bootstrap(holdout),
                              "placebo": placebo(holdout), "por_jugada": por_jugada(holdout)}
        lo, hi = informe["dev"]["IC95_A_pol"]
        informe["holdout"]["dentro_del_IC_dev"] = bool(lo is not None and lo <= informe["holdout"]["A_pol"] <= hi)
    informe["pbo"] = pbo([f.get("por_bloque") or [] for f in previos] + [informe["por_bloque"]])
    if registrar:
        anotar(informe)
    espacio.escribir_json(f"vara/informe_{variante}.json", informe)
    return informe


def anotar(informe: dict) -> dict:
    """Un renglón de la bitácora: solo agregados."""
    fila = {k: informe[k] for k in ("fecha", "cliente_id", "variante", "descripcion", "commit", "bot", "universo",
                                    "clasificador", "costos_version", "vara_version", "sello", "particion",
                                    "perfil", "por_bloque", "placebo", "cpcv")}
    fila["dev"] = {k: informe["dev"][k] for k in ("n", "hilos", "A_lit", "A_pol", "cobertura", "a_la_ia", "puntaje",
                                                  "errores_caros", "IC95_A_pol", "cobertura_donde_toca")}
    fila["holdout_abierto"] = "holdout" in informe
    if "holdout" in informe:
        fila["holdout"] = {k: informe["holdout"][k] for k in ("n", "A_lit", "A_pol", "cobertura", "puntaje",
                                                              "errores_caros", "dentro_del_IC_dev")}
    if "redactados" in informe:
        fila["redactados"] = {k: informe["redactados"][k] for k in ("n", "A_lit", "A_pol", "cobertura", "puntaje",
                                                                    "errores_caros", "detenidos_por_candado")}
    for parte in ("contra", "contra_holdout", "contra_redactados"):
        if parte in informe and "error" not in informe[parte]:
            fila[parte] = {k: informe[parte].get(k) for k in ("base", "n", "delta_A_pol", "delta_cobertura",
                                                             "delta_puntaje", "delta_caros", "dsr")}
    ruta = ruta_bitacora()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False, sort_keys=True) + "\n")
    return fila


def comparar(moms: list[dict], base_pred: dict, previos: list[dict], parte: str, nombre: str = "") -> dict:
    """El candidato contra la línea base sobre los MISMOS momentos."""
    comunes = [m for m in moms if m["id"] in base_pred]
    base = [{**m, "bot": base_pred[m["id"]]["bot"], "via": base_pred[m["id"]].get("via"),
             "texto": base_pred[m["id"]].get("texto") or ""} for m in comunes]
    calificar(base)
    por = defaultdict(list)
    for m, b in zip(comunes, base, strict=True):
        por[m["hilo"]].append(m["score"] - b["score"])
    deltas = [statistics.mean(v) for v in por.values()]
    srs = [f["contra"]["dsr"]["sr"] for f in previos if (f.get("contra") or {}).get("dsr", {}).get("sr")]
    mc, mb = metricas(comunes), metricas(base)
    if not comunes:
        return {"parte": parte, "n": 0}
    return {"parte": parte, "base": nombre, "n": len(comunes),
            "delta_A_pol": round(mc["A_pol"] - mb["A_pol"], 1),
            "delta_cobertura": round(mc["cobertura"] - mb["cobertura"], 1),
            "delta_puntaje": round(mc["puntaje"] - mb["puntaje"], 4),
            "delta_caros": mc["errores_caros"] - mb["errores_caros"],
            "dsr": dsr(deltas, len({f["variante"] for f in previos}) + 1,
                       statistics.pvariance(srs) if len(srs) >= 2 else None),
            "cambiaron": Counter((m["casa"], b["bot"], m["bot"]) for m, b in zip(comunes, base, strict=True)
                                 if m["bot"] != b["bot"]).most_common(10)}


# --------------------------------------------------------------------------- #
def resumen(inf: dict) -> str:
    d, p = inf["dev"], inf["particion"]
    lineas = [
        f"variante {inf['variante']} · agente {inf['bot']} · universo {inf['universo']} · "
        f"clasificador {inf['clasificador']} · sello {inf['sello'][:12]}",
        f"partición: total {p['n_total']} · dev {p['n_dev']} · holdout {p['n_holdout']} (sellado desde {p['corte']}, "
        f"desarrollo hasta {p['limite_desarrollo']}) · purgados {p['purgados']}",
        f"dev: n={d['n']} ({d['hilos']} hilos) A_pol={d['A_pol']}% IC95={d['IC95_A_pol']} A_lit={d['A_lit']}% "
        f"cobertura={d['cobertura']}% ia={d['a_la_ia']}% puntaje={d['puntaje']} IC95={d['IC95_puntaje']} "
        f"caros={d['errores_caros']} {d['por_error']}",
        f"fiel (el agente hablaría en vivo): {d['fiel']} · cobertura donde le toca: {d['cobertura_donde_toca']}%",
        f"cpcv: {inf['cpcv']}",
        f"placebo: {inf['placebo']} · oráculo: {inf['placebo_oraculo']}",
        f"pbo: {inf['pbo']}",
        f"perfil: {inf['perfil']}",
    ]
    if "redactados" in inf:
        r = inf["redactados"]
        lineas.append(f"redactados por el enjambre: n={r['n']} A_lit={r.get('A_lit')}% A_pol={r.get('A_pol')}% "
                      f"cobertura={r.get('cobertura')}% puntaje={r.get('puntaje')} caros={r.get('errores_caros')} "
                      f"{r.get('por_error')} detenidos por candado={r['detenidos_por_candado']}")
        for s in r.get("por_jugada", [])[:12]:
            lineas.append(f"   {s['casa']:<16} n={s['n']:<4}{'' if s['concluye'] else '*'} A_pol={s['A_pol']:<5} "
                          f"puntaje={s['puntaje']:<6} {s['bot']}")
    for parte in ("contra", "contra_holdout", "contra_redactados"):
        if parte in inf:
            lineas.append(f"{parte}: " + json.dumps({k: v for k, v in inf[parte].items() if k != 'cambiaron'},
                                                    ensure_ascii=False))
    if "holdout" in inf:
        lineas.append("HOLDOUT: " + json.dumps({k: v for k, v in inf["holdout"].items() if k != "por_jugada"},
                                               ensure_ascii=False))
    dd = inf["desenlace_dev"]
    lineas.append(f"desenlace (dev): avanzó {dd['avanzo']} · contestó {dd['contesto']} · silencio {dd['silencio']}")
    lineas.append("la casa gana con: " + ", ".join(
        f"{r['casa']} {r['contesta_o_avanza']}% (avanza {r['avanza']}%, n={r['n']}{'' if r['concluye'] else ', no concluye'})"
        for r in dd["la_casa_gana_con"][:8]))
    lineas.append("pérdida por jugada de la casa (dev):")
    for s in inf["por_jugada_dev"][:14]:
        lineas.append(f"   {s['casa']:<16} n={s['n']:<4}{'' if s['concluye'] else '*'} A_pol={s['A_pol']:<5} "
                      f"cob={s['cobertura']:<5} puntaje={s['puntaje']:<6} pérdida={s['perdida']:<6} {s['bot']}")
    lineas.append("(* n < 30: no concluye)")
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    from .local import _espacio

    ap = argparse.ArgumentParser(prog="python -m agente.vara", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="orden", required=True)
    m = sub.add_parser("medir")
    m.add_argument("cliente_id")
    m.add_argument("--variante", required=True)
    m.add_argument("--perfil", help="propuesta {nombre, perfil} o perfil; se valida contra la copia local")
    m.add_argument("--descripcion", default="")
    m.add_argument("--contra")
    m.add_argument("--abrir-holdout", action="store_true")
    m.add_argument("--sin-registrar", action="store_true")
    m.add_argument("--redacciones", help="{id de momento: {textos, persona, cotizar, duda}} del enjambre (desarrollo)")
    a = ap.parse_args(argv)
    espacio = _espacio(a.cliente_id)
    activo = None
    if a.perfil:
        crudo = json.loads(Path(a.perfil).read_text(encoding="utf-8"))
        activo, descartados = perfil.validar(espacio, crudo.get("perfil", crudo))
        if descartados:
            print(f"· {len(descartados)} renglones del perfil no prueban su origen y no entran", file=sys.stderr)
    try:
        inf = medir(espacio, a.variante, activo=activo, contra=a.contra, abrir_holdout=a.abrir_holdout,
                    registrar=not a.sin_registrar, descripcion=a.descripcion,
                    redacciones=json.loads(Path(a.redacciones).read_text(encoding="utf-8")) if a.redacciones else None)
    except (HoldoutYaAbierto, PerfilMiraElHoldout) as error:
        print(f"no se abre el holdout: {error}", file=sys.stderr)
        return 2
    print(resumen(inf))
    return 0


if __name__ == "__main__":
    sys.exit(main())
