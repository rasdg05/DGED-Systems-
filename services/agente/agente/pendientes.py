"""Qué conversaciones esperan al negocio, leídas igual en local y en producción.

Gestor lo aprendió con tres varas que no cuadraban (`exp.no_espera_nada`,
2026-10-24): "el último mensaje es del cliente" no es "espera respuesta". Un
*"ok gracias"*, un *"lo platico y le aviso"* o *"ya rentamos en otro lado"* no
piden nada. Esta es la única vara del agente; el panel y el enjambre la usan.

- `espera`: el cliente pidió algo y nadie le contestó después.
- `solo_medios`: lo último fue una foto, audio o documento: lo ve una persona.
- `reclamo`: molestia o dinero reclamado: nunca lo contesta el enjambre.
- `no_pide`: acuse, cierre o contestador. El último mensaje es del cliente,
  pero no es trabajo: el panel no lo cuenta como sin responder.

Lo automático del negocio (la bienvenida y las plantillas que salen a los
segundos) no es una persona contestando: `hubo_persona` lo dice por hilo, con
la misma regla que la vara (`jugadas.automaticas`). Un *"Ok"* repetido 26 veces
sí lo tecleó una persona (antes contaba como plantilla, 2026-10-27).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

from . import conversacion, jugadas
from .historial import Mensaje

USOS_DE_PLANTILLA = jugadas.USOS_DE_PLANTILLA
ESTADOS = ("espera", "solo_medios", "reclamo", "no_pide")


@dataclass(frozen=True)
class Pendiente:
    hilo: str
    estado: str           # espera | solo_medios | reclamo | no_pide
    ultimo_id: str        # el enjambre lo cita: si cambia, su ronda no sale
    ultimo_ts: int
    espera_desde: int     # el primer mensaje del cliente sin respuesta
    dicho: str            # la ráfaga del cliente sin contestar
    hubo_persona: bool    # alguna vez contestó alguien que no fuera plantilla

    def a_dict(self) -> dict:
        return asdict(self)


plantillas = jugadas.plantillas


def _de_un_hilo(hilo: str, mensajes: list[Mensaje], fijas: set[str]) -> Pendiente | None:
    if not mensajes or mensajes[-1].del_negocio:
        return None
    i = len(mensajes)
    while i > 0 and not mensajes[i - 1].del_negocio:
        i -= 1
    sin_respuesta = mensajes[i:]
    dicho = conversacion.rafaga(sin_respuesta) or "\n".join(m.texto for m in sin_respuesta if m.texto)
    if not any(m.texto for m in sin_respuesta):
        estado = "solo_medios"
    elif conversacion.es_reclamo(dicho):
        estado = "reclamo"
    elif (conversacion.nada_que_contestar(dicho) or conversacion.es_cierre(dicho)
          or conversacion.es_contestador(dicho)):
        estado = "no_pide"
    else:
        estado = "espera"
    auto = jugadas.automaticas(mensajes, fijas)
    hubo_persona = any(m.del_negocio and m.texto and m.id not in auto for m in mensajes)
    return Pendiente(hilo=hilo, estado=estado, ultimo_id=mensajes[-1].id, ultimo_ts=mensajes[-1].ts,
                     espera_desde=sin_respuesta[0].ts, dicho=dicho, hubo_persona=hubo_persona)


def leer(hilos: dict[str, list[Mensaje]]) -> list[Pendiente]:
    """Los hilos cuyo último mensaje es del cliente, clasificados; los que más esperan primero."""
    fijas = plantillas(hilos)
    salida = [p for h, ms in hilos.items() if (p := _de_un_hilo(h, ms, fijas))]
    return sorted(salida, key=lambda p: p.espera_desde)


def resumen(pendientes: list[Pendiente]) -> dict:
    estados = Counter(p.estado for p in pendientes)
    return {"sin_responder": len(pendientes), **{e: estados.get(e, 0) for e in ESTADOS},
            "espera_sin_persona_nunca": sum(1 for p in pendientes if p.estado == "espera" and not p.hubo_persona)}
