"""Del historial a un corpus de entrenamiento medido, con `{{cifra}}` en vez de montos.

Gestor, `app/services/entrenamiento.py`: *"los precios no se enseñan, se
consultan"*. Una cifra en un ejemplo es una tarifa congelada que un modelo
repite con seguridad el día que ya cambió (invariante XXXII). Aquí:

1. **Exportar** (`exportar`): cada plática de venta como ejemplo JSONL, con los
   teléfonos y correos tapados, cada monto del negocio como `{{cifra}}` (los
   originales en `meta.cifras`, para auditar al cotizador contra lo que la casa
   cobró) y la jugada de la casa por momento. Va a
   `datos/espacios/<id>/corpus/` — **fuera de git** (invariantes XXXIX y XLVII):
   tapado no es anónimo (un nombre escrito dentro del mensaje no se quita con
   certeza).
2. **Medir** (`faltaba_al_cotizar`): en cada momento en que la casa dio una
   cifra, ¿qué dato de los que pide el cotizador (fechas, personas, propiedad)
   no estaba escrito todavía en la plática? Cada renglón es algo que una persona
   resolvió sin el dato —o que el cotizador no sabría hacer— y es la lista de
   trabajo del cotizador, con su n.

No llama a ningún modelo.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone

from . import historial, jugadas
from .conversacion import normalizar
from .espacio import Espacio

CARPETA = "corpus"
_TELEFONO = re.compile(r"(?<!\d)(?:\+?52\s?)?(?:\d[\s-]?){10}(?!\d)")
_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_CUENTA = re.compile(r"(?<!\d)\d{11,18}(?!\d)")
_MONTO = re.compile(r"\$\s*\d[\d,.]*|\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\d:/.])\d{3,6}(?![\d:/])"
                    r"|\b\d+(?:\.\d+)?\s*mil\b", re.IGNORECASE)
_ANO = re.compile(r"^(?:19[5-9]\d|20[0-3]\d)$")

_MESES = r"(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\w*"
FECHAS = re.compile(rf"\b\d{{1,2}}\s*(?:al|y|-|a)?\s*(?:\d{{1,2}}\s*)?(?:de\s+)?{_MESES}\b|\b{_MESES}\b"
                    r"|\bfin(?:de)? de semana\b|\b(?:este|el|proximo) (?:viernes|sabado|domingo|fin)\b"
                    r"|\b(?:navidad|ano nuevo|semana santa|puente)\b|\b\d{1,2}/\d{1,2}\b")
PERSONAS = re.compile(r"\b\d{1,3}\s*(?:personas?|adultos?|invitados?|pax|gente|huespedes|ninos|jovenes|chicos)\b"
                      r"|\bsomos\s+\d{1,3}\b|\bpara\s+\d{1,3}\b|\b(?:una|la) pareja\b|\bseriamos\s+\d{1,3}\b"
                      r"|^\s*\d{1,3}\s*(?:aprox\w*)?\s*$")
PROPIEDAD = re.compile(r"\b(?:finca|quinta|casa grande|casa chica|las dos|ambas)\b")


def tapar(texto: str | None) -> str:
    """Teléfonos, correos y cuentas fuera. Los montos se quedan (los tapa `con_cifras`)."""
    t = _CORREO.sub("[correo]", texto or "")
    t = _CUENTA.sub("[cuenta]", t)
    return _TELEFONO.sub("[telefono]", t)


def con_cifras(texto: str) -> tuple[str, list[str]]:
    """Cada monto → `{{cifra}}`. Un año no es monto."""
    cifras: list[str] = []

    def cambiar(m: re.Match) -> str:
        if _ANO.match(m.group(0).strip()):
            return m.group(0)
        cifras.append(m.group(0).strip())
        return "{{cifra}}"

    return _MONTO.sub(cambiar, texto), cifras


def lo_que_sabia(mensajes: list[historial.Mensaje]) -> dict[str, bool]:
    """Lo que el cliente ya había escrito: lo que el cotizador necesita para cotizar."""
    dicho = "\n".join(normalizar(m.texto) for m in mensajes if not m.del_negocio and m.texto)
    return {"fechas": bool(FECHAS.search(dicho)), "personas": bool(PERSONAS.search(dicho)),
            "propiedad": bool(PROPIEDAD.search(dicho))}


def faltaba_al_cotizar(hilos: dict[str, list[historial.Mensaje]]) -> dict:
    """En cada momento en que la casa dio cifra, qué dato no estaba escrito."""
    moms = [m for m in jugadas.momentos(hilos) if m.casa == "cifra"]
    faltas: Counter = Counter()
    completos = 0
    for m in moms:
        sabia = lo_que_sabia(list(m.prefijo))
        falta = tuple(k for k, v in sabia.items() if not v)
        faltas.update(falta)
        completos += not falta
    n = len(moms)
    return {"n": n, "concluye": n >= 30, "con_los_tres_datos": completos,
            "faltaba": {k: faltas[k] for k in ("fechas", "personas", "propiedad")},
            "pct_faltaba": {k: round(100 * faltas[k] / n, 1) for k in ("fechas", "personas", "propiedad")} if n else {}}


def ejemplos(espacio: Espacio) -> list[dict]:
    hilos = historial.hilos(espacio)
    fijas = jugadas.plantillas(hilos)
    por_hilo: dict[str, list[jugadas.Momento]] = {}
    for m in jugadas.momentos(hilos):
        por_hilo.setdefault(m.hilo, []).append(m)
    salida = []
    for n, (hilo, mensajes) in enumerate(sorted(hilos.items(), key=lambda kv: kv[1][0].ts)):
        if not jugadas.es_platica_de_venta(mensajes, fijas):
            continue
        auto = jugadas.automaticas(mensajes, fijas)
        casa_por_id = {m.id: m.casa for m in por_hilo.get(hilo, [])}
        turnos, cifras = [], []
        for x in mensajes:
            texto = tapar(x.texto) if x.texto else f"[{x.tipo}]"
            if x.del_negocio:
                texto, halladas = con_cifras(texto)
                cifras += halladas
            turnos.append({"rol": "negocio" if x.del_negocio else "cliente", "texto": texto,
                           "automatico": x.id in auto, **({"jugada": casa_por_id[x.id]} if x.id in casa_por_id else {})})
        salida.append({"platica": f"p{n:04d}", "turnos": turnos,
                       "meta": {"cifras": cifras, "mensajes": len(mensajes),
                                "desde": datetime.fromtimestamp(mensajes[0].ts, timezone.utc).date().isoformat()}})
    return salida


def exportar(espacio: Espacio) -> dict:
    filas = ejemplos(espacio)
    ruta = espacio.ruta(f"{CARPETA}/ejemplos.jsonl")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in filas), encoding="utf-8")
    medida = faltaba_al_cotizar(historial.hilos(espacio))
    espacio.escribir_json(f"{CARPETA}/faltaba_al_cotizar.json", medida)
    return {"platicas": len(filas), "cifras_tapadas": sum(len(f["meta"]["cifras"]) for f in filas),
            "faltaba_al_cotizar": medida, "ruta": str(ruta)}


if __name__ == "__main__":
    import sys

    from .local import _espacio

    print(json.dumps(exportar(_espacio(sys.argv[1])), ensure_ascii=False, indent=1))
