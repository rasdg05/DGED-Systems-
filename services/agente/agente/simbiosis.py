"""Simbiosis: del historial y el alta sale una propuesta de perfil, citada renglón por renglón.

Diseñado por costo (`docs/15-agente-a-la-medida.md`):

1. **Clasificación en lote con el modelo chico** (Batch API, 50% del precio):
   cada mensaje del negocio se marca como voz, respuesta frecuente, cotización,
   escala u otro. Es trabajo de fondo, no de tiempo real.
2. **Una pasada cara, una vez**: el modelo grande lee el alta y solo los
   mensajes que la clasificación no tiró, y propone el perfil con origen por
   renglón. Después se actualiza por diferencias (`desde_ts`): solo mensajes
   nuevos, sobre el perfil activo.

Lo que el modelo propone pasa por `perfil.proponer`, que tira lo que no cita
un mensaje real de este cliente con la cita literal y la cifra dentro de la
cita. Nada se activa solo: lo aprueba el dueño (`perfil.aprobar`).

**No medido contra la API real**: los tests corren con respuestas grabadas.
"""
from __future__ import annotations

import json

from . import gasto, historial, perfil
from .espacio import Espacio
from .modelo import FALLBACK_BETA, MODELO_GRANDE, MODELO_RUTINA, cliente_real

CATEGORIAS = ("voz", "faq", "cotizacion", "escala", "otro")
CONTEXTO_CLIENTE = 1

ESQUEMA_CLASE = {
    "type": "object",
    "properties": {"categoria": {"type": "string", "enum": list(CATEGORIAS)}},
    "required": ["categoria"],
    "additionalProperties": False,
}

_ORIGEN = {
    "type": "object",
    "properties": {
        "tipo": {"type": "string", "enum": ["mensaje", "alta", "documento"]},
        "id": {"type": "string"}, "campo": {"type": "string"}, "nombre": {"type": "string"},
        "cita": {"type": "string"},
    },
    "required": ["tipo", "id", "campo", "nombre", "cita"],
    "additionalProperties": False,
}
_NUM = {"type": ["integer", "null"]}
_TXT = {"type": ["string", "null"]}


def _lista(propiedades: dict) -> dict:
    props = dict(propiedades, origen=_ORIGEN)
    return {"type": "array", "items": {"type": "object", "properties": props,
                                       "required": list(props), "additionalProperties": False}}


ESQUEMA_PERFIL = {
    "type": "object",
    "properties": {
        "trato": {"type": ["string", "null"], "enum": ["usted", "tu", None]},
        "datos": _lista({"objeto": {"type": "string"}, "id": {"type": "string"}, "campo": {"type": "string"},
                         "valor": {"type": ["string", "integer", "number", "boolean"]}}),
        "temporadas": _lista({"nombre": {"type": "string"}, "desde": {"type": "string"}, "hasta": {"type": "string"}}),
        "voz": _lista({"frase": {"type": "string"}}),
        "reglas": _lista({"propiedad": {"type": "string"},
                          "tipo": {"type": "string", "enum": ["noche", "persona_extra", "evento", "minimo_noches",
                                                             "capacidad", "anticipo", "deposito"]},
                          "temporada": _TXT, "dias": {"type": ["string", "null"],
                                                      "enum": ["fin_de_semana", "entre_semana", None]},
                          "monto_centavos": _NUM, "pct": _NUM, "noches": _NUM, "personas": _NUM}),
        "faq": _lista({"pregunta": {"type": "string"}, "respuesta": {"type": "string"}}),
        "escala": _lista({"caso": {"type": "string"}}),
    },
    "required": ["trato", "datos", "temporadas", "voz", "reglas", "faq", "escala"],
    "additionalProperties": False,
}

INSTRUCCION_PERFIL = (
    "Arma el perfil de este negocio SOLO con lo que está escrito abajo (alta y mensajes). Cada renglón "
    "lleva su origen: el id del mensaje (o el campo del alta) y una cita copiada letra por letra de ese "
    "texto. Si una cifra no está en la cita, el renglón se tira. Datos, voz, reglas y respuestas salen de "
    "mensajes DEL NEGOCIO, nunca del cliente. Voz: frases tal cual las escribe el negocio. Reglas de "
    "cotización: montos en centavos (3,500 pesos = 350000). Temporadas con fechas MM-DD. Lo que no esté "
    "escrito, no lo pongas."
)


