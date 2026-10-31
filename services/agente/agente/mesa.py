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

Órdenes: la tabla de `ordenes.py` (más de 60, del 2026-10-31: clientes, rondas y
borradores, envío, precios, calendario y la mesa misma); lo que hace cada una,
en `capacidades.py`. *ayuda* las enseña por tema.
"""
from __future__ import annotations

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
NOVEDADES = "mesa/novedades.json"
#: Lo nuevo de la mesa, una vez por administradora en su siguiente reporte (sube la clave al cambiar).
NOVEDAD = ("2026-10-31", "Novedad: ahora me entiende más. Pruebe: «contestaron», «ficha …1234», «cotiza 8 personas "
                         "del 9 al 11 de noviembre», «huecos», «borradores» y «aprueba 1 3», «no le escribas a …1234», "
                         "«lo llevo …1234», «cerró …1234 15000», «dile a …1234 que …» y «deshaz». "
                         "Escriba ayuda para ver todo.")
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


def _dicho(texto: str | None) -> str:
    """Lo que dijo el cliente en una línea de WhatsApp: sin saltos, y el medio dicho como medio."""
    t = " / ".join(r.strip() for r in (texto or "").splitlines() if r.strip())
    return (t[:60] + ("…" if len(t) > 60 else "")) if t else "(foto o audio)"


def reporte(espacio: Espacio) -> str:
    from . import calendario, capacidades, enviador, historial, operacion, semaforo

    hilos = clientes(espacio, historial.hilos(espacio))
    filas = capacidades._filas(espacio, hilos)  # sin los que la dueña ya marcó como contestados
    res = semaforo.resumen(filas)
    por_aprobar = capacidades._por_aprobar(espacio)  # sin lo descartado
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
    from . import desenlace, tiempos
    if (al_numero := tiempos.linea(tiempos.al_numero(hilos, semanas=1))):
        lineas.append(al_numero)
    semana = datetime.now(timezone.utc).timestamp() - 7 * 86400
    lineas += [desenlace.linea(r) for r in desenlace.de_rondas(espacio, hilos)[:2] if (r["desde"] or 0) >= semana]
    calientes = [f for f in filas if f.estado == "contesto_ronda" and f.color in ("rojo", "ambar")]
    if calientes:
        lineas.append(f"Contestaron al seguimiento y esperan respuesta: {len(calientes)}. Van primero.")
    # Las respuestas a la ronda primero aunque sean ámbar (< 2 h): son las más calientes.
    urgentes = (calientes + [f for f in filas if f.color == "rojo" and f.estado in ("nos_toca", "sin_atender", "promesa")])[:5]
    if urgentes:
        lineas.append("Lo más urgente:")
        lineas += [f"· …{f.hilo[-4:]} {semaforo.ETIQUETA[f.estado].lower()}, {operacion._horas_txt(f.horas)}: "
                   f"{_dicho(f.dicho)}" for f in urgentes]
    if por_aprobar:
        ultima = next((r for r in reversed(_rondas_cargadas(espacio))), None)
        if ultima:
            lineas.append(f"Para mandar los seguimientos de la ronda {ultima['nombre']}, conteste: aprueba la ronda")
    lineas.append("Escriba ayuda para ver lo que puede pedirme.")
    return "\n".join(lineas)


# --------------------------------------------------------------------------- #
#  Las órdenes                                                                 #
# --------------------------------------------------------------------------- #
def leer_orden(texto: str) -> dict | None:
    """La orden que pidió una administradora (`ordenes.TABLA`), o None."""
    from . import ordenes
    return ordenes.leer(texto)


def _anotar(espacio: Espacio, hilo: str, orden: str, resultado: str) -> None:
    espacio.agregar_linea(BITACORA, {"de": f"…{hilo[-4:]}", "orden": orden, "resultado": resultado[:300],
                                     "en": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def encolar_aprobadas(espacio: Espacio) -> int:
    """Lo ya aprobado que todavía no pasó por la cola entra ahora, si sus candados lo
    dejan (lo aprobado con el envío en pausa sale al encender, sin aprobar de nuevo)."""
    from . import agente, canal, enviador
    ya = agente.aprobadas(espacio)
    vistas = {e["salida"] for e in espacio.leer_lineas(enviador.COLA)}
    en_cola = set(enviador.pendientes(espacio))
    candidatas = [s for s in agente.salidas(espacio) if s.id in ya and s.requiere_aprobacion and s.id not in en_cola
                  and (s.id not in vistas or enviador.reencolable(espacio, s.id))]
    if not candidatas:
        return 0
    ctx = canal.contexto(espacio)
    n = 0
    for s in candidatas:
        s.aprobada_por = ya[s.id]
        if not canal.motivo_para_no_enviar(espacio, s, ctx):
            canal.enviar(espacio, s, ctx=ctx)
            n += 1
    return n


def ejecutar(espacio: Espacio, hilo: str, orden: dict, via: str = "") -> str:
    """Quién puede, y luego lo que hace (`capacidades.MANEJADORES`). Lo que cambia algo
    y se leyó corrigiendo una errata no se hace: se pregunta."""
    from . import capacidades, ordenes

    spec = ordenes.POR_ID[orden["orden"]]
    de = f"{via}:{_diez(hilo)}" if via else _diez(hilo)
    if spec.id in ("confirma", "cancela") and not capacidades.hay_dictado(espacio, de):
        return ""  # "mándalo" o "no lo mandes" sin un dictado enfrente es plática: no se contesta
    if spec.id not in ("dile", "confirma", "cancela"):
        capacidades.olvidar_dictado(espacio, de)  # el "mándalo" vale para lo último que se le enseñó
    if spec.quien == ordenes.QUIEN_APRUEBA and not es_quien_aprueba(espacio, hilo):
        return "Eso solo lo puede ordenar quien aprueba las cotizaciones del negocio."
    alta = espacio.leer_json("alta.json", {}) or {}
    nombre = (alta.get("aprobador") or "").strip() if es_quien_aprueba(espacio, hilo) else ""
    pedido = capacidades.Pedido(espacio, hilo, orden, nombre, via)
    antes = len(espacio.leer_lineas(capacidades.ACCIONES))
    if orden.get("corregida") and spec.cambia:
        respuesta = f"¿Quiso decir «{orden.get('como', spec.id)}»? Escríbalo así y lo hago."
    else:
        respuesta = capacidades.MANEJADORES[spec.id](pedido)
    if spec.cambia and spec.id != "deshaz" and len(espacio.leer_lineas(capacidades.ACCIONES)) == antes:
        # Toda orden que cambia algo, aunque no haya cambiado nada (cliente no encontrado, pregunta), queda como
        # la última: un "deshaz" después no revierte la de antes (tercera revisión).
        capacidades._accion(pedido, None)
    return respuesta


def por_fuera(espacio: Espacio, texto: str, *, solo_lectura: bool, via: str) -> dict:
    """La misma mesa sin WhatsApp: el panel, el taller (`local.py mesa`) o el MCP.

    Corre como quien aprueba según el alta (sus listas numeradas son las mismas que
    en su WhatsApp). `solo_lectura` no deja pasar nada que cambie algo: así el MCP
    de afinación y una sesión de código miran sin tocar. Queda en la bitácora con su vía."""
    from . import ordenes
    orden = leer_orden(texto)
    if orden is None:
        quiso = ordenes.parece_orden(texto)
        return {"orden": None, "respuesta": (f"No entendí la orden. ¿Quiso decir: {ordenes.POR_ID[quiso].ayuda.split(':')[0]}?"
                                             if quiso else "No es una orden de la mesa. Escriba ayuda.")}
    spec = ordenes.POR_ID[orden["orden"]]
    if solo_lectura and spec.cambia:
        return {"orden": spec.id, "respuesta": "Esta vía solo lee: esa orden cambia algo y la da quien aprueba."}
    alta = espacio.leer_json("alta.json", {}) or {}
    hilo = _hilo_de(espacio, _diez(alta.get("aprobador_telefono"))) if _diez(alta.get("aprobador_telefono")) else ""
    if not hilo:
        return {"orden": spec.id, "respuesta": "El alta no tiene el teléfono de quien aprueba."}
    respuesta = ejecutar(espacio, hilo, orden, via=via)
    _anotar(espacio, hilo, f"{spec.id} ({via})", respuesta)
    return {"orden": spec.id, "respuesta": respuesta}


def atender(espacio: Espacio, m: Mensaje) -> str | None:
    """Un mensaje de una administradora al WhatsApp del negocio. Contesta una orden
    conocida (o la ayuda si parece que pide algo) y deja la respuesta en el buzón.
    `None`: no es de una administradora o no se contesta."""
    if m.del_negocio or not m.texto or not es_admin(espacio, m.hilo):
        return None
    orden = leer_orden(m.texto)
    if orden is None:
        from . import ordenes
        quiso = ordenes.parece_orden(m.texto)
        if quiso is None:
            return None  # una plática normal con la dueña: no se le contesta en automático
        respuesta = (f"No entendí la orden. ¿Quiso decir: {ordenes.POR_ID[quiso].ayuda.split(':')[0]}? "
                     "Escriba ayuda para ver todo.")
        _anotar(espacio, m.hilo, "no_entendida", respuesta)
        encolar(espacio, m.hilo, respuesta)
        return respuesta
    try:
        respuesta = ejecutar(espacio, m.hilo, orden)
        if not respuesta:
            return None
    except Exception as error:  # noqa: BLE001 - una orden que truena no tumba al lector
        respuesta = f"No pude con esa orden ({type(error).__name__}). Quedó escrito para revisarlo."
        _anotar(espacio, m.hilo, f"error:{orden['orden']}", repr(error))
        encolar(espacio, m.hilo, respuesta)
        return respuesta
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
    silenciadas = set(espacio.config().get("reportes_silenciados", []) or [])  # "silencia los reportes"
    admins = administradores(espacio) - silenciadas
    if not toca or not admins:
        return 0
    for h in toca:
        hechos[f"{ahora.date()}-{h}"] = ahora.isoformat(timespec="seconds")
    espacio.escribir_json(REPORTES, hechos)
    texto = reporte(espacio)
    vistas = espacio.leer_json(NOVEDADES, {}) or {}
    for admin in sorted(admins):
        nuevo = vistas.get(admin) != NOVEDAD[0]
        encolar(espacio, _hilo_de(espacio, admin), texto + (f"\n\n{NOVEDAD[1]}" if nuevo else ""))
        vistas[admin] = NOVEDAD[0]
    espacio.escribir_json(NOVEDADES, vistas)
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
