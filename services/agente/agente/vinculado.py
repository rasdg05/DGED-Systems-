"""Lector por dispositivo vinculado (QR de WhatsApp Web, neonize): SOLO LECTURA.

    AGENTE_ESPACIO_VINCULADO=<cliente> AGENTE_DATOS=/data/espacios python -m agente.vinculado

Decisión del dueño, 2026-10-21 (D-018): mientras Meta no apruebe a DGED como
Tech Provider, el historial del negocio se lee vinculando un dispositivo, como
el worker de Gestor Morelos. **Es el canal no oficial** que D-016 prohibió para
ENVIAR; aquí se usa solo para leer, que es lo que hace cualquier WhatsApp Web
abierto. Tres candados:

- **Este módulo no envía nada.** No hay llamada de envío, ni de "escribiendo",
  ni de "en línea", ni acuse de lectura; un test lo revisa en el código fuente.
  Lo que redacte el agente sigue saliendo solo por la Cloud API (`canal.py`).
- **La sesión vive en el espacio** (`vinculado/session.sqlite3`): sobrevive a
  los reinicios del contenedor si el espacio está en un volumen, y se borra
  con el espacio al terminar el contrato.
- **Si `config.json` trae `numero_negocio` y se vinculó otro número, no se
  importa nada** (lección de Gestor: el historial de un teléfono ajeno se
  vuelve "clientes").

Las funciones de traducción no importan neonize: se prueban sin él.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone

from . import historial
from .espacio import Espacio
from .historial import Mensaje

logger = logging.getLogger("agente.vinculado")

ESTADO = "vinculado/estado.json"
SESION = "vinculado/session.sqlite3"
ENVOLTURAS = ("ephemeralMessage", "viewOnceMessage", "viewOnceMessageV2", "viewOnceMessageV2Extension",
              "documentWithCaptionMessage", "editedMessage")
MEDIOS = (("imageMessage", "imagen"), ("videoMessage", "video"), ("documentMessage", "documento"),
          ("audioMessage", "audio"), ("stickerMessage", "sticker"))


def _campo(obj, nombre: str):
    if obj is None:
        return None
    try:
        if hasattr(obj, "HasField") and not obj.HasField(nombre):
            return None
    except ValueError:  # el proto no tiene ese campo
        return None
    return getattr(obj, nombre, None)


def desenvolver(mensaje):
    for _ in range(3):
        for nombre in ENVOLTURAS:
            sobre = _campo(mensaje, nombre)
            adentro = _campo(sobre, "message") if sobre is not None else None
            if adentro is not None:
                mensaje = adentro
                break
        else:
            return mensaje
    return mensaje


def contenido(mensaje) -> tuple[str, str | None]:
    """(tipo, texto) de un mensaje de WhatsApp. Texto None si no trae palabras."""
    m = desenvolver(mensaje)
    if m is None:
        return "otro", None
    texto = getattr(m, "conversation", "") or ""
    if not texto:
        ext = _campo(m, "extendedTextMessage")
        texto = (getattr(ext, "text", "") or "") if ext is not None else ""
    if texto:
        return "text", texto
    for campo, tipo in MEDIOS:
        sub = _campo(m, campo)
        if sub is not None:
            return tipo, (getattr(sub, "caption", "") or None)
    return "otro", None


def _usuario(jid: str) -> str:
    return (jid or "").split("@", 1)[0].split(":", 1)[0]


def mensajes_del_historial(data) -> list[Mensaje]:
    """Un `HistorySync` de neonize → mensajes del espacio. Sin grupos ni difusiones."""
    lid_a_tel = {}
    for par in getattr(data, "phoneNumberToLidMappings", []) or []:
        pn, lid = _usuario(getattr(par, "pnJID", "")), _usuario(getattr(par, "lidJID", ""))
        if pn.isdigit() and lid:
            lid_a_tel[lid] = pn
    salida = []
    for conv in getattr(data, "conversations", []) or []:
        jid = getattr(conv, "ID", "") or ""
        if any(s in jid for s in ("@g.us", "@broadcast", "@newsletter")):
            continue
        usuario = _usuario(jid)
        telefono = lid_a_tel.get(usuario, usuario)
        if not telefono.isdigit():
            continue
        for hm in getattr(conv, "messages", []) or []:
            wmi = getattr(hm, "message", None)
            key = getattr(wmi, "key", None) if wmi is not None else None
            ident = getattr(key, "ID", "") if key is not None else ""
            if not ident:
                continue
            tipo, texto = contenido(getattr(wmi, "message", None))
            salida.append(Mensaje(id=ident, hilo=telefono, del_negocio=bool(getattr(key, "fromMe", False)),
                                  ts=int(getattr(wmi, "messageTimestamp", 0) or 0), tipo=tipo, texto=texto))
    return salida


def telefono_de(jid, alt=None, resolver=None) -> str:
    usuario = (getattr(jid, "User", "") or "").strip()
    if getattr(jid, "Server", "") != "lid":
        return usuario
    alterno = (getattr(alt, "User", "") or "").strip() if alt is not None else ""
    if alterno.isdigit() and getattr(alt, "Server", "") != "lid":
        return alterno
    if resolver is not None:
        try:
            numero = (getattr(resolver(jid), "User", "") or "").strip()
            if numero.isdigit():
                return numero
        except Exception:  # sin traducción, el LID es mejor que perder el mensaje
            logger.warning("No se pudo traducir un LID")
    return usuario


def mensaje_vivo(event, resolver=None) -> Mensaje | None:
    """Un `MessageEv` → mensaje del espacio. None para grupos o sin remitente."""
    info = getattr(event, "Info", None)
    src = getattr(info, "MessageSource", None)
    if src is None or getattr(src, "IsGroup", False):
        return None
    de_la_casa = bool(getattr(src, "IsFromMe", False))
    if de_la_casa:
        hilo = telefono_de(getattr(src, "Chat", None), getattr(src, "RecipientAlt", None), resolver)
    else:
        hilo = telefono_de(getattr(src, "Sender", None), getattr(src, "SenderAlt", None), resolver)
    ident = getattr(info, "ID", "") or ""
    if not hilo or not ident:
        return None
    ts = getattr(info, "Timestamp", 0) or 0
    ts = int(ts / 1000) if ts > 10_000_000_000 else int(ts)  # neonize da milisegundos
    tipo, texto = contenido(getattr(event, "Message", None))
    return Mensaje(id=ident, hilo=hilo, del_negocio=de_la_casa, ts=ts, tipo=tipo, texto=texto)


# --------------------------------------------------------------------------- #
#  Estado para la página del QR                                                #
# --------------------------------------------------------------------------- #
def publicar(espacio: Espacio, estado: str, **extra) -> None:
    anterior = espacio.leer_json(ESTADO, {}) or {}
    if anterior.get("estado") != estado:
        anterior.pop("detalle", None)  # el aviso de un estado viejo no se queda pegado al nuevo (429 del 2026-10-27)
    anterior.update(extra, estado=estado, en=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    if estado != "esperando_qr":
        anterior.pop("qr", None)
    if estado != "esperando_codigo":
        anterior.pop("codigo", None)
    espacio.escribir_json(ESTADO, anterior)


class Emparejar:
    """Qué se le enseña al negocio para vincular: el código de 8 si se puede, si no el QR.

    WhatsApp limita los códigos por número (429 rate-overlimit; medido el 2026-10-27 con
    Finca Emiliano tras varios reinicios del servicio). Antes, al fallar el código se
    anunciaba "esperando_qr" SIN el QR y los QR siguientes se ignoraban: el negocio veía
    "Preparando" para siempre. Ahora el último QR se publica en cuanto el código falla,
    y el código se vuelve a pedir solo pasado `reintento_s`.
    """

    def __init__(self, espacio: Espacio, telefono: str, pedir, reintento_s: int = 3600, reloj=time.time):
        self.espacio, self.telefono, self.pedir = espacio, telefono, pedir
        self.reintento_s, self.reloj = reintento_s, reloj
        self.ultimo_qr = ""
        self.estado = "sin_pedir"  # sin_pedir | pidiendo | mostrado | fallo
        self.fallo_en = 0.0

    def al_recibir_qr(self, qr: str) -> bool:
        """Devuelve True si hay que pedir el código (el llamador lo pide en otro hilo)."""
        self.ultimo_qr = qr
        if not self.telefono:
            publicar(self.espacio, "esperando_qr", qr=qr)
            return False
        if self.estado in ("pidiendo", "mostrado"):
            return False
        if self.estado == "fallo" and self.reloj() - self.fallo_en < self.reintento_s:
            publicar(self.espacio, "esperando_qr", qr=qr)
            return False
        self.estado = "pidiendo"
        return True

    def pedir_codigo(self) -> None:
        try:
            codigo = self.pedir(self.telefono)
        except Exception as error:  # el QR sigue sirviendo, y se publica YA
            logger.warning("No se pudo pedir el código de vinculación: %r", error)
            self.estado, self.fallo_en = "fallo", self.reloj()
            espera = "WhatsApp pidió esperar antes de dar otro código." if "429" in repr(error) else \
                "No se pudo pedir el código."
            publicar(self.espacio, "esperando_qr", qr=self.ultimo_qr,
                     detalle=f"{espera} Mientras, escanee el QR desde otra pantalla.")
            return
        self.estado = "mostrado"
        publicar(self.espacio, "esperando_codigo", codigo=codigo)


def leer_estado(espacio: Espacio) -> dict:
    return espacio.leer_json(ESTADO, {}) or {"estado": "sin_lector"}


def numero_permitido(espacio: Espacio, numero: str) -> bool:
    esperado = "".join(c for c in str(espacio.config().get("numero_negocio", "")) if c.isdigit())
    return not esperado or esperado[-10:] == "".join(c for c in numero if c.isdigit())[-10:]


def importar(espacio: Espacio, mensajes: list[Mensaje]) -> int:
    estado = leer_estado(espacio)
    if estado.get("numero") and not numero_permitido(espacio, estado["numero"]):
        logger.critical("Sesión de un número que no es el del negocio: no se importa nada")
        return 0
    nuevos = historial.guardar(espacio, mensajes)
    publicar(espacio, estado.get("estado", "conectado"),
             mensajes=len(historial.cargar(espacio)), ultimo_import=nuevos)
    return nuevos


# --------------------------------------------------------------------------- #
#  El proceso                                                                  #
# --------------------------------------------------------------------------- #
def main() -> int:  # pragma: no cover - necesita WhatsApp de verdad
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    cliente_id = os.environ.get("AGENTE_ESPACIO_VINCULADO", "").strip()
    if not cliente_id:
        logger.info("Sin AGENTE_ESPACIO_VINCULADO: el lector vinculado no arranca.")
        while True:  # dormido sin tumbar el contenedor
            time.sleep(3600)
    espacio = Espacio(cliente_id)
    espacio.ruta(SESION).parent.mkdir(parents=True, exist_ok=True)
    try:
        from neonize.client import NewClient
        from neonize.events import ConnectedEv, HistorySyncEv, LoggedOutEv, MessageEv, PairStatusEv
    except BaseException as error:  # noqa: BLE001 - ImportError o la librería nativa
        logger.error("No se pudo importar neonize: %r", error)
        publicar(espacio, "error", detalle=f"neonize: {error!r}")
        return 1

    client = NewClient(str(espacio.ruta(SESION)))
    publicar(espacio, "arrancando")

    # Sin cámara a la mano: "Vincular con número de teléfono". Se pide UNA vez,
    # con el cliente ya corriendo (cuando WhatsApp manda el primer QR).
    telefono = "".join(c for c in os.environ.get("AGENTE_VINCULAR_TELEFONO", "") if c.isdigit())
    emparejar = Emparejar(espacio, telefono, lambda tel: client.PairPhone(tel, True))

    @client.qr
    def on_qr(_c, data_qr):
        codigo = data_qr.decode() if isinstance(data_qr, (bytes, bytearray)) else str(data_qr)
        if emparejar.al_recibir_qr(codigo):
            threading.Thread(target=emparejar.pedir_codigo, daemon=True).start()

    @client.event(PairStatusEv)
    def on_pair(_c, event):
        numero = _usuario(str(getattr(event, "ID", "") or ""))
        publicar(espacio, "vinculado", numero=numero, negocio=getattr(event, "BusinessName", ""))
        if not numero_permitido(espacio, numero):
            publicar(espacio, "numero_ajeno", numero=numero)

    @client.event(ConnectedEv)
    def on_connected(_c, _e):
        estado = leer_estado(espacio)
        if estado.get("estado") != "numero_ajeno":
            publicar(espacio, "conectado", mensajes=len(historial.cargar(espacio)))

    @client.event(HistorySyncEv)
    def on_history(_c, event):
        try:
            n = importar(espacio, mensajes_del_historial(getattr(event, "Data", None)))
            logger.info("Historial: %s mensajes nuevos", n)
        except Exception:
            logger.exception("Error importando el historial")

    @client.event(MessageEv)
    def on_message(_c, event):
        try:
            if (m := mensaje_vivo(event, client.get_pn_from_lid)):
                importar(espacio, [m])
        except Exception:
            logger.exception("Error guardando un mensaje")

    @client.event(LoggedOutEv)
    def on_logout(_c, _e):
        publicar(espacio, "desconectado")

    client.connect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
