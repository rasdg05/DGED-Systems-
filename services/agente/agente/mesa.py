"""La mesa de la dueña: su asistente por WhatsApp, como `dueno.py` de Gestor Morelos.

Dueño, 2026-10-27: *"el agente asistente debe tener las mismas o más
capacidades que el de Gestor Morelos. El número de la otra administradora (...)
con ella le puedes enviar los reportes de los agentes autónomos, seguimientos y
todo eso"*.

Las administradoras escriben al WhatsApp del negocio y el asistente les
contesta por el mismo dispositivo vinculado. Tres reglas:

- **Una administradora no es clienta.** Su plática no entra al semáforo, a las
  rondas ni al envío a clientes (`clientes()`); un enjambre no le escribe
  seguimientos. Son administradoras el teléfono de quien aprueba (alta) y los
  de `config.json` → `administradores`.
- **Lo que solo decide quien aprueba** (aprobar una ronda, encender o pausar el
  envío) lo puede ordenar solo el teléfono de quien aprueba según el alta, y
  queda escrito con su nombre (`mesa/bitacora.jsonl`). Aprobar por aquí es lo
  mismo que en la pantalla: cada salida queda aprobada a su nombre y pasa por
  los mismos candados al enviarse.
- **La mesa solo escribe a administradoras**: su buzón (`mesa/salida.jsonl`) se
  revisa contra la lista al despachar, no al escribir (LXVII).

Reportes: a las `HORAS_REPORTE` (hora de México), uno por horario y por día, a
cada administradora: semáforo, cola, envíos y lo que espera a la dueña.

Órdenes (sin acentos ni mayúsculas): *ayuda*, *estado* (o *reporte*),
*pendientes*, *cola*, *aprueba la ronda* (la última cargada) o *aprueba la
ronda <nombre>*, *enciende el envío*, *pausa el envío*.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .espacio import Espacio
from .historial import Mensaje

ZONA = ZoneInfo("America/Mexico_City")
SALIDA = "mesa/salida.jsonl"
ENVIADOS = "mesa/enviados.jsonl"
BITACORA = "mesa/bitacora.jsonl"
REPORTES = "mesa/reportes.json"
HORAS_REPORTE = (9, 19)
TOPE_DIA = 40  # mensajes de la mesa por día, por si algo se encicla


# --------------------------------------------------------------------------- #
#  Quién es administradora                                                     #
# --------------------------------------------------------------------------- #
def _diez(telefono) -> str:
    """Los últimos 10 dígitos: 52 777…, 521 777… y 777… son el mismo número."""
    digitos = "".join(c for c in str(telefono or "") if c.isdigit())
    return digitos[-10:] if len(digitos) >= 10 else ""


def administradores(espacio: Espacio) -> set[str]:
    alta = espacio.leer_json("alta.json", {}) or {}
    numeros = [alta.get("aprobador_telefono")] + list(espacio.config().get("administradores", []) or [])
    return {d for n in numeros if (d := _diez(n))}


def es_admin(espacio: Espacio, hilo: str) -> bool:
    return bool(_diez(hilo)) and _diez(hilo) in administradores(espacio)


def es_quien_aprueba(espacio: Espacio, hilo: str) -> bool:
    alta = espacio.leer_json("alta.json", {}) or {}
    return bool(_diez(hilo)) and _diez(hilo) == _diez(alta.get("aprobador_telefono"))


def clientes(espacio: Espacio, hilos: dict) -> dict:
    """Las pláticas sin las de las administradoras: lo único que ven el semáforo,
    las rondas y el envío a clientes."""
    admins = administradores(espacio)
    return {h: ms for h, ms in hilos.items() if _diez(h) not in admins}


# --------------------------------------------------------------------------- #
#  Lo que dice el reporte                                                      #
# --------------------------------------------------------------------------- #
def _hoy(espacio: Espacio) -> list[dict]:
    from . import enviador
    hoy = datetime.now(ZONA).date()
    return [e for e in espacio.leer_lineas(enviador.ENVIADOS)
            if e.get("cuando") and datetime.fromisoformat(e["cuando"]).astimezone(ZONA).date() == hoy]


def _rondas_cargadas(espacio: Espacio) -> list[dict]:
    carpeta = espacio.ruta("rondas")
    if not carpeta.exists():
        return []
    rondas_ = [espacio.leer_json(f"rondas/{p.name}", {}) or {} for p in carpeta.glob("*.json")]
    return sorted((r for r in rondas_ if r.get("nombre")), key=lambda r: r.get("cargada", ""))


def reporte(espacio: Espacio) -> str:
    from . import agente, calendario, enviador, historial, operacion, semaforo

    filas = semaforo.leer(clientes(espacio, historial.hilos(espacio)))
    res = semaforo.resumen(filas)
    por_aprobar = [s for s in agente.salidas(espacio) if s.requiere_aprobacion and not s.aprobada_por]
    hoy = _hoy(espacio)
    _, titulo, _ = operacion.estado_canal(espacio)
    lineas = [f"Reporte de su asistente · {datetime.now(ZONA):%d/%m %H:%M}",
              f"Semáforo: {res['rojo']} urgentes, {res['ambar']} para hoy, {res['seguimiento']} para dar seguimiento.",
              f"Envío: {titulo}. Hoy salieron {sum(1 for e in hoy if e.get('enviado'))}, "
              f"en cola {len(enviador.pendientes(espacio))}, esperan su sí {len(por_aprobar)}."]
    no_salieron = [e for e in hoy if not e.get("enviado")]
    if no_salieron:
        lineas.append(f"No salieron hoy: {len(no_salieron)} (el cliente escribió antes, fecha apartada o envío en pausa).")
    if not calendario.Ocupacion.de(espacio).configurada:
        lineas.append("Calendario: sin conectar. Las rondas no ofrecen fechas hasta que se conecte.")
    urgentes = [f for f in filas if f.color == "rojo" and f.estado in ("nos_toca", "sin_atender", "promesa")][:5]
    if urgentes:
        lineas.append("Lo más urgente:")
        lineas += [f"· …{f.hilo[-4:]} {semaforo.ETIQUETA[f.estado].lower()}, {operacion._horas_txt(f.horas)}: "
                   f"{(f.dicho or '')[:60]}" for f in urgentes]
    if por_aprobar:
        ultima = next((r for r in reversed(_rondas_cargadas(espacio))), None)
        if ultima:
            lineas.append(f"Para mandar los seguimientos de la ronda {ultima['nombre']}, conteste: aprueba la ronda")
    lineas.append("Escriba ayuda para ver lo que puede pedirme.")
    return "\n".join(lineas)


def _pendientes(espacio: Espacio) -> str:
    from . import historial, operacion, semaforo
    filas = [f for f in semaforo.leer(clientes(espacio, historial.hilos(espacio))) if f.color in ("rojo", "ambar")]
    if not filas:
        return "No hay pendientes urgentes."
    return "Pendientes, el más urgente primero:\n" + "\n".join(
        f"· …{f.hilo[-4:]} {semaforo.ETIQUETA[f.estado].lower()}, {operacion._horas_txt(f.horas)}: {(f.dicho or '')[:60]}"
        for f in filas[:12]) + (f"\n…y {len(filas) - 12} más en la app." if len(filas) > 12 else "")


def _cola(espacio: Espacio) -> str:
    from . import agente, enviador, operacion
    _, titulo, texto = operacion.estado_canal(espacio)
    por_aprobar = [s for s in agente.salidas(espacio) if s.requiere_aprobacion and not s.aprobada_por]
    hoy = _hoy(espacio)
    return (f"{titulo}. {texto}\nEsperan su sí: {len(por_aprobar)} · en cola: {len(enviador.pendientes(espacio))} · "
            f"enviados hoy: {sum(1 for e in hoy if e.get('enviado'))}")


AYUDA = ("Puede escribirme:\n· estado: el reporte del día\n· pendientes: a quién contestar primero\n"
         "· cola: lo que espera su sí y lo que sale\n· aprueba la ronda: manda los seguimientos que preparó el equipo\n"
         "· enciende el envío / pausa el envío\nLos mensajes salen uno cada 40 segundos, de 9 a 9, y antes de cada uno "
         "se revisa si el cliente ya escribió o si la fecha ya se apartó.")


# --------------------------------------------------------------------------- #
#  Las órdenes                                                                 #
# --------------------------------------------------------------------------- #
def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[¿?¡!.,/]", " ", t).split())


_ORDENES = (
    ("ayuda", re.compile(r"^(?:ayuda|help|menu|que puedes hacer|comandos)$")),
    ("estado", re.compile(r"^(?:estado|reporte|resumen|como vamos|como va todo)$")),
    ("pendientes", re.compile(r"^(?:pendientes|urgentes|a quien contesto)$")),
    ("cola", re.compile(r"^(?:cola|envios|envio)$")),
    ("aprueba", re.compile(r"^(?:aprueba|apruebo|aprobar|si aprueba|manda|mandala)\s+(?:la\s+)?ronda(?:\s+(?P<nombre>[a-z0-9-]+))?$")),
    ("enciende", re.compile(r"^(?:enciende|prende|activa|encender|prender)\s+(?:el\s+)?envio$")),
    ("pausa", re.compile(r"^(?:pausa|apaga|deten|para|deten el|pausar)\s+(?:el\s+)?envio$")),
)


def leer_orden(texto: str) -> dict | None:
    t = _norm(texto)
    for orden, patron in _ORDENES:
        if (m := patron.match(t)):
            return {"orden": orden, **{k: v for k, v in m.groupdict().items() if v}}
    return None


def _anotar(espacio: Espacio, hilo: str, orden: str, resultado: str) -> None:
    espacio.agregar_linea(BITACORA, {"de": f"…{hilo[-4:]}", "orden": orden, "resultado": resultado[:300],
                                     "en": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def encolar_aprobadas(espacio: Espacio) -> int:
    """Lo ya aprobado que todavía no pasó por la cola entra ahora, si sus candados lo
    dejan (lo aprobado con el envío en pausa sale al encender, sin aprobar de nuevo)."""
    from . import agente, canal, enviador
    ya = agente.aprobadas(espacio)
    vistas = {e["salida"] for e in espacio.leer_lineas(enviador.COLA)}
    n = 0
    for s in agente.salidas(espacio):
        if s.id in ya and s.id not in vistas and s.requiere_aprobacion:
            s.aprobada_por = ya[s.id]
            if not canal.motivo_para_no_enviar(espacio, s):
                canal.enviar(espacio, s)
                n += 1
    return n


def ejecutar(espacio: Espacio, hilo: str, orden: dict) -> str:
    from . import agente, canal, perfil

    o = orden["orden"]
    if o == "ayuda":
        return AYUDA
    if o == "estado":
        return reporte(espacio)
    if o == "pendientes":
        return _pendientes(espacio)
    if o == "cola":
        return _cola(espacio)
    if not es_quien_aprueba(espacio, hilo):
        return "Eso solo lo puede ordenar quien aprueba las cotizaciones del negocio."
    alta = espacio.leer_json("alta.json", {}) or {}
    nombre = (alta.get("aprobador") or "").strip()
    if o in ("enciende", "pausa"):
        config = espacio.config()
        antes = {"canal": config.get("canal", "oficial"), "encendido": config.get("encendido", "sombra")}
        config.update(canal="vinculado", encendido="sin_cifra") if o == "enciende" else config.update(encendido="sombra")
        espacio.escribir_json("config.json", config)
        espacio.agregar_linea("cambios_canal.jsonl", {"antes": antes, "ahora": {"canal": config.get("canal"),
                                                                                "encendido": config["encendido"]},
                                                     "por": nombre, "via": "mesa",
                                                     "en": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        if o == "pausa":
            return "Envío en pausa. No sale nada hasta que escriba: enciende el envío"
        n = encolar_aprobadas(espacio)
        return ("Envío encendido. Sale lo que usted aprueba, uno cada 40 segundos, de 9 a 9."
                + (f" Ya van a la cola {n} que había aprobado." if n else ""))
    # aprueba la ronda
    cargadas = _rondas_cargadas(espacio)
    ronda = next((r for r in cargadas if r["nombre"] == orden.get("nombre")), None) if orden.get("nombre") \
        else (cargadas[-1] if cargadas else None)
    if ronda is None:
        return "No encontré esa ronda." if orden.get("nombre") else "No hay rondas cargadas."
    try:
        aprobadas, encoladas, no_salen = 0, 0, {}
        ya = agente.aprobadas(espacio)
        for salida_id in ronda.get("salidas", []):
            if salida_id in ya:
                continue
            try:
                salida = agente.aprobar_salida(espacio, salida_id, nombre)
            except KeyError:
                continue
            aprobadas += 1
            if (motivo := canal.motivo_para_no_enviar(espacio, salida)):
                from .operacion import motivo_amable
                no_salen[motivo_amable(motivo)] = no_salen.get(motivo_amable(motivo), 0) + 1
                continue
            canal.enviar(espacio, salida)
            encoladas += 1
    except perfil.AprobacionInvalida as error:
        return f"No se pudo aprobar: {error}"
    encoladas += encolar_aprobadas(espacio)
    texto = (f"Aprobé {aprobadas} mensaje{'' if aprobadas == 1 else 's'} de la ronda {ronda['nombre']} "
             f"a su nombre. En cola: {encoladas}.")
    if no_salen:
        texto += " No salen por ahora: " + "; ".join(f"{k} ({v})" for k, v in no_salen.items()) + "."
        c = espacio.config()
        if c.get("encendido") != "sin_cifra" or c.get("canal") != "vinculado":
            texto += " Para mandarlos, escriba: enciende el envío"
    return texto


def atender(espacio: Espacio, m: Mensaje) -> str | None:
    """Un mensaje de una administradora al WhatsApp del negocio. Contesta una orden
    conocida (o la ayuda si parece que pide algo) y deja la respuesta en el buzón.
    `None`: no es de una administradora o no se contesta."""
    if m.del_negocio or not m.texto or not es_admin(espacio, m.hilo):
        return None
    orden = leer_orden(m.texto)
    if orden is None:
        return None  # una plática normal con la dueña: no se le contesta en automático
    respuesta = ejecutar(espacio, m.hilo, orden)
    _anotar(espacio, m.hilo, orden["orden"], respuesta)
    encolar(espacio, m.hilo, respuesta)
    return respuesta


# --------------------------------------------------------------------------- #
#  Buzón y reportes                                                            #
# --------------------------------------------------------------------------- #
def encolar(espacio: Espacio, para: str, texto: str) -> None:
    espacio.agregar_linea(SALIDA, {"id": uuid.uuid4().hex[:12], "para": para, "texto": texto,
                                   "creada": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def reporte_si_toca(espacio: Espacio, ahora: datetime | None = None) -> int:
    """El reporte de la mañana y de la tarde, una vez por horario y por día, a cada administradora."""
    ahora = (ahora or datetime.now(timezone.utc)).astimezone(ZONA)
    hechos = espacio.leer_json(REPORTES, {}) or {}
    toca = [h for h in HORAS_REPORTE if ahora.hour >= h and f"{ahora.date()}-{h}" not in hechos]
    admins = administradores(espacio)
    if not toca or not admins:
        return 0
    for h in toca:
        hechos[f"{ahora.date()}-{h}"] = ahora.isoformat(timespec="seconds")
    espacio.escribir_json(REPORTES, hechos)
    texto = reporte(espacio)
    for admin in sorted(admins):
        encolar(espacio, _hilo_de(espacio, admin), texto)
    return len(admins)


def _hilo_de(espacio: Espacio, diez: str) -> str:
    """El número como lo escribe WhatsApp en el historial (521 + 10 en México);
    si no hay plática todavía, 521 + los 10 dígitos."""
    from . import historial
    return next((h for h in historial.hilos(espacio) if _diez(h) == diez), "521" + diez)


def despachar(espacio: Espacio, mandar, ahora: datetime | None = None) -> int:
    """Manda lo del buzón. Se revisa aquí que el destino sea administradora (LXVII):
    la mesa nunca le escribe a un cliente."""
    ahora = ahora or datetime.now(timezone.utc)
    hechos = {e["id"] for e in espacio.leer_lineas(ENVIADOS)}
    hoy = ahora.astimezone(ZONA).date()
    del_dia = sum(1 for e in espacio.leer_lineas(ENVIADOS) if e.get("enviado")
                  and datetime.fromisoformat(e["cuando"]).astimezone(ZONA).date() == hoy)
    n = 0
    for e in espacio.leer_lineas(SALIDA):
        if e["id"] in hechos:
            continue
        registro = {"id": e["id"], "cuando": ahora.isoformat(timespec="seconds")}
        if not es_admin(espacio, e["para"]):
            espacio.agregar_linea(ENVIADOS, {**registro, "enviado": False, "motivo": "no es administradora"})
            continue
        if del_dia >= TOPE_DIA:
            break
        try:
            wamid = mandar(e["para"], e["texto"])
        except Exception as error:  # noqa: BLE001 - queda escrito y no se reintenta solo
            espacio.agregar_linea(ENVIADOS, {**registro, "enviado": False, "motivo": f"falló: {type(error).__name__}"})
            continue
        espacio.agregar_linea(ENVIADOS, {**registro, "enviado": True})
        from .enviador import al_historial
        al_historial(espacio, e["para"], e["texto"], ahora, wamid, f"mesa-{e['id']}")
        del_dia += 1
        n += 1
    return n
