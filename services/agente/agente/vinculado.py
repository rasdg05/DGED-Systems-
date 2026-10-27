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
from pathlib import Path

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


ORDEN = "vinculado/orden.json"
VIGENCIA_CODIGO_S = 150  # un código de 8 vale un par de minutos; pasado eso, otra vez el QR


def ordenar(espacio: Espacio, accion: str) -> None:
    """La web le deja una orden al lector (otro proceso, mismo volumen): `qr_nuevo` o `codigo`."""
    espacio.escribir_json(ORDEN, {"accion": accion, "en": time.time()})


def tomar_orden(espacio: Espacio) -> str | None:
    ruta = espacio.ruta(ORDEN)
    if not ruta.exists():
        return None
    try:
        orden = espacio.leer_json(ORDEN, {}) or {}
    finally:
        ruta.unlink(missing_ok=True)
    return orden.get("accion")


def borrar_sesion(espacio: Espacio) -> None:
    """Sesión a medias fuera: al reiniciar, WhatsApp da un QR nuevo (como el botón de Gestor)."""
    carpeta = espacio.ruta(SESION).parent
    for f in carpeta.glob(Path(SESION).name + "*"):
        f.unlink(missing_ok=True)


class Emparejar:
    """Qué se le enseña al negocio para vincular. Como en Gestor: **el QR siempre**, y el
    código de 8 solo cuando alguien lo pide con el botón.

    Antes el código se pedía solo en cada arranque, y cada redespliegue gastaba uno: el
    2026-10-27 WhatsApp contestó 429 rate-overlimit a Finca Emiliano y, encima, el respaldo
    anunciaba el QR sin publicarlo ("Preparando" sin fin).
    """

    def __init__(self, espacio: Espacio, telefono: str, pedir, reloj=time.time):
        self.espacio, self.telefono, self.pedir, self.reloj = espacio, telefono, pedir, reloj
        self.ultimo_qr = ""
        self.codigo_en = 0.0  # cuándo se enseñó el último código; 0 = se enseña el QR

    def _codigo_vigente(self) -> bool:
        return bool(self.codigo_en) and self.reloj() - self.codigo_en < VIGENCIA_CODIGO_S

    def al_recibir_qr(self, qr: str) -> None:
        self.ultimo_qr = qr
        if not self._codigo_vigente():
            self.codigo_en = 0.0
            publicar(self.espacio, "esperando_qr", qr=qr)

    def volver_al_qr(self, detalle: str = "") -> None:
        self.codigo_en = 0.0
        if self.ultimo_qr:
            publicar(self.espacio, "esperando_qr", qr=self.ultimo_qr, **({"detalle": detalle} if detalle else {}))

    def pedir_codigo(self) -> None:
        if not self.telefono:
            self.volver_al_qr("Falta el número del negocio para pedir el código: use el QR.")
            return
        try:
            codigo = self.pedir(self.telefono)
        except Exception as error:
            logger.warning("No se pudo pedir el código de vinculación: %r", error)
            espera = ("WhatsApp pidió esperar antes de dar otro código." if "429" in repr(error)
                      else "No se pudo pedir el código.")
            self.volver_al_qr(f"{espera} Mientras, escanee el QR desde otra pantalla.")
            return
        self.codigo_en = self.reloj()
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
    # El número para el código de 8 (solo si alguien lo pide): el de la variable o el del alta.
    telefono = "".join(c for c in (os.environ.get("AGENTE_VINCULAR_TELEFONO", "")
                                   or str(espacio.config().get("numero_negocio", ""))) if c.isdigit())
    emparejar = Emparejar(espacio, telefono, lambda tel: client.PairPhone(tel, True))
    tomar_orden(espacio)  # una orden vieja de antes del arranque ya se cumplió con el arranque

    @client.qr
    def on_qr(_c, data_qr):
        emparejar.al_recibir_qr(data_qr.decode() if isinstance(data_qr, (bytes, bytearray)) else str(data_qr))

    def atender_ordenes():  # las órdenes de la web: QR nuevo o código de 8
        while True:
            time.sleep(2)
            try:
                accion = tomar_orden(espacio)
                if accion == "qr_nuevo":
                    logger.warning("QR nuevo pedido: se borra la sesión a medias y el lector reinicia")
                    borrar_sesion(espacio)
                    publicar(espacio, "arrancando")
                    os._exit(0)  # arrancar.sh lo vuelve a levantar en 5 s; la web sigue
                elif accion == "codigo":
                    emparejar.pedir_codigo()
                elif accion == "qr":
                    emparejar.volver_al_qr()
            except Exception:
                logger.exception("Error atendiendo una orden de la web")

    threading.Thread(target=atender_ordenes, daemon=True).start()

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
