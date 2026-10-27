"""El semáforo: a quién se le escribe primero y por qué, como el de Gestor Morelos.

De Gestor (`expediente_cotizacion.semaforo`, `QUE_HACER`): **un solo estado por
plática, el más urgente**, y la lista **ordenada por cuánto lleva esperando**,
no por cuándo llegó. Tres etiquetas a la vez sobre el mismo chat no ayudan a
decidir; la lista existe para saber a quién se le escribe primero.

Sobre `pendientes.py` (la única vara de "espera respuesta") agrega lo que pasa
cuando lo último es del negocio, que es donde se cierran o se pierden las
cotizaciones:

- `sin_atender`: escribió y solo le contestó la bienvenida automática.
- `nos_toca`: escribió, ya lo atendió una persona antes, y nadie le contestó esto.
- `reclamo` y `solo_medios`: los ve una persona; el enjambre no los toca.
- `promesa`: la casa quedó de mandar algo (*"déjame revisar"*) y no llegó.
- `cotizado`: ya tiene precio y no ha decidido: **seguimiento para cerrar**.
- `esperando_cliente`: se le preguntó algo y no contesta.
- `cerrada`: ya resolvió, dijo que no o no pide nada: no se le escribe.

El color sale del estado y de las horas, no de una opinión: rojo es trabajo
nuestro con más de `HORAS_ROJO` encima (o un reclamo); ámbar, trabajo nuestro
reciente o un seguimiento que ya toca; verde, la pelota la tiene el cliente y
aún no toca; gris, nada que hacer. Sin red ni modelo.
"""
from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass

from . import conversacion, jugadas, pendientes
from .historial import Mensaje

HORAS_ROJO = 2            # trabajo nuestro con más de esto encima: rojo
HORAS_SEGUIMIENTO = 24    # un cotizado o una pregunta sin respuesta: el seguimiento toca desde aquí
DIAS_VIGENCIA = 21        # después, la plática se enfrió: no se persigue en ronda

QUE_HACER = {
    "sin_atender": "solo recibió la bienvenida automática: nadie lo ha atendido",
    "nos_toca": "escribió y nadie le ha contestado",
    "reclamo": "está molesto o reclama dinero: lo atiende una persona",
    "solo_medios": "mandó foto, audio o documento: lo ve una persona",
    "promesa": "quedamos de mandarle algo y no ha llegado",
    "cotizado": "ya tiene precio: falta que decida, dele seguimiento",
    "esperando_cliente": "se le preguntó y no ha contestado",
    "cerrada": "ya lo resolvió, dijo que no o no pide nada",
}
ETIQUETA = {"sin_atender": "Sin atender", "nos_toca": "Le toca contestar", "reclamo": "Reclamo",
            "solo_medios": "Foto o audio", "promesa": "Quedamos de mandar", "cotizado": "Cotizado",
            "esperando_cliente": "Esperando al cliente", "cerrada": "Cerrada"}
COLORES = ("rojo", "ambar", "verde", "gris")
#: La casa quedó de dar algo (*"déjeme revisar"*, *"ahorita le mando"*, *"le confirmo"*).
_PROMETE = re.compile(
    r"\b(?:dejame|dejeme|permitame|permiteme)\s+(?:revisar|checar|validar|verificar|confirmar\w*|consultar|preguntar)\b|"
    r"\b(?:ahorita|en un momento|mas tarde|al rato|en un rato|en breve|hoy|manana)\s+(?:le|te)\s+"
    r"(?:mando|envio|paso|confirmo|digo|aviso|escribo|comparto)\b|"
    r"\b(?:le|te) (?:confirmo|aviso|paso|mando|comparto) (?:en|el|la|mas|ahorita|hoy|manana|disponibilidad|fechas)\b|"
    r"\bya (?:lo|la|le) estoy (?:checando|revisando|cotizando|validando)\b")


@dataclass(frozen=True)
class Fila:
    hilo: str
    estado: str
    color: str
    horas: float          # cuánto lleva así
    que_hacer: str
    dicho: str            # lo último con palabras (del cliente si es suyo; si no, de la casa)
    ultimo_id: str
    hubo_persona: bool
    seguimiento: bool     # candidato a recordatorio en ronda (cotizado o esperando, 24 h a 21 días)

    @property
    def etiqueta(self) -> str:
        return ETIQUETA[self.estado]

    def a_dict(self) -> dict:
        return {**asdict(self), "etiqueta": self.etiqueta}