# --------------------------------------------------------------------------- #
#  1. Clasificación en lote (modelo chico)                                     #
# --------------------------------------------------------------------------- #
def solicitudes_de_clasificacion(espacio: Espacio) -> tuple[list[dict], dict[str, str]]:
    pedidos, mapa = [], {}
    for mensajes in historial.hilos(espacio).values():
        for i, m in enumerate(mensajes):
            if not m.del_negocio or not m.texto:
                continue
            previos = [p for p in mensajes[max(0, i - CONTEXTO_CLIENTE):i] if not p.del_negocio and p.texto]
            contexto = "".join(f"Cliente: {p.texto}\n" for p in previos)
            custom_id = f"m{len(mapa):06d}"  # el wamid no cabe en el patrón de custom_id
            mapa[custom_id] = m.id
            pedidos.append({"custom_id": custom_id, "params": {
                "model": MODELO_RUTINA, "max_tokens": 1024, "output_config": {
                    "effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA_CLASE}},
                "messages": [{"role": "user", "content": (
                    f"{contexto}Negocio: {m.texto}\n\n¿Qué es el mensaje del negocio? voz (cómo saluda, "
                    "despide o pide datos), faq (contesta una pregunta común), cotizacion (da precio o "
                    "condiciones), escala (pasa el caso a alguien o lo atiende aparte) u otro.")}]}})
    return pedidos, mapa


def enviar_lote(espacio: Espacio, client=None) -> str:
    gasto.exigir_saldo(espacio)
    client = client or cliente_real()
    pedidos, mapa = solicitudes_de_clasificacion(espacio)
    lote = client.messages.batches.create(requests=pedidos)
    espacio.escribir_json("simbiosis/lote.json", {"id": lote.id, "mapa": mapa})
    return lote.id


def recoger_lote(espacio: Espacio, client=None) -> dict[str, str] | None:
    """None si el lote no ha terminado. Si terminó, {wamid: categoría} y el gasto anotado."""
    client = client or cliente_real()
    registro = espacio.leer_json("simbiosis/lote.json")
    if client.messages.batches.retrieve(registro["id"]).processing_status != "ended":
        return None
    clases = {}
    for r in client.messages.batches.results(registro["id"]):
        if r.result.type != "succeeded":
            continue
        msg = r.result.message
        gasto.registrar(espacio, MODELO_RUTINA, msg.usage, motivo="clasificacion", lote=True)
        texto = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")
        try:
            categoria = json.loads(texto).get("categoria")
        except (json.JSONDecodeError, AttributeError):
            continue
        if categoria in CATEGORIAS and r.custom_id in registro["mapa"]:
            clases[registro["mapa"][r.custom_id]] = categoria
    espacio.escribir_json("simbiosis/clasificacion.json", clases)
    return clases


# --------------------------------------------------------------------------- #
#  2. Una pasada grande, y después por diferencias                             #
# --------------------------------------------------------------------------- #
def _material(espacio: Espacio, desde_ts: int | None) -> str:
    clases = espacio.leer_json("simbiosis/clasificacion.json", {}) or {}
    alta = espacio.leer_json("alta.json", {}) or {}
    partes = ["<alta>"] + [f'<campo nombre="{k}">{v}</campo>' for k, v in alta.items()
                           if k not in ("aprobador_telefono",)] + ["</alta>"]
    for hilo in historial.hilos(espacio).values():
        bloque = []
        for m in hilo:
            if not m.texto or (desde_ts is not None and m.ts < desde_ts):
                continue
            if m.del_negocio and clases.get(m.id) == "otro":
                continue
            bloque.append(f'<mensaje id="{m.id}" de="{"negocio" if m.del_negocio else "cliente"}">{m.texto}</mensaje>')
        if bloque:
            partes += ["<conversacion>"] + bloque + ["</conversacion>"]
    return "\n".join(partes)


def _sin_nulos(propuesta: dict) -> dict:
    limpio = {"trato": propuesta.get("trato")}
    for seccion in perfil.SECCIONES:
        filas = []
        for fila in propuesta.get(seccion, []) or []:
            fila = {k: v for k, v in fila.items() if v is not None}
            origen = {k: v for k, v in fila.get("origen", {}).items() if v not in ("", None)}
            filas.append(dict(fila, origen=origen))
        limpio[seccion] = filas
    return limpio


def construir_perfil(espacio: Espacio, client=None, *, desde_ts: int | None = None,
                     nombre: str = "simbiosis") -> tuple[int, list[dict]]:
    gasto.exigir_saldo(espacio)
    client = client or cliente_real()
    respuesta = client.beta.messages.create(
        model=MODELO_GRANDE, max_tokens=32000,
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": ESQUEMA_PERFIL}},
        betas=[FALLBACK_BETA], fallbacks="default",
        messages=[{"role": "user", "content": f"{_material(espacio, desde_ts)}\n\n{INSTRUCCION_PERFIL}"}],
    )
    gasto.registrar(espacio, MODELO_GRANDE, getattr(respuesta, "usage", None), motivo="perfil")
    if respuesta.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"la pasada del perfil no terminó ({respuesta.stop_reason}); no se propone a medias")
    texto = "".join(getattr(b, "text", "") for b in respuesta.content if getattr(b, "type", "") == "text")
    propuesta = _sin_nulos(json.loads(texto))
    alta = espacio.leer_json("alta.json", {}) or {}
    base = perfil.activo(espacio) or {}
    combinado = {"giro": alta.get("giro"), "nombre_comercial": alta.get("nombre_comercial"),
                 "trato": propuesta.get("trato") or base.get("trato")}
    for seccion in perfil.SECCIONES:
        filas = list(base.get(seccion, []) or [])
        vistas = {json.dumps(f, sort_keys=True, ensure_ascii=False) for f in filas}
        filas += [f for f in propuesta[seccion] if json.dumps(f, sort_keys=True, ensure_ascii=False) not in vistas]
        combinado[seccion] = filas
    return perfil.proponer(espacio, combinado, autor=MODELO_GRANDE, nombre=nombre)
