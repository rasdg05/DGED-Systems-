"""El turno: un mensaje del cliente final entra, una `Salida` queda escrita.

Orden (del más barato y seguro al más caro):

1. Sin perfil aprobado, todo a la persona.
2. Respuesta guardada del negocio: sin modelo.
3. Borrador del modelo chico (el grande si el chico dice `dificil=si`).
4. Candados por código: cifra en el texto del modelo, voz ajena o duda → a
   la persona, con el borrador para que no empiece de cero.
5. Si pide cotizar con fechas y personas, la cifra la pone el cotizador y la
   salida queda **esperando aprobación** (invariante 2). Incompleta, sin total.

Una `Salida` no se envía aquí: la envía `canal.py`, que revisa el modo de
encendido y la aprobación. Todas quedan en `salidas.jsonl` para la sombra.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone

from . import cotizador, gasto, guardia, historial, modelo, perfil, respuestas, voz
from .espacio import Espacio
from .historial import Mensaje

ARCHIVO = "salidas.jsonl"
CONTEXTO_MENSAJES = 20
LO_CONFIRMO = "Permítame confirmarlo y le escribo en un momento."


@dataclass
class Salida:
    cliente_id: str
    hilo: str
    responde_a: str
    via: str                   # guardada | modelo | cotizador | persona
    texto: str                 # lo que recibiría el cliente final
    borrador: str = ""         # lo que redactó el modelo, si no salió
    motivo: str = ""
    cotizacion: dict | None = None
    requiere_aprobacion: bool = False
    aprobada_por: str | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    creada: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @property
    def a_persona(self) -> bool:
        return self.via == "persona"

    def a_dict(self) -> dict:
        return asdict(self)


def _conversacion(espacio: Espacio, entrante: Mensaje) -> list[dict]:
    hilo = [m for m in historial.hilos(espacio).get(entrante.hilo, []) if m.texto and m.ts <= entrante.ts]
    if not hilo or hilo[-1].id != entrante.id:
        hilo.append(entrante)
    salida: list[dict] = []
    for m in hilo[-CONTEXTO_MENSAJES:]:
        rol = "assistant" if m.del_negocio else "user"
        if salida and salida[-1]["role"] == rol:
            salida[-1]["content"] += "\n" + m.texto
        else:
            salida.append({"role": rol, "content": m.texto})
    while salida and salida[0]["role"] != "user":
        salida.pop(0)
    return salida


def _fecha(texto: str | None) -> date | None:
    try:
        return date.fromisoformat((texto or "").strip())
    except ValueError:
        return None


def _entero(texto: str | None) -> int | None:
    t = (texto or "").strip()
    return int(t) if t.isdigit() else None


def _a_persona(base: dict, motivo: str, borrador: str = "") -> Salida:
    return Salida(**base, via="persona", texto=LO_CONFIRMO, borrador=borrador, motivo=motivo)


def decidir(espacio: Espacio, entrante: Mensaje, client=None) -> Salida:
    base = {"cliente_id": espacio.cliente_id, "hilo": entrante.hilo, "responde_a": entrante.id}
    activo = perfil.activo(espacio)
    if activo is None:
        return _a_persona(base, "sin perfil aprobado")
    if not (entrante.texto or "").strip():
        return _a_persona(base, "mensaje sin texto (foto, audio o documento)")

    guardada = respuestas.buscar(activo, entrante.texto)
    if guardada:
        return Salida(**base, via="guardada", texto=guardada["respuesta"])

    conversacion = _conversacion(espacio, entrante)
    try:
        texto, meta = modelo.turno(espacio, activo, conversacion, client=client)
        if meta.get("dificil") == "si" and gasto.puede_gastar(espacio):
            texto, meta = modelo.turno(espacio, activo, conversacion, client=client, modelo=modelo.MODELO_GRANDE)
    except (modelo.Dormido, gasto.TopeAlcanzado, modelo.LlamadaFallida) as error:
        return _a_persona(base, str(error) or type(error).__name__)

    if (cifras := guardia.cifras_no_permitidas(texto)):
        return _a_persona(base, f"cifra que no puso el cotizador: {cifras}", texto)
    if (rasgos := voz.hallazgos(texto, activo)):
        return _a_persona(base, "voz ajena: " + "; ".join(rasgos), texto)
    if meta.get("persona") == "si" or not texto:
        return _a_persona(base, meta.get("duda") or "el modelo pidió a la persona", texto)

    llegada, salida_ = _fecha(meta.get("llegada")), _fecha(meta.get("salida"))
    personas, propiedad = _entero(meta.get("personas")), (meta.get("propiedad") or "").strip()
    if meta.get("cotizar") == "si" and llegada and salida_ and personas and propiedad:
        cot = cotizador.cotizar(activo, propiedad, llegada, salida_, personas, meta.get("evento") == "si")
        if not cot.completa:
            return Salida(**base, via="persona", texto=LO_CONFIRMO, borrador=texto,
                          motivo="cotización incompleta: " + "; ".join(cot.faltan), cotizacion=cot.a_dict())
        return Salida(**base, via="cotizador", texto=f"{texto}\n\n{cot.texto()}", borrador=texto,
                      cotizacion=cot.a_dict(), requiere_aprobacion=True)
    return Salida(**base, via="modelo", texto=texto)


def atender(espacio: Espacio, entrante: Mensaje, client=None) -> Salida:
    historial.guardar(espacio, [entrante])
    salida = decidir(espacio, entrante, client=client)
    espacio.agregar_linea(ARCHIVO, salida.a_dict())
    return salida


def salidas(espacio: Espacio) -> list[Salida]:
    return [Salida(**d) for d in espacio.leer_lineas(ARCHIVO)]


def aprobar_salida(espacio: Espacio, salida_id: str, aprobador: str) -> Salida:
    """Una persona del negocio aprueba una cotización. Queda escrito quién."""
    alta = espacio.leer_json("alta.json", {}) or {}
    autorizados = {a.strip().casefold() for a in [alta.get("aprobador", "")] + list(alta.get("asesores", []) or []) if a}
    if aprobador.strip().casefold() not in autorizados:
        raise perfil.AprobacionInvalida("solo aprueban las personas que el alta registra")
    for s in salidas(espacio):
        if s.id == salida_id:
            s.aprobada_por = aprobador
            espacio.agregar_linea("aprobaciones_salida.jsonl", {"id": salida_id, "aprobador": aprobador,
                                                                "en": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            return s
    raise KeyError(salida_id)


def aprobadas(espacio: Espacio) -> dict[str, str]:
    return {r["id"]: r["aprobador"] for r in espacio.leer_lineas("aprobaciones_salida.jsonl")}