def _horas(desde_ts: int, ahora_ts: float) -> float:
    return round(max(0.0, ahora_ts - desde_ts) / 3600, 1)


def _color(estado: str, horas: float) -> str:
    if estado == "reclamo":
        return "rojo"
    if estado in ("sin_atender", "nos_toca", "promesa", "solo_medios"):
        return "rojo" if horas >= HORAS_ROJO else "ambar"
    if estado in ("cotizado", "esperando_cliente"):
        return "ambar" if HORAS_SEGUIMIENTO <= horas <= DIAS_VIGENCIA * 24 else ("verde" if horas < HORAS_SEGUIMIENTO
                                                                                  else "gris")
    return "gris"


def _del_negocio_al_final(hilo: str, mensajes: list[Mensaje], auto: set[str], ahora_ts: float) -> Fila:
    i = len(mensajes)
    while i > 0 and mensajes[i - 1].del_negocio:
        i -= 1
    tanda = mensajes[i:]
    texto = "\n".join(m.texto for m in tanda if m.texto)
    t = conversacion.normalizar(texto)
    previo_cliente = [m for m in mensajes[:i] if not m.del_negocio and m.texto]
    hubo_persona = any(m.del_negocio and m.texto and m.id not in auto for m in mensajes)
    cerro = previo_cliente and (conversacion.es_cierre(previo_cliente[-1].texto)
                                or conversacion.es_contestador(previo_cliente[-1].texto))
    if cerro:
        estado = "cerrada"
    elif all(m.id in auto for m in tanda) and not hubo_persona:
        estado = "sin_atender"  # solo le contestó la máquina: la pelota sigue siendo nuestra
    elif any(jugadas.es_monto(m.texto) for m in tanda if m.texto):
        estado = "cotizado"
    elif _PROMETE.search(t):
        estado = "promesa"
    else:
        estado = "esperando_cliente"
    desde = (previo_cliente[-1].ts if estado == "sin_atender" and previo_cliente else tanda[-1].ts)
    horas = _horas(desde, ahora_ts)
    dicho = (previo_cliente[-1].texto if estado == "sin_atender" and previo_cliente else texto) or ""
    color = _color(estado, horas)
    return Fila(hilo=hilo, estado=estado, color=color, horas=horas, que_hacer=QUE_HACER[estado], dicho=dicho[:200],
                ultimo_id=mensajes[-1].id, hubo_persona=hubo_persona,
                seguimiento=estado in ("cotizado", "esperando_cliente") and color == "ambar")


def leer(hilos: dict[str, list[Mensaje]], ahora_ts: float | None = None) -> list[Fila]:
    """Una fila por plática, la más urgente primero: rojo, ámbar, verde, gris; y dentro
    de cada color, la que más lleva esperando."""
    ahora_ts = ahora_ts if ahora_ts is not None else time.time()
    fijas = jugadas.plantillas(hilos)
    del_cliente = {p.hilo: p for p in pendientes.leer(hilos)}
    filas = []
    for hilo, mensajes in hilos.items():
        if not mensajes:
            continue
        auto = jugadas.automaticas(mensajes, fijas)
        p = del_cliente.get(hilo)
        if p is not None:
            estado = {"espera": "nos_toca" if p.hubo_persona else "sin_atender", "solo_medios": "solo_medios",
                      "reclamo": "reclamo", "no_pide": "cerrada"}[p.estado]
            horas = _horas(p.espera_desde, ahora_ts)
            filas.append(Fila(hilo=hilo, estado=estado, color=_color(estado, horas), horas=horas,
                              que_hacer=QUE_HACER[estado], dicho=(p.dicho or "")[:200], ultimo_id=p.ultimo_id,
                              hubo_persona=p.hubo_persona, seguimiento=False))
        else:
            filas.append(_del_negocio_al_final(hilo, mensajes, auto, ahora_ts))
    return sorted(filas, key=lambda f: (COLORES.index(f.color), -f.horas))


def resumen(filas: list[Fila]) -> dict:
    por_color = {c: sum(1 for f in filas if f.color == c) for c in COLORES}
    por_estado = {e: sum(1 for f in filas if f.estado == e) for e in QUE_HACER}
    return {"total": len(filas), **por_color, "estados": por_estado,
            "seguimiento": sum(1 for f in filas if f.seguimiento)}
