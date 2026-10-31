"""Lo que hace cada orden de la mesa (`ordenes.TABLA`), con lo que ya sabe el agente.

Corrida del 2026-10-31 (dueño: *"por lo menos 50 funciones nuevas (...) sácalos
de gestor Morelos"*). Cada orden reusa una pieza que ya existe —semáforo,
cotizador, calendario, rondas, perfil, desenlace, tiempos, gasto—; aquí no se
calcula nada que la app no calcule ya. Lo de Gestor que se trae:

- **Listas numeradas** (*contesta 3* de Gestor): cada lista de clientes o de
  borradores queda guardada por administradora (`mesa/listas.json`), y *"ficha
  2"* o *"aprueba 1 3"* se refieren a ESA lista, no a una que cambió mientras
  tanto.
- ***lo tomo*, *nota*, *cerró*, *dile que*** (`cierre.py`, `consultas.py`):
  la dueña se queda con un cliente, deja algo en su ficha, asienta una renta o
  le dicta un mensaje. Lo dictado sale con SUS palabras y a su nombre, por los
  mismos candados del canal.
- ***deshaz*** (`dueno.py`): toda orden que cambia algo deja escrito cómo
  revertirse (`mesa/acciones.jsonl`); lo que ya salió por WhatsApp no se
  deshace y se dice.
- **Las marcas mandan en el código, no en la memoria** (regla de `CLAUDE.md`):
  *no le escribas* y *lo llevo yo* las revisa `canal.motivo_para_no_enviar`
  justo antes de cada envío y `rondas.validar` al cargar; un borrador
  descartado no sale aunque estuviera aprobado; un apartado a mano lo ve el
  calendario (`calendario.Ocupacion`).

Todo lo que contesta va a una administradora (el buzón de la mesa lo revisa,
LXVII): por eso aquí sí hay cifras. A un cliente solo le llega lo que dicta la
dueña o lo que ella aprueba.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import ordenes
from .espacio import Espacio

ZONA = ZoneInfo("America/Mexico_City")
MARCAS = "mesa/marcas.jsonl"
NOTAS = "mesa/notas.jsonl"
RESERVAS = "mesa/reservas.jsonl"
RECUERDA = "mesa/recuerda.jsonl"
ACCIONES = "mesa/acciones.jsonl"
LISTAS = "mesa/listas.json"
DESCARTES = "descartes_salida.jsonl"
MANUAL = "calendario/manual.jsonl"
DICTADOS = "mesa/dictados.json"
POR_PAGINA = 10
MINUTOS_LISTA = 30      # "ficha 2", "aprueba 1 3": una lista más vieja ya no es la que ella tiene enfrente
MINUTOS_DICTADO = 10    # "sí, mándalo" vale para lo que se le enseñó hace poco
MINUTOS_DESHAZ = 30
SEMANAS_HUECOS = 8

NO_SE_LE_ESCRIBE = "la dueña pidió no escribirle a este cliente"
LO_LLEVA = "lo lleva una persona del negocio"
DESCARTADA = "descartada por una persona del negocio"


@dataclass
class Pedido:
    espacio: Espacio
    hilo: str              # de quien escribe (una administradora)
    orden: dict
    nombre: str = ""       # quien aprueba según el alta, si es ella
    via: str = ""          # "" = su WhatsApp; http, taller, mcp: otra vía con sus propias listas

    @property
    def de(self) -> str:
        """De quién son las listas, las acciones y el deshaz. Otra vía (el MCP, el panel)
        no le cambia a la dueña a quién se refiere "1" en su WhatsApp (revisión adversarial)."""
        from .mesa import _diez
        return f"{self.via}:{_diez(self.hilo)}" if self.via else _diez(self.hilo)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _id() -> str:
    return uuid.uuid4().hex[:10]


def _local(iso: str) -> datetime:
    """Una hora guardada en UTC, como la lee la dueña (hora de México)."""
    return datetime.fromisoformat(iso).astimezone(ZONA)


def _hoy() -> date:
    return datetime.now(ZONA).date()


def _txt(texto: str | None, largo: int = 60) -> str:
    t = " / ".join(r.strip() for r in (texto or "").splitlines() if r.strip())
    return (t[:largo] + ("…" if len(t) > largo else "")) if t else "(foto o audio)"


def _mask(hilo: str) -> str:
    return f"…{hilo[-4:]}"


def _plural(n: int, uno: str, varios: str | None = None) -> str:
    return f"{n} {uno if n == 1 else (varios or uno + 's')}"


# --------------------------------------------------------------------------- #
#  Marcas por cliente: no escribir, lo llevo, atendido                         #
# --------------------------------------------------------------------------- #
def marcas(espacio: Espacio) -> dict[str, dict[str, dict]]:
    """Por hilo, la última marca de cada tipo que sigue puesta."""
    vigentes: dict[str, dict[str, dict]] = {}
    for r in espacio.leer_lineas(MARCAS):
        if r.get("valor"):
            vigentes.setdefault(r["hilo"], {})[r["tipo"]] = r
        else:
            vigentes.get(r["hilo"], {}).pop(r["tipo"], None)
    return {h: m for h, m in vigentes.items() if m}


def marcar(espacio: Espacio, hilo: str, tipo: str, valor: bool, por: str) -> dict:
    registro = {"hilo": hilo, "tipo": tipo, "valor": valor, "por": por, "en": _ahora(),
                "ts": int(datetime.now(timezone.utc).timestamp())}
    espacio.agregar_linea(MARCAS, registro)
    return registro


def no_escribir(espacio: Espacio, hilo: str, todas: dict | None = None) -> str:
    """'' si al cliente se le puede escribir; si no, por qué. Lo revisa el canal antes de
    cada envío y las rondas al cargar (`canal.motivo_para_no_enviar`, `rondas.validar`)."""
    m = (todas if todas is not None else marcas(espacio)).get(hilo, {})
    if "no_escribir" in m:
        return NO_SE_LE_ESCRIBE
    if "lo_llevo" in m:
        return LO_LLEVA
    return ""


def atendidos(espacio: Espacio, hilos: dict) -> set[str]:
    """Los que la dueña marcó como contestados y no han vuelto a escribir desde entonces."""
    salida = set()
    for hilo, m in marcas(espacio).items():
        if "atendido" not in m:
            continue
        del_cliente = [x.ts for x in hilos.get(hilo, []) if not x.del_negocio]
        if not del_cliente or max(del_cliente) <= int(m["atendido"].get("ts") or 0):
            salida.add(hilo)
    return salida


def descartadas(espacio: Espacio) -> set[str]:
    vivas: set[str] = set()
    for r in espacio.leer_lineas(DESCARTES):
        (vivas.add if r.get("valor", True) else vivas.discard)(r["id"])
    return vivas


def descartada(espacio: Espacio, salida_id: str) -> bool:
    return salida_id in descartadas(espacio)


# --------------------------------------------------------------------------- #
#  Apartados a mano en el calendario                                           #
# --------------------------------------------------------------------------- #
def apartados_a_mano(espacio: Espacio) -> list[dict]:
    """Los bloques que la dueña apartó por la mesa y siguen puestos (los lee `calendario.Ocupacion`)."""
    vivos: dict[str, dict] = {}
    for r in espacio.leer_lineas(MANUAL):
        if r.get("activo", True):
            vivos[r["id"]] = r
        else:
            vivos.pop(r["id"], None)
    return list(vivos.values())


# --------------------------------------------------------------------------- #
#  Acciones con su deshacer                                                    #
# --------------------------------------------------------------------------- #
def _accion(p: Pedido, deshacer: dict | None) -> None:
    p.espacio.agregar_linea(ACCIONES, {"id": _id(), "de": p.de, "orden": p.orden["orden"], "deshacer": deshacer,
                                       "de_quien_aprueba": bool(p.nombre), "en": _ahora()})


def _deshacer(p: Pedido, d: dict) -> str:
    e = p.espacio
    tipo = d["tipo"]
    if tipo == "marca":
        if d.get("previo"):  # la marca de antes, tal cual (su hora y quién), no una nueva con la hora de hoy
            e.agregar_linea(MARCAS, dict(d["previo"], restaurada=_ahora()))
        else:
            marcar(e, d["hilo"], d["marca"], bool(d["antes"]), p.nombre or "mesa")
        return f"Listo: {_mask(d['hilo'])} quedó como estaba."
    if tipo == "nota":
        e.agregar_linea(NOTAS, {"id": d["id"], "borrada": True, "en": _ahora()})
        return "Borré la nota."
    if tipo == "reserva":
        e.agregar_linea(RESERVAS, {"id": d["id"], "borrada": True, "en": _ahora()})
        return "Quité esa renta de las asentadas."
    if tipo == "dictado":
        _tomar_dictado(p)
        return "Listo: no lo mando."
    if tipo == "manual":
        vivos = {r["id"] for r in apartados_a_mano(e)}
        if d.get("activo") is False and not set(d["ids"]) <= vivos:
            return "No lo deshice: después se liberó una parte por otro lado. Escriba calendario para ver cómo quedó."
        for i in d["ids"]:
            e.agregar_linea(MANUAL, {"id": i, "activo": d["activo"], "en": _ahora()})
        return "Listo: el calendario quedó como estaba."
    if tipo == "manual_reactivar":
        for i in d.get("pedazos", []):  # lo que quedó apartado de los lados se quita: vuelve el bloque entero
            e.agregar_linea(MANUAL, {"id": i, "activo": False, "en": _ahora()})
        for r in d["registros"]:
            e.agregar_linea(MANUAL, dict(r, activo=True, en=_ahora()))
        return "Listo: lo apartado volvió a quedar apartado."
    if tipo == "descartes":
        for i in d["ids"]:
            e.agregar_linea(DESCARTES, {"id": i, "valor": False, "por": p.nombre, "en": _ahora()})
        return f"Regresé {_plural(len(d['ids']), 'mensaje')} a los borradores."
    if tipo == "config":
        config = e.config()
        if "despues" in d and any(config.get(k) != v for k, v in d["despues"].items()):
            return "No lo deshice: alguien lo cambió después desde otro lado. Dígame cómo lo quiere."
        for k, v in d["antes"].items():
            if v is None:
                config.pop(k, None)
            else:
                config[k] = v
        e.escribir_json("config.json", config)
        if {"canal", "encendido"} & set(d["antes"]):
            e.agregar_linea("cambios_canal.jsonl", {"antes": d["despues"], "ahora": d["antes"], "por": p.nombre,
                                                   "via": "mesa (deshaz)", "en": _ahora()})
        if d.get("encolar"):
            from . import mesa
            mesa.encolar_aprobadas(e)
        return "Listo: quedó como estaba."
    if tipo == "reportes":
        actuales = list(e.config().get("reportes_silenciados", []) or [])
        nuevos = sorted(set(actuales) | {d["admin"]}) if d["antes"] else [x for x in actuales if x != d["admin"]]
        config = e.config()
        config["reportes_silenciados"] = nuevos
        e.escribir_json("config.json", config)
        return "Listo: sus reportes quedaron como estaban."
    if tipo == "recuerda":
        e.agregar_linea(RECUERDA, {"id": d["id"], "retirada": True, "en": _ahora()})
        return "Quité esa regla de la lista para la próxima versión."
    if tipo == "perfil":
        from . import perfil
        if perfil.version_activa(e) != d.get("puso"):
            return "No lo deshice: después se activó otra versión. Escriba propuestas o perfil."
        if d.get("antes") is None:
            return "No había versión activa antes; esa no se puede regresar."
        perfil.aprobar(e, d["antes"], aprobador=p.nombre)
        return f"Regresé a la versión {d['antes']}."
    return "Eso ya no se puede deshacer."


def deshaz(p: Pedido) -> str:
    """Solo su ÚLTIMA orden, de hace menos de `MINUTOS_DESHAZ`, y solo si ella todavía puede
    darla. No camina hacia atrás: un segundo *deshaz* no revierte la orden anterior
    (revisión adversarial: así una pausa de días atrás se volvía a encender)."""
    acciones = p.espacio.leer_lineas(ACCIONES)
    hechas = {a.get("deshace") for a in acciones if a.get("deshace")}
    suyas = [a for a in acciones if a.get("de") == p.de]
    if not suyas:
        return "No encontré una orden suya que deshacer."
    a = suyas[-1]
    if a.get("deshace") or a["id"] in hechas:
        return "Su última orden ya la deshice. Lo de antes se cambia con su propia orden."
    if datetime.now(timezone.utc) - datetime.fromisoformat(a["en"]) > timedelta(minutes=MINUTOS_DESHAZ):
        return f"Su última orden fue hace más de {MINUTOS_DESHAZ} minutos: ya no la deshago sola. Dígame qué cambio quiere."
    if a.get("de_quien_aprueba") and not p.nombre:
        return "Esa orden la dio quien aprueba; solo ella la puede deshacer."
    if not a.get("deshacer"):
        return ("Su última orden no se puede deshacer: lo que ya salió por WhatsApp no se regresa, y una pausa se "
                "levanta con: enciende el envío.")
    respuesta = _deshacer(p, a["deshacer"])
    if respuesta.startswith("No lo deshice"):
        return respuesta
    p.espacio.agregar_linea(ACCIONES, {"id": _id(), "de": p.de, "orden": "deshaz", "deshace": a["id"], "en": _ahora()})
    return respuesta


# --------------------------------------------------------------------------- #
#  Listas numeradas y a qué cliente se refiere                                 #
# --------------------------------------------------------------------------- #
def _guardar_lista(p: Pedido, tipo: str, items: list[str]) -> None:
    listas = p.espacio.leer_json(LISTAS, {}) or {}
    listas.setdefault(p.de, {})[tipo] = {"items": items, "en": _ahora()}
    p.espacio.escribir_json(LISTAS, listas)


def _lista_guardada(p: Pedido, tipo: str) -> list[str]:
    """La última lista de ese tipo que se le mandó, si tiene menos de `MINUTOS_LISTA`."""
    guardada = (p.espacio.leer_json(LISTAS, {}) or {}).get(p.de, {}).get(tipo) or {}
    if not guardada.get("en") or datetime.now(timezone.utc) - datetime.fromisoformat(guardada["en"]) \
            > timedelta(minutes=MINUTOS_LISTA):
        return []
    return guardada.get("items", [])


def _hilos(espacio: Espacio) -> dict:
    from . import historial, mesa
    return mesa.clientes(espacio, historial.hilos(espacio))


def resolver(p: Pedido, ref: str | None, hilos: dict | None = None) -> tuple[str | None, str]:
    """(hilo, '') o (None, por qué no). `ref`: lugar en la última lista (1–2 dígitos),
    los últimos 4 dígitos o el teléfono entero."""
    from .mesa import _diez
    hilos = hilos if hilos is not None else _hilos(p.espacio)
    ref = ref or ""
    if not ref:
        return None, "¿De qué cliente? Escriba sus últimos 4 dígitos (…1234) o su número en la lista."
    if len(ref) <= 2:
        lista = _lista_guardada(p, "clientes")
        n = int(ref)
        if not lista:
            return None, (f"No tengo una lista suya de los últimos {MINUTOS_LISTA} minutos. Pídame una (pendientes, "
                          "contestaron…) o use los últimos 4 dígitos.")
        if not 1 <= n <= len(lista):
            return None, f"La última lista tiene {len(lista)}; no hay un {n}."
        return lista[n - 1], ""
    if len(ref) >= 10:
        candidatos = [h for h in hilos if _diez(h) == _diez(ref)]
    else:
        candidatos = [h for h in hilos if h.endswith(ref)]
    if len(candidatos) == 1:
        return candidatos[0], ""
    if not candidatos:
        return None, f"No encontré a ningún cliente con …{ref[-4:]}."
    _guardar_lista(p, "clientes", sorted(candidatos))
    return None, (f"Hay {len(candidatos)} clientes que terminan en {ref}: "
                  + ", ".join(f"{i}) …{h[-6:]}" for i, h in enumerate(sorted(candidatos), 1))
                  + ". Escriba el teléfono completo o su número.")


def _filas(espacio: Espacio, hilos: dict | None = None):
    from . import semaforo
    hilos = hilos if hilos is not None else _hilos(espacio)
    fuera = atendidos(espacio, hilos)
    return [f for f in semaforo.leer(hilos, de_ronda=semaforo.nuestros(espacio, hilos)) if f.hilo not in fuera]


def _renglon(espacio: Espacio, i: int, f, m: dict) -> str:
    from . import operacion, semaforo
    extra = " (lo lleva usted)" if "lo_llevo" in m.get(f.hilo, {}) else (
        " (no se le escribe)" if "no_escribir" in m.get(f.hilo, {}) else "")
    return (f"{i}) …{f.hilo[-4:]} {semaforo.ETIQUETA[f.estado].lower()}, {operacion._horas_txt(f.horas)}: "
            f"{_txt(f.dicho)}{extra}")


def _lista_clientes(p: Pedido, filas: list, titulo: str, vacia: str, pagina: int = 1) -> str:
    if not filas:
        return vacia
    pagina = max(1, pagina)
    desde = (pagina - 1) * POR_PAGINA
    tramo = filas[desde:desde + POR_PAGINA]
    if not tramo:
        return f"Solo hay {(len(filas) - 1) // POR_PAGINA + 1} páginas."
    _guardar_lista(p, "clientes", [f.hilo for f in tramo])
    m = marcas(p.espacio)
    lineas = [f"{titulo} ({len(filas)}):"] + [_renglon(p.espacio, i, f, m) for i, f in enumerate(tramo, 1)]
    if len(filas) > desde + POR_PAGINA:
        lineas.append(f"Hay más: escriba {p.orden['orden']} {pagina + 1}" if p.orden["orden"] == "pendientes"
                      else f"…y {len(filas) - desde - POR_PAGINA} más en la app.")
    lineas.append("Para ver uno: ficha 1 (o sus últimos 4 dígitos).")
    return "\n".join(lineas)


# --------------------------------------------------------------------------- #
#  El tablero                                                                  #
# --------------------------------------------------------------------------- #
def ayuda(p: Pedido) -> str:
    return ordenes.ayuda(p.orden.get("tema"))


def estado(p: Pedido) -> str:
    from . import mesa
    return mesa.reporte(p.espacio)


def _del_dia(ts: int, dia: date) -> bool:
    return datetime.fromtimestamp(ts, ZONA).date() == dia


def hoy(p: Pedido) -> str:
    from . import mesa
    hilos = _hilos(p.espacio)
    dia = _hoy()
    escribieron = {h for h, ms in hilos.items() if any(not m.del_negocio and _del_dia(m.ts, dia) for m in ms)}
    nuevos = {h for h in escribieron if _del_dia(min(m.ts for m in hilos[h]), dia)}
    contestamos = {h for h, ms in hilos.items() if any(m.del_negocio and _del_dia(m.ts, dia) for m in ms)}
    enviados = [e for e in mesa._hoy(p.espacio) if e.get("enviado")]
    no = [e for e in mesa._hoy(p.espacio) if not e.get("enviado")]
    sin = [h for h in escribieron if not hilos[h][-1].del_negocio]
    lineas = [f"Hoy {dia:%d/%m}:",
              f"· Escribieron {_plural(len(escribieron), 'cliente')} ({_plural(len(nuevos), 'nuevo')}).",
              f"· El negocio le escribió a {len(contestamos)}.",
              f"· Por la cola salieron {len(enviados)}" + (f"; no salieron {len(no)}." if no else ".")]
    if sin:
        lineas.append(f"· Esperan respuesta ahora: {len(sin)}. Escriba pendientes para verlos.")
    return "\n".join(lineas)


def semana(p: Pedido) -> str:
    hilos = _hilos(p.espacio)
    ahora = datetime.now(timezone.utc).timestamp()

    def cuenta(desde: float, hasta: float) -> dict:
        escribieron = {h for h, ms in hilos.items() if any(not m.del_negocio and desde <= m.ts < hasta for m in ms)}
        nuevos = {h for h in escribieron if desde <= min(m.ts for m in hilos[h]) < hasta}
        rentas = [r for r in _reservas_vivas(p.espacio)
                  if desde <= datetime.fromisoformat(r["en"]).timestamp() < hasta]
        return {"escribieron": len(escribieron), "nuevos": len(nuevos), "rentas": len(rentas)}

    a = cuenta(ahora - 7 * 86400, ahora + 1)
    b = cuenta(ahora - 14 * 86400, ahora - 7 * 86400)
    return ("Últimos 7 días (los 7 anteriores entre paréntesis):\n"
            f"· Clientes que escribieron: {a['escribieron']} ({b['escribieron']})\n"
            f"· Nuevos: {a['nuevos']} ({b['nuevos']})\n"
            f"· Rentas asentadas: {a['rentas']} ({b['rentas']})\n"
            "Con menos de 30 por semana, la diferencia no concluye.")


def oportunidades(p: Pedido) -> str:
    orden = {"contesto_ronda": 0, "promesa": 1, "nos_toca": 2, "cotizado": 3}
    filas = sorted((f for f in _filas(p.espacio) if f.estado in orden and f.color != "gris"),
                   key=lambda f: (orden[f.estado], f.horas))
    return _lista_clientes(p, filas, "Más cerca de rentar", "No veo oportunidades abiertas ahora.")


# --------------------------------------------------------------------------- #
#  Clientes                                                                    #
# --------------------------------------------------------------------------- #
def pendientes(p: Pedido) -> str:
    filas = [f for f in _filas(p.espacio) if f.color in ("rojo", "ambar")]
    return _lista_clientes(p, filas, "Pendientes, el más urgente primero", "No hay pendientes urgentes.",
                           p.orden.get("pagina", 1))


def _por_estado(*estados: str, titulo: str, vacia: str, colores=("rojo", "ambar", "verde")):
    def manejador(p: Pedido) -> str:
        filas = [f for f in _filas(p.espacio) if f.estado in estados and f.color in colores]
        return _lista_clientes(p, filas, titulo, vacia)
    return manejador


def _urgentes(p: Pedido) -> str:
    filas = [f for f in _filas(p.espacio) if f.color == "rojo"]
    return _lista_clientes(p, filas, "En rojo", "Nada en rojo.")


contestaron = _por_estado("contesto_ronda", titulo="Contestaron al seguimiento y esperan",
                          vacia="Nadie que haya contestado al seguimiento está esperando.")
promesas = _por_estado("promesa", titulo="Les quedamos de mandar algo", vacia="No hay promesas pendientes.",
                       colores=("rojo", "ambar", "verde", "gris"))
reclamos = _por_estado("reclamo", titulo="Reclamos", vacia="No hay reclamos sin contestar.",
                       colores=("rojo", "ambar", "verde", "gris"))
nuevos = _por_estado("sin_atender", titulo="Solo les contestó la máquina", vacia="No hay clientes sin atender.")
medios = _por_estado("solo_medios", titulo="Mandaron foto, audio o archivo (hay que verlo en el teléfono)",
                     vacia="No hay fotos ni audios sin ver.")
seguimiento = _por_estado("cotizado", "esperando_cliente", titulo="Para dar seguimiento",
                          vacia="No hay seguimientos pendientes.", colores=("ambar",))


def ficha(p: Pedido) -> str:
    from . import lectura, lista_precios, semaforo
    hilos = _hilos(p.espacio)
    hilo, error = resolver(p, p.orden.get("ref"), hilos)
    if not hilo:
        return error
    ms = hilos.get(hilo, [])
    fila = next((f for f in _filas(p.espacio, {hilo: ms})), None)
    lineas = [f"Cliente …{hilo[-4:]} ({_plural(len(ms), 'mensaje')})"]
    if fila:
        from .operacion import _horas_txt
        lineas.append(f"En qué va: {semaforo.ETIQUETA[fila.estado]} ({_horas_txt(fila.horas)}). {fila.que_hacer}")
    elif hilo in atendidos(p.espacio, {hilo: ms}):
        lineas.append("En qué va: usted lo marcó como contestado.")
    if (n := lectura.personas(ms)):
        lineas.append(f"Personas: {n}")
    if (fechas := lectura.fechas(ms)):
        lineas.append(f"Fechas: del {fechas[0]:%d/%m} al {fechas[1]:%d/%m/%Y}")
    if (prop := lista_precios.propiedad_en_platica(ms)):
        lineas.append(f"Propiedad de la que se habló: {prop}")
    ultimo = next((m for m in reversed(ms) if not m.del_negocio), None)
    if ultimo:
        lineas.append(f"Lo último que dijo ({datetime.fromtimestamp(ultimo.ts, ZONA):%d/%m %H:%M}): {_txt(ultimo.texto, 140)}")
    m = marcas(p.espacio).get(hilo, {})
    if "lo_llevo" in m:
        lineas.append(f"Lo lleva: {m['lo_llevo'].get('por') or 'usted'}")
    if "no_escribir" in m:
        lineas.append("No se le escribe (lo pidió usted).")
    for n_ in _notas_de(p.espacio, hilo)[-3:]:
        lineas.append(f"Nota ({_local(n_['en']):%d/%m}): {_txt(n_['texto'], 120)}")
    for r in [r for r in _reservas_vivas(p.espacio) if r["hilo"] == hilo]:
        lineas.append("Rentó" + (f": {_pesos(r['monto_centavos'])}" if r.get("monto_centavos") else "")
                      + f" ({_local(r['en']):%d/%m}).")
    lista = _lista_guardada(p, "clientes")
    if hilo in lista:  # ver una ficha no borra la lista de donde salió (revisión 2026-10-31)
        n = lista.index(hilo) + 1
    else:
        _guardar_lista(p, "clientes", [hilo])
        n = 1
    lineas.append(f"Historial: historial {n} · Nota: nota {n} <texto> · Dictarle: dile {n} que …")
    return "\n".join(lineas)


def historial_(p: Pedido) -> str:
    hilos = _hilos(p.espacio)
    hilo, error = resolver(p, p.orden.get("ref"), hilos)
    if not hilo:
        return error
    ms = [m for m in hilos.get(hilo, [])][-8:]
    if not ms:
        return "Esa plática está vacía."
    return f"Últimos mensajes de …{hilo[-4:]}:\n" + "\n".join(
        f"{datetime.fromtimestamp(m.ts, ZONA):%d/%m %H:%M} {'Negocio' if m.del_negocio else 'Cliente'}: {_txt(m.texto, 120)}"
        for m in ms)


def busca(p: Pedido) -> str:
    buscado = ordenes.normalizar(p.orden.get("texto", ""))
    if len(buscado) < 3:
        return "Escriba al menos 3 letras: busca boda"
    hilos = _hilos(p.espacio)
    hallados = []
    for hilo, ms in hilos.items():
        m = next((m for m in reversed(ms) if not m.del_negocio and buscado in ordenes.normalizar(m.texto or "")), None)
        if m:
            hallados.append((m.ts, hilo, m.texto))
    if not hallados:
        return f"Nadie ha escrito «{buscado}»."
    hallados.sort(reverse=True)
    _guardar_lista(p, "clientes", [h for _, h, _ in hallados[:POR_PAGINA]])
    return (f"Dicen «{buscado}» ({len(hallados)}):\n"
            + "\n".join(f"{i}) …{h[-4:]} {datetime.fromtimestamp(ts, ZONA):%d/%m}: {_txt(t)}"
                        for i, (ts, h, t) in enumerate(hallados[:POR_PAGINA], 1)))


def _notas_de(espacio: Espacio, hilo: str | None = None) -> list[dict]:
    vivas: dict[str, dict] = {}
    for r in espacio.leer_lineas(NOTAS):
        if r.get("borrada"):
            vivas.pop(r["id"], None)
        else:
            vivas[r["id"]] = r
    return [n for n in vivas.values() if hilo is None or n["hilo"] == hilo]


def notas(p: Pedido) -> str:
    if p.orden.get("ref"):
        hilo, error = resolver(p, p.orden["ref"])
        if not hilo:
            return error
        lista = _notas_de(p.espacio, hilo)
        if not lista:
            return f"…{hilo[-4:]} no tiene notas."
        return f"Notas de …{hilo[-4:]}:\n" + "\n".join(f"· {_local(n['en']):%d/%m} {n['por']}: {n['texto']}" for n in lista)
    lista = _notas_de(p.espacio)[-10:]
    if not lista:
        return "No hay notas todavía. Para dejar una: nota …1234 <texto>"
    return "Últimas notas:\n" + "\n".join(f"· …{n['hilo'][-4:]} {_local(n['en']):%d/%m}: {_txt(n['texto'])}" for n in lista)


def marcados(p: Pedido) -> str:
    m = marcas(p.espacio)
    no = sorted(h for h, x in m.items() if "no_escribir" in x)
    lleva = sorted(h for h, x in m.items() if "lo_llevo" in x)
    if not (no or lleva):
        return "No hay clientes marcados."
    lineas = []
    if no:
        lineas.append("No se les escribe: " + ", ".join(_mask(h) for h in no))
    if lleva:
        lineas.append("Los lleva usted: " + ", ".join(_mask(h) for h in lleva))
    return "\n".join(lineas)


def nota(p: Pedido) -> str:
    hilo, error = resolver(p, p.orden.get("ref"))
    if not hilo:
        return error
    texto = (p.orden.get("texto") or "").strip()
    if not texto:
        return "¿Qué anoto? nota …1234 <texto>"
    ident = _id()
    p.espacio.agregar_linea(NOTAS, {"id": ident, "hilo": hilo, "texto": texto[:500], "por": p.nombre or _mask(p.hilo),
                                    "en": _ahora()})
    _accion(p, {"tipo": "nota", "id": ident})
    return f"Anotado en la ficha de …{hilo[-4:]}."


def _marca_orden(tipo: str, valor: bool, hecho: str):
    def manejador(p: Pedido) -> str:
        hilo, error = resolver(p, p.orden.get("ref"))
        if not hilo:
            return error
        previo = marcas(p.espacio).get(hilo, {}).get(tipo)
        marcar(p.espacio, hilo, tipo, valor, p.nombre)
        _accion(p, {"tipo": "marca", "hilo": hilo, "marca": tipo, "antes": previo is not None, "previo": previo})
        return hecho.format(c=f"…{hilo[-4:]}")
    return manejador


no_escribir_ = _marca_orden("no_escribir", True, "Listo: a {c} no le llega ninguna ronda ni envío. "
                                                 "Para regresarlo: ya puedes escribirle {c}")
si_escribir = _marca_orden("no_escribir", False, "Listo: {c} vuelve a recibir seguimientos.")
lo_llevo = _marca_orden("lo_llevo", True, "Listo: {c} lo lleva usted. El equipo no le escribe; "
                                          "para soltarlo: suelta {c}")
suelta = _marca_orden("lo_llevo", False, "Listo: el equipo vuelve a darle seguimiento a {c}.")
atendido = _marca_orden("atendido", True, "Listo: {c} sale de pendientes hasta que vuelva a escribir.")


def _pesos(centavos: int) -> str:
    from .cotizador import pesos
    return pesos(centavos)


def _reservas_vivas(espacio: Espacio) -> list[dict]:
    vivas: dict[str, dict] = {}
    for r in espacio.leer_lineas(RESERVAS):
        if r.get("borrada"):
            vivas.pop(r["id"], None)
        else:
            vivas[r["id"]] = r
    return list(vivas.values())


def cerro(p: Pedido) -> str:
    hilo, error = resolver(p, p.orden.get("ref"))
    if not hilo:
        return error
    monto = ordenes.monto_centavos(p.orden.get("monto"))
    if p.orden.get("monto") and monto is None:
        return "No entendí el monto. Escríbalo así: cerró …1234 15000"
    ident = _id()
    p.espacio.agregar_linea(RESERVAS, {"id": ident, "hilo": hilo, "monto_centavos": monto, "por": p.nombre,
                                       "en": _ahora()})
    _accion(p, {"tipo": "reserva", "id": ident})
    return (f"Asentado: …{hilo[-4:]} rentó" + (f" por {_pesos(monto)}" if monto else "") + "."
            + ("" if monto else " Si quiere agregar el monto: deshaz y cerró …" + hilo[-4:] + " 15000"))


def reservas(p: Pedido) -> str:
    hoy_ = _hoy()
    del_mes = [r for r in _reservas_vivas(p.espacio)
               if datetime.fromisoformat(r["en"]).astimezone(ZONA).date().replace(day=1) == hoy_.replace(day=1)]
    if not del_mes:
        return "Este mes no hay rentas asentadas. Para asentar una: cerró …1234 15000"
    con = [r for r in del_mes if r.get("monto_centavos")]
    total = sum(r["monto_centavos"] for r in con)
    lineas = [f"Rentas asentadas en {ordenes._MES_N[hoy_.month]}: {len(del_mes)}"
              + (f", {_pesos(total)} en {_plural(len(con), 'renta')} con monto" if con else "") + "."]
    lineas += [f"· …{r['hilo'][-4:]} {_local(r['en']):%d/%m}"
               + (f": {_pesos(r['monto_centavos'])}" if r.get("monto_centavos") else "") for r in del_mes[-10:]]
    return "\n".join(lineas)


_OTRO_CLIENTE = re.compile(r"\b(?:a|al|a la|al de|para)\s+(?:…|\.\.\.)?\s*\d{4,}\b")


def dile(p: Pedido) -> str:
    """Lo que la dueña le dicta a un cliente. Primero se le enseña tal cual saldría; sale
    cuando contesta *sí, mándalo* (Gestor: *contesta 3* enseña, *contesta 3 ya* manda)."""
    hilo, error = resolver(p, p.orden.get("ref"))
    if not hilo:
        return error
    texto = (p.orden.get("texto") or "").strip()
    if len(re.findall(r"\w", texto)) < 2 or texto.endswith(("...", "…")):
        return "¿Qué le digo? dile …1234 que ya quedó apartado"
    if _OTRO_CLIENTE.search(texto):
        return "Ahí veo a otro cliente. Una orden por cliente: dile …1234 que … y luego dile …5678 que …"
    dictados = p.espacio.leer_json(DICTADOS, {}) or {}
    dictados[p.de] = {"hilo": hilo, "texto": texto, "en": _ahora()}
    p.espacio.escribir_json(DICTADOS, dictados)
    _accion(p, {"tipo": "dictado"})  # "deshaz" justo después lo cancela, no deshace la orden de antes
    return f"Le mando a …{hilo[-4:]}:\n«{texto}»\n¿Lo mando? Conteste: mándalo (o: no lo mandes)"


def olvidar_dictado(espacio: Espacio, de: str) -> None:
    """Cualquier otra orden deja sin efecto lo dictado: el "mándalo" vale para lo último que se le enseñó."""
    dictados = espacio.leer_json(DICTADOS, {}) or {}
    if de in dictados:
        dictados.pop(de)
        espacio.escribir_json(DICTADOS, dictados)


def hay_dictado(espacio: Espacio, de: str) -> bool:
    d = (espacio.leer_json(DICTADOS, {}) or {}).get(de)
    return bool(d) and datetime.now(timezone.utc) - datetime.fromisoformat(d["en"]) <= timedelta(minutes=MINUTOS_DICTADO)


def _tomar_dictado(p: Pedido) -> dict | None:
    dictados = p.espacio.leer_json(DICTADOS, {}) or {}
    d = dictados.pop(p.de, None)
    p.espacio.escribir_json(DICTADOS, dictados)
    if d and datetime.now(timezone.utc) - datetime.fromisoformat(d["en"]) <= timedelta(minutes=MINUTOS_DICTADO):
        return d
    return None


def cancela(p: Pedido) -> str:
    return "Listo, no lo mando." if _tomar_dictado(p) else ""


def confirma(p: Pedido) -> str:
    """Sale con SUS palabras y a su nombre, por los candados del canal (se revisa otra vez
    justo antes de mandar). Sin dictado reciente no contesta nada: "sí" es plática."""
    from . import agente, canal, historial
    d = _tomar_dictado(p)
    if not d:
        return ""
    hilo, texto = d["hilo"], d["texto"]
    c = p.espacio.config()
    if c.get("encendido") != "sin_cifra" or not canal.configurado(p.espacio):
        # No se aprueba para "más tarde": saldría días después, al encender, sin que nadie lo recuerde (tercera revisión).
        return ("No lo mandé: el envío está en pausa o el WhatsApp no está conectado. Cuando escriba "
                "enciende el envío, díctemelo otra vez.")
    ms = historial.hilos(p.espacio).get(hilo, [])
    salida = agente.Salida(cliente_id=p.espacio.cliente_id, hilo=hilo, responde_a=ms[-1].id if ms else "",
                           via="mesa", texto=texto, motivo=f"dictado por {p.nombre} en la mesa",
                           requiere_aprobacion=True)
    p.espacio.agregar_linea(agente.ARCHIVO, salida.a_dict())
    agente.aprobar_salida(p.espacio, salida.id, p.nombre)
    salida.aprobada_por = p.nombre
    _accion(p, None)
    if (motivo := canal.motivo_para_no_enviar(p.espacio, salida)):
        from .operacion import motivo_amable
        c = p.espacio.config()
        apagado = c.get("encendido") != "sin_cifra" or c.get("canal") != "vinculado"
        extra = " Sale en cuanto escriba: enciende el envío" if apagado and ("sombra" in motivo or "conector" in motivo) else ""
        return f"Quedó aprobado a su nombre, pero no sale por ahora: {motivo_amable(motivo)}.{extra}"
    canal.enviar(p.espacio, salida)
    return f"Va en la cola para …{hilo[-4:]}, con sus palabras: «{_txt(texto, 80)}»"


# --------------------------------------------------------------------------- #
#  Rondas y borradores                                                         #
# --------------------------------------------------------------------------- #
def _por_aprobar(espacio: Espacio) -> list:
    from . import agente
    fuera = descartadas(espacio)
    return [s for s in agente.salidas(espacio) if s.requiere_aprobacion and not s.aprobada_por and s.id not in fuera]


def borradores(p: Pedido) -> str:
    lista = _por_aprobar(p.espacio)
    if not lista:
        return "No hay nada esperando su sí."
    tramo = lista[:15]
    _guardar_lista(p, "borradores", [s.id for s in tramo])
    lineas = [f"Esperan su sí ({len(lista)}):"]
    for i, s in enumerate(tramo, 1):
        de = s.motivo.split(":")[0] if s.motivo.startswith("ronda ") else s.via
        lineas.append(f"{i}) …{s.hilo[-4:]} [{de}]: {_txt(s.texto, 90)}")
    if len(lista) > 15:
        lineas.append(f"…y {len(lista) - 15} más. «aprueba todos» manda solo estos 15; para toda la ronda: aprueba la ronda")
    lineas.append("Para mandar: aprueba 1 3 · para quitar: descarta 2 · todos: aprueba todos")
    return "\n".join(lineas)


def _elegidos(p: Pedido) -> tuple[list[str], str]:
    lista = _lista_guardada(p, "borradores")
    pedidos = p.orden.get("lista")
    if not lista:  # también "todos": nada se aprueba sin que ella haya visto la lista (revisión adversarial)
        return [], "Primero escriba borradores para ver la lista numerada."
    if pedidos == "todos":
        return lista, ""
    fuera = [n for n in pedidos if not 1 <= n <= len(lista)]
    if fuera:
        return [], f"La lista tiene {len(lista)}; no hay {', '.join(map(str, fuera))}."
    return [lista[n - 1] for n in dict.fromkeys(pedidos)], ""


def _aprobar_y_encolar(p: Pedido, ids: list[str]) -> tuple[int, int, dict]:
    """En lote: una lectura del disco para toda la ronda (antes, 14 s con 120 y el lector detenido)."""
    from . import agente, canal
    from .operacion import motivo_amable
    encoladas, no_salen = 0, {}
    fuera = descartadas(p.espacio)
    nuevas = agente.aprobar_salidas(p.espacio, [i for i in ids if i not in fuera], p.nombre)
    ctx = canal.contexto(p.espacio)
    for salida in nuevas:
        if (motivo := canal.motivo_para_no_enviar(p.espacio, salida, ctx)):
            no_salen[motivo_amable(motivo)] = no_salen.get(motivo_amable(motivo), 0) + 1
            continue
        canal.enviar(p.espacio, salida, ctx=ctx)
        encoladas += 1
    return len(nuevas), encoladas, no_salen


def _texto_aprobadas(p: Pedido, aprobadas_: int, encoladas: int, no_salen: dict, de: str = "") -> str:
    texto = f"Aprobé {_plural(aprobadas_, 'mensaje')}{de} a su nombre. En cola: {encoladas}."
    if no_salen:
        texto += " No salen por ahora: " + "; ".join(f"{k} ({v})" for k, v in no_salen.items()) + "."
        c = p.espacio.config()
        if c.get("encendido") != "sin_cifra" or c.get("canal") != "vinculado":
            texto += " Para mandarlos, escriba: enciende el envío"
    return texto


def aprueba_borradores(p: Pedido) -> str:
    from . import perfil
    ids, error = _elegidos(p)
    if error:
        return error
    try:
        a, e, no = _aprobar_y_encolar(p, ids)
    except perfil.AprobacionInvalida as err:
        return f"No se pudo aprobar: {err}"
    _accion(p, None)
    return _texto_aprobadas(p, a, e, no)


def descarta(p: Pedido) -> str:
    from . import agente
    ids, error = _elegidos(p)
    if error:
        return error
    ya = agente.aprobadas(p.espacio)
    ids = [i for i in ids if i not in descartadas(p.espacio) and i not in ya]
    if not ids:
        return "No había nada que descartar."
    for i in ids:
        p.espacio.agregar_linea(DESCARTES, {"id": i, "valor": True, "por": p.nombre, "en": _ahora()})
    _accion(p, {"tipo": "descartes", "ids": ids})
    return f"Descarté {_plural(len(ids), 'mensaje')}: no salen. Para regresarlos: deshaz"


def _ronda_pedida(espacio: Espacio, nombre: str | None) -> tuple[dict | None, str]:
    from .mesa import _rondas_cargadas
    cargadas = _rondas_cargadas(espacio)
    if nombre:
        ronda = next((r for r in cargadas if r["nombre"] == nombre), None)
        return ronda, "" if ronda else f"No encontré la ronda {nombre}."
    return (cargadas[-1], "") if cargadas else (None, "No hay rondas cargadas.")


def aprueba(p: Pedido) -> str:
    from . import mesa, perfil
    ronda, error = _ronda_pedida(p.espacio, p.orden.get("nombre"))
    if ronda is None:
        return error
    try:
        a, e, no = _aprobar_y_encolar(p, ronda.get("salidas", []))
    except perfil.AprobacionInvalida as err:
        return f"No se pudo aprobar: {err}"
    e += mesa.encolar_aprobadas(p.espacio)
    _accion(p, None)
    return _texto_aprobadas(p, a, e, no, de=f" de la ronda {ronda['nombre']}")


def descarta_ronda(p: Pedido) -> str:
    from . import agente
    ronda, error = _ronda_pedida(p.espacio, p.orden.get("nombre"))
    if ronda is None:
        return error
    ya = agente.aprobadas(p.espacio)
    fuera = descartadas(p.espacio)
    ids = [i for i in ronda.get("salidas", []) if i not in ya and i not in fuera]
    if not ids:
        return f"De la ronda {ronda['nombre']} no queda nada por descartar."
    for i in ids:
        p.espacio.agregar_linea(DESCARTES, {"id": i, "valor": True, "por": p.nombre, "en": _ahora()})
    _accion(p, {"tipo": "descartes", "ids": ids})
    return (f"Descarté {_plural(len(ids), 'mensaje')} de la ronda {ronda['nombre']}: no salen."
            + (" Lo que ya había aprobado sigue su camino; para detenerlo: pausa el envío." if any(i in ya for i in ronda.get("salidas", [])) else ""))


def _cuenta_ronda(espacio: Espacio, ronda: dict) -> dict:
    from . import agente, enviador
    ids = set(ronda.get("salidas", []))
    ya = agente.aprobadas(espacio)
    fuera = descartadas(espacio)
    hechos = [e for e in espacio.leer_lineas(enviador.ENVIADOS) if e.get("salida") in ids]
    return {"total": len(ids), "aprobadas": len(ids & set(ya)), "descartadas": len(ids & fuera),
            "enviadas": len({e["salida"] for e in hechos if e.get("enviado")}),
            "no_salieron": len({e["salida"] for e in hechos if not e.get("enviado")}),
            "fuera_al_cargar": len(ronda.get("descartadas", []))}


def rondas_(p: Pedido) -> str:
    from .mesa import _rondas_cargadas
    cargadas = _rondas_cargadas(p.espacio)
    if not cargadas:
        return "No hay rondas cargadas."
    lineas = ["Rondas (la última al final):"]
    for r in cargadas[-8:]:
        c = _cuenta_ronda(p.espacio, r)
        lineas.append(f"· {r['nombre']} ({r.get('cargada', '')[:10]}): {c['total']} mensajes, aprobados {c['aprobadas']}, "
                      f"enviados {c['enviadas']}, descartados {c['descartadas']}")
    return "\n".join(lineas)


def ronda(p: Pedido) -> str:
    from . import desenlace
    r, error = _ronda_pedida(p.espacio, p.orden.get("nombre"))
    if r is None:
        return error
    c = _cuenta_ronda(p.espacio, r)
    lineas = [f"Ronda {r['nombre']}, cargada {r.get('cargada', '')[:16].replace('T', ' ')}",
              f"Quién la pidió: {_txt(r.get('orden'), 120)}",
              f"Mensajes: {c['total']} · aprobados {c['aprobadas']} · enviados {c['enviadas']} · "
              f"no salieron {c['no_salieron']} · descartados {c['descartadas']} · fuera al cargar {c['fuera_al_cargar']}"]
    fila = next((f for f in desenlace.de_rondas(p.espacio) if f["ronda"] == r["nombre"]), None)
    if fila:
        lineas.append(desenlace.linea(fila) + ("" if fila["concluye"] else " (n < 30, no concluye)"))
    return "\n".join(lineas)


def desenlace_(p: Pedido) -> str:
    from . import desenlace
    filas = desenlace.de_rondas(p.espacio)
    if not filas:
        return "Todavía no sale ninguna ronda."
    return "\n".join(desenlace.linea(f) + ("" if f["concluye"] else " (n < 30, no concluye)") for f in filas[:5])


# --------------------------------------------------------------------------- #
#  El envío                                                                    #
# --------------------------------------------------------------------------- #
def cola(p: Pedido) -> str:
    from . import enviador, mesa, operacion
    _, titulo, texto = operacion.estado_canal(p.espacio)
    hoy_ = mesa._hoy(p.espacio)
    return (f"{titulo}. {texto}\nEsperan su sí: {len(_por_aprobar(p.espacio))} · en cola: "
            f"{len(enviador.pendientes(p.espacio))} · enviados hoy: {sum(1 for e in hoy_ if e.get('enviado'))}")


def enviados(p: Pedido) -> str:
    from . import agente, mesa
    hoy_ = [e for e in mesa._hoy(p.espacio) if e.get("enviado")]
    if not hoy_:
        return "Hoy no ha salido nada por la cola."
    salidas = {s.id: s for s in agente.salidas(p.espacio)}
    lineas = [f"Salieron hoy ({len(hoy_)}):"]
    for e in hoy_[-12:]:
        s = salidas.get(e.get("salida", ""))
        lineas.append(f"· {_local(e['cuando']):%H:%M} …{(e.get('hilo') or (s.hilo if s else '????'))[-4:]}"
                      + (f": {_txt(s.texto, 60)}" if s else ""))
    return "\n".join(lineas)


def fallidos(p: Pedido) -> str:
    from . import mesa
    from .operacion import motivo_amable
    no = [e for e in mesa._hoy(p.espacio) if not e.get("enviado")]
    if not no:
        return "Hoy no hubo envíos fallidos."
    por: dict[str, int] = {}
    for e in no:
        por[motivo_amable(e.get("motivo", ""))] = por.get(motivo_amable(e.get("motivo", "")), 0) + 1
    return f"No salieron hoy ({len(no)}):\n" + "\n".join(f"· {k}: {v}" for k, v in sorted(por.items(), key=lambda x: -x[1]))


def canal_(p: Pedido) -> str:
    from . import canal, operacion, vinculado
    c = p.espacio.config()
    estado_ = vinculado.leer_estado(p.espacio).get("estado") or "sin datos"
    _, titulo, texto = operacion.estado_canal(p.espacio)
    return (f"WhatsApp vinculado: {estado_}. Canal: {c.get('canal', 'oficial')}. "
            f"{'Listo para mandar' if canal.configurado(p.espacio) else 'No puede mandar todavía'}.\n{titulo}. {texto}")


def _cambiar_config(p: Pedido, cambios: dict, encolar: bool = False, deshacer: bool = True) -> None:
    config = p.espacio.config()
    antes = {k: config.get(k) for k in cambios}
    config.update(cambios)
    p.espacio.escribir_json("config.json", config)
    # "despues": si alguien lo cambia por otro lado, el deshaz no le pisa ese cambio.
    _accion(p, {"tipo": "config", "antes": antes, "despues": dict(cambios), "encolar": encolar} if deshacer else None)


def enciende(p: Pedido) -> str:
    from . import mesa
    config = p.espacio.config()
    antes = {"canal": config.get("canal", "oficial"), "encendido": config.get("encendido", "sombra")}
    _cambiar_config(p, {"canal": "vinculado", "encendido": "sin_cifra"})
    p.espacio.agregar_linea("cambios_canal.jsonl", {"antes": antes, "ahora": {"canal": "vinculado", "encendido": "sin_cifra"},
                                                    "por": p.nombre, "via": "mesa", "en": _ahora()})
    n = mesa.encolar_aprobadas(p.espacio)
    return ("Envío encendido. Sale lo que usted aprueba, uno cada 40 segundos, de 9 a 9."
            + (f" Ya van a la cola {n} que había aprobado." if n else ""))


def pausa(p: Pedido) -> str:
    config = p.espacio.config()
    antes = {"canal": config.get("canal", "oficial"), "encendido": config.get("encendido", "sombra")}
    _cambiar_config(p, {"encendido": "sombra"}, deshacer=False)  # una pausa se levanta con "enciende", no con "deshaz"
    p.espacio.agregar_linea("cambios_canal.jsonl", {"antes": antes, "ahora": {"canal": antes["canal"], "encendido": "sombra"},
                                                    "por": p.nombre, "via": "mesa", "en": _ahora()})
    return "Envío en pausa. No sale nada hasta que escriba: enciende el envío"


def ritmo(p: Pedido) -> str:
    from . import enviador
    r = enviador.Ritmo.de(p.espacio)
    return (f"Ritmo: uno cada {r.pausa_min} a {r.pausa_max} segundos, de {r.hora_desde}:00 a {r.hora_hasta}:59, "
            f"hasta {r.tope_dia} al día (el techo es {enviador.TOPE_DIA}). Para bajarlo: máximo 50 al día")


def tope(p: Pedido) -> str:
    from . import enviador
    n = p.orden.get("n", 0)
    config = p.espacio.config()
    envio = dict(config.get("envio") or {})
    envio["tope_dia"] = max(0, min(enviador.TOPE_DIA, n))
    _cambiar_config(p, {"envio": envio})
    return (f"Listo: hasta {envio['tope_dia']} al día." + (f" (El techo es {enviador.TOPE_DIA}.)" if n > enviador.TOPE_DIA else ""))


# --------------------------------------------------------------------------- #
#  Precios y perfil                                                            #
# --------------------------------------------------------------------------- #
def _propiedades(espacio: Espacio) -> list[str]:
    alta = espacio.leer_json("alta.json", {}) or {}
    return [str(x).lower() for x in alta.get("propiedades", []) or []]


def _prop_y_resto(p: Pedido) -> tuple[str | None, str]:
    """La propiedad que nombró (si es una del negocio) y el resto del texto; si la
    "propiedad" era una palabra cualquiera (*"para"*), vuelve al resto."""
    prop, resto = p.orden.get("prop"), p.orden.get("resto", "") or ""
    validas = set(_propiedades(p.espacio)) | {"ambas"}
    if prop and prop not in validas:
        resto, prop = f"{prop} {resto}", None
    if not prop:
        prop = next((x for x in sorted(validas) if f" {x} " in f" {ordenes.normalizar(resto)} "), None)
    return prop, resto


def cotiza(p: Pedido) -> str:
    from . import calendario, cotizador, perfil
    activo = perfil.activo(p.espacio)
    if not activo:
        return "No hay lista de precios aprobada todavía: no puedo dar un número."
    personas = p.orden.get("personas", 0)
    prop, resto = _prop_y_resto(p)
    fechas = ordenes.fechas_de(resto, _hoy())
    llegada, salida = fechas if fechas else (None, None)
    g = cotizador.cotizar_grupo(activo, personas, llegada, salida, propiedad=prop)
    if g.completa:
        texto = g.texto()
    elif prop and fechas and prop != "ambas":
        c = cotizador.cotizar(activo, prop, llegada, salida, personas)
        texto = c.texto()
    else:
        texto = g.texto()
    lineas = [f"Para {personas} personas" + (f", {cotizador._rango(llegada, salida)}" if fechas else "") + ":", texto]
    if fechas:
        oc = calendario.Ocupacion.de(p.espacio)
        props = [o.propiedad for o in g.completas] or ([prop] if prop else [])
        for x in props:
            d = oc.disponibilidad(x, llegada, salida)
            lineas.append(f"Calendario {x}: " + {"libre": "libre", "ocupada": "OCUPADA"}.get(d.estado, "sin saber")
                          + (f" ({d.por_que})" if d.estado != "libre" and d.por_que else ""))
    elif resto.strip() and any(ch.isdigit() for ch in resto):
        lineas.append("No entendí las fechas; escríbalas así: del 9 al 11 de noviembre")
    lineas.append("Es para usted: al cliente se le manda con su sí (dile …1234 que …).")
    return "\n".join(lineas)


_TIPO = {"noche": "la noche", "fin_de_semana": "el fin de semana", "grupo": "por grupo", "evento": "el evento",
         "anticipo": "anticipo", "deposito": "depósito", "extra": "extra", "persona_extra": "persona extra",
         "minimo": "mínimo", "servicio": "servicio"}


def _regla_txt(r: dict) -> str:
    partes = [str(r.get("propiedad") or r.get("servicio") or r.get("clave") or "").capitalize()]
    partes.append(_TIPO.get(r.get("tipo", ""), r.get("tipo", "")))
    if r.get("personas"):
        partes.append(f"hasta {r['personas']} personas")
    if r.get("habitaciones"):
        partes.append(f"{r['habitaciones']} hab.")
    for k in ("dias", "unidad", "temporada", "concepto"):
        if r.get(k):
            partes.append(str(r[k]).replace("_", " "))
    valor = (_pesos(r["monto_centavos"]) if r.get("monto_centavos") is not None else
             f"{r['pct']}%" if r.get("pct") is not None else f"{r['noches']} noches" if r.get("noches") else "")
    return " · ".join(x for x in partes if x) + (f": {valor}" if valor else "")


def precios(p: Pedido) -> str:
    from . import perfil
    activo = perfil.activo(p.espacio)
    if not activo:
        return "No hay lista de precios aprobada todavía."
    prop, _ = _prop_y_resto(p)
    prop = None if prop == "ambas" else prop  # "precios las dos": la lista entera
    reglas = [r for r in activo.get("reglas", []) or [] if not prop or r.get("propiedad") in (prop, None)]
    if not reglas:
        return f"La lista no tiene precios de {prop}." if prop else "La lista no tiene precios."
    v = perfil.version_activa(p.espacio)
    lineas = [f"Lista activa (versión {v}){' de ' + prop if prop else ''}, {_plural(len(reglas), 'renglón', 'renglones')}:"]
    lineas += [f"· {_regla_txt(r)}" for r in reglas[:25]]
    if len(reglas) > 25:
        lineas.append(f"…y {len(reglas) - 25} más en Asistente → Precios.")
    return "\n".join(lineas)


def perfil_(p: Pedido) -> str:
    from . import perfil
    v = perfil.version_activa(p.espacio)
    todas = perfil.versiones(p.espacio)
    if v is None:
        return f"No hay versión activa. Versiones guardadas: {len(todas)}." + (" Escriba propuestas." if todas else "")
    d = perfil.leer_version(p.espacio, v) or {}
    pf = d.get("perfil", {}) or {}
    return (f"Activa: versión {v} «{d.get('nombre', '')}» ({d.get('creada', '')[:10]}), de {d.get('autor', '')}. "
            f"{len(pf.get('reglas', []) or [])} precios, {len(pf.get('faq', []) or [])} respuestas guardadas, "
            f"{len(pf.get('voz', []) or [])} frases de voz. Versiones guardadas: {len(todas)}.")


def propuestas(p: Pedido) -> str:
    from . import perfil
    v = perfil.version_activa(p.espacio) or 0
    nuevas = [n for n in perfil.versiones(p.espacio) if n > v]
    vivas: dict[str, dict] = {}
    for r in p.espacio.leer_lineas(RECUERDA):
        (vivas.pop(r["id"], None) if r.get("retirada") else vivas.__setitem__(r["id"], r))
    pendientes_ = len(vivas)
    if not nuevas:
        return "No hay versiones esperando su sí." + (f" Hay {pendientes_} reglas suyas anotadas para la próxima." if pendientes_ else "")
    lineas = ["Esperan su sí:"]
    for n in nuevas:
        d = perfil.leer_version(p.espacio, n) or {}
        lineas.append(f"· versión {n} «{d.get('nombre', '')}» de {d.get('autor', '')}, "
                      f"{len((d.get('perfil') or {}).get('reglas', []) or [])} precios")
    lineas.append(f"Para activarla: aprueba la versión {nuevas[-1]}")
    return "\n".join(lineas)


def aprueba_perfil(p: Pedido) -> str:
    from . import perfil
    v = perfil.version_activa(p.espacio)
    n = p.orden.get("n")
    if n is None:
        nuevas = [x for x in perfil.versiones(p.espacio) if x > (v or 0)]
        if len(nuevas) != 1:
            return "¿Cuál versión? " + (f"Hay {len(nuevas)}: " + ", ".join(map(str, nuevas)) if nuevas else "No hay propuestas.")
        n = nuevas[0]
    if n == v:
        return f"La versión {n} ya es la activa."
    try:
        perfil.aprobar(p.espacio, n, aprobador=p.nombre)
    except (perfil.AprobacionInvalida, ValueError) as err:
        return f"No se pudo: {err}"
    _accion(p, {"tipo": "perfil", "antes": v, "puso": n})
    return f"Versión {n} activa. El agente cotiza con esa lista desde ahora. Para regresar: deshaz"


def faq(p: Pedido) -> str:
    from . import perfil
    lista = (perfil.activo(p.espacio) or {}).get("faq", []) or []
    if not lista:
        return "No hay respuestas guardadas en la versión activa."
    return f"Respuestas guardadas ({len(lista)}):\n" + "\n".join(
        f"· {_txt(f.get('pregunta'), 70)} → {_txt(f.get('respuesta'), 70)}" for f in lista[:12])


def recuerda(p: Pedido) -> str:
    texto = (p.orden.get("texto") or "").strip()
    if len(texto) < 4:
        return "¿Qué quiere que recuerde? recuerda: la alberca se calienta con 24 h de aviso"
    ident = _id()
    p.espacio.agregar_linea(RECUERDA, {"id": ident, "texto": texto[:500], "por": p.nombre or _mask(p.hilo), "en": _ahora()})
    _accion(p, {"tipo": "recuerda", "id": ident})
    return ("Anotado para la próxima versión del perfil. No cambia lo que el agente contesta hasta que usted "
            "apruebe esa versión.")


def gasto_(p: Pedido) -> str:
    from . import gasto
    return (f"Inteligencia artificial este mes: USD {gasto.gastado_usd(p.espacio):.2f} de un tope de "
            f"USD {gasto.tope_usd(p.espacio):.2f}. Al llegar al tope, todo pasa a una persona.")


# --------------------------------------------------------------------------- #
#  Calendario                                                                  #
# --------------------------------------------------------------------------- #
def _props_calendario(espacio: Espacio, oc) -> list[str]:
    return sorted(set(_propiedades(espacio)) | set(oc.por_propiedad) | set(oc.bloques))


def disponible(p: Pedido) -> str:
    from . import calendario, cotizador
    prop, resto = _prop_y_resto(p)
    fechas = ordenes.fechas_de(resto, _hoy())
    if not fechas:
        return "No entendí las fechas. Escríbalas así: libre del 9 al 11 de noviembre"
    oc = calendario.Ocupacion.de(p.espacio)
    props = [prop] if prop else _props_calendario(p.espacio, oc)
    lineas = [f"{cotizador._rango(*fechas).capitalize()}:"]
    for x in props:
        d = oc.disponibilidad(x, *fechas)
        lineas.append(f"· {x}: " + {"libre": "libre", "ocupada": "OCUPADA"}.get(d.estado, "sin saber")
                      + (f" ({d.por_que})" if d.estado != "libre" and d.por_que else ""))
    return "\n".join(lineas)


def calendario_(p: Pedido) -> str:
    from . import calendario
    dias = min(60, p.orden.get("dias", 30))
    oc = calendario.Ocupacion.de(p.espacio)
    props = _props_calendario(p.espacio, oc)
    if not props:
        return "No hay calendario conectado ni noches apartadas."
    desde = _hoy()
    lineas = [f"Próximos {dias} días:"]
    for x in props:
        ocupadas = [desde + timedelta(days=i) for i in range(dias)
                    if oc.disponibilidad(x, desde + timedelta(days=i), desde + timedelta(days=i + 1)).estado == "ocupada"]
        conectado = x in oc.por_propiedad
        lineas.append(f"· {x}: {_plural(len(ocupadas), 'noche ocupada', 'noches ocupadas')}"
                      + (": " + ", ".join(f"{d:%d/%m}" for d in ocupadas[:12]) + ("…" if len(ocupadas) > 12 else "") if ocupadas else "")
                      + ("" if conectado else " (sin calendario conectado: solo lo apartado a mano)"))
    return "\n".join(lineas)


def huecos(p: Pedido) -> str:
    from . import calendario
    oc = calendario.Ocupacion.de(p.espacio)
    props = _props_calendario(p.espacio, oc)
    if not props:
        return "No hay calendario conectado: no puedo decir qué está libre."
    hoy_ = _hoy()
    viernes = hoy_ + timedelta(days=(4 - hoy_.weekday()) % 7)
    lineas = [f"Fines de semana (viernes a domingo), próximas {SEMANAS_HUECOS} semanas:"]
    noches_ = []
    if hoy_.weekday() == 5:  # sábado: el fin de este fin de semana todavía se vende (la noche de hoy)
        noches_.append((hoy_, hoy_ + timedelta(days=1)))
    noches_ += [(viernes + timedelta(weeks=i), viernes + timedelta(weeks=i, days=2))
                for i in range(SEMANAS_HUECOS - len(noches_))]
    for v, hasta in noches_:
        estados = []
        for x in props:
            d = oc.disponibilidad(x, v, hasta)
            estados.append(f"{x} {'libre' if d.estado == 'libre' else 'ocupada' if d.estado == 'ocupada' else '¿?'}")
        lineas.append(f"· {v:%d/%m}: " + ", ".join(estados))
    if not oc.configurada:
        lineas.append("¿? = sin calendario conectado; solo sé lo que usted apartó.")
    return "\n".join(lineas)


def aparta(p: Pedido) -> str:
    prop, resto = _prop_y_resto(p)
    if not prop:
        return "¿Cuál propiedad? aparta finca del 9 al 11 de noviembre"
    fechas = ordenes.fechas_de(resto, _hoy())
    if not fechas:
        return "No entendí las fechas. Escríbalas así: aparta finca del 9 al 11 de noviembre"
    props = sorted(set(_propiedades(p.espacio))) if prop == "ambas" else [prop]
    ids = []
    for x in props:
        ident = _id()
        p.espacio.agregar_linea(MANUAL, {"id": ident, "propiedad": x, "desde": fechas[0].isoformat(),
                                         "hasta": fechas[1].isoformat(), "por": p.nombre, "activo": True, "en": _ahora()})
        ids.append(ident)
    _accion(p, {"tipo": "manual", "ids": ids, "activo": False})
    from .cotizador import _rango
    return (f"Apartado: {', '.join(props)} {_rango(*fechas)}. Ninguna ronda ni cotización ofrece esas noches. "
            "Para quitarlo: libera " + prop + " …")


def libera(p: Pedido) -> str:
    prop, resto = _prop_y_resto(p)
    fechas = ordenes.fechas_de(resto, _hoy())
    if not prop or not fechas:
        return "Escríbalo así: libera finca del 9 al 11 de noviembre"
    props = set(_propiedades(p.espacio)) if prop == "ambas" else {prop}
    quitar = [r for r in apartados_a_mano(p.espacio) if r["propiedad"] in props
              and date.fromisoformat(r["desde"]) < fechas[1] and fechas[0] < date.fromisoformat(r["hasta"])]
    if not quitar:
        return ("No hay nada apartado a mano en esas fechas. Lo que viene de Airbnb, Booking o Google "
                "se libera allá.")
    pedazos = []
    for r in quitar:
        p.espacio.agregar_linea(MANUAL, {"id": r["id"], "activo": False, "en": _ahora()})
        # Liberar del 9 al 11 dentro de un apartado del 1 al 15 deja apartado lo de los lados.
        desde, hasta = date.fromisoformat(r["desde"]), date.fromisoformat(r["hasta"])
        for a, b in ((desde, min(hasta, fechas[0])), (max(desde, fechas[1]), hasta)):
            if a < b:
                ident = _id()
                p.espacio.agregar_linea(MANUAL, {"id": ident, "propiedad": r["propiedad"], "desde": a.isoformat(),
                                                 "hasta": b.isoformat(), "por": r.get("por", ""), "activo": True,
                                                 "en": _ahora()})
                pedazos.append(ident)
    _accion(p, {"tipo": "manual_reactivar", "registros": quitar, "pedazos": pedazos})
    from .cotizador import _rango
    return (f"Liberé {_rango(*fechas)} de lo apartado a mano" + (" (lo de los lados sigue apartado)" if pedazos else "")
            + ". Lo de las plataformas sigue como esté allá.")


# --------------------------------------------------------------------------- #
#  La mesa                                                                     #
# --------------------------------------------------------------------------- #
def bitacora(p: Pedido) -> str:
    from . import mesa
    lineas = p.espacio.leer_lineas(mesa.BITACORA)[-10:]
    if not lineas:
        return "Todavía no hay órdenes."
    return "Últimas órdenes:\n" + "\n".join(
        f"· {_local(r['en']):%d/%m %H:%M} {r.get('de', '')}: {r.get('orden', '')}" if r.get("en")
        else f"· {r.get('de', '')}: {r.get('orden', '')}" for r in lineas)


def administradoras(p: Pedido) -> str:
    from . import mesa
    alta = p.espacio.leer_json("alta.json", {}) or {}
    quien = mesa._diez(alta.get("aprobador_telefono"))
    silenciadas = set(p.espacio.config().get("reportes_silenciados", []) or [])
    return "Administradoras:\n" + "\n".join(
        f"· …{d[-4:]}" + (f" ({alta.get('aprobador')}, aprueba)" if d == quien else "")
        + (" — sin reportes" if d in silenciadas else "") for d in sorted(mesa.administradores(p.espacio)))


def _admins_config(p: Pedido, tel: str, agregar: bool) -> str:
    from . import mesa
    diez = mesa._diez(tel)
    if not diez:
        return "Ese teléfono no tiene 10 dígitos."
    alta = p.espacio.leer_json("alta.json", {}) or {}
    if not agregar and diez == mesa._diez(alta.get("aprobador_telefono")):
        return "A quien aprueba no se le quita desde aquí: está en el alta."
    actuales = list(p.espacio.config().get("administradores", []) or [])
    nuevos = ([*actuales, diez] if agregar and diez not in {mesa._diez(x) for x in actuales}
              else [x for x in actuales if mesa._diez(x) != diez])
    if nuevos == actuales:
        return f"…{diez[-4:]} ya {'era' if agregar else 'no era'} administradora."
    _cambiar_config(p, {"administradores": nuevos})
    return (f"Listo: …{diez[-4:]} {'ya puede escribirle a la mesa y recibe los reportes' if agregar else 'ya no es administradora'}.")


def agrega_admin(p: Pedido) -> str:
    return _admins_config(p, p.orden.get("tel", ""), True)


def quita_admin(p: Pedido) -> str:
    return _admins_config(p, p.orden.get("tel", ""), False)


def _reportes(p: Pedido, silenciar: bool) -> str:
    from .mesa import _diez
    yo = _diez(p.hilo)
    actuales = list(p.espacio.config().get("reportes_silenciados", []) or [])
    nuevos = sorted(set(actuales) | {yo}) if silenciar else [x for x in actuales if x != yo]
    if nuevos != actuales:
        config = p.espacio.config()
        config["reportes_silenciados"] = nuevos
        p.espacio.escribir_json("config.json", config)
        # Se deshace solo SU renglón: el de las demás administradoras no se toca.
        _accion(p, {"tipo": "reportes", "admin": yo, "antes": yo in actuales})
    return ("Listo: ya no le mando los reportes de las 9 y las 19. Para volver: activa los reportes" if silenciar
            else "Listo: le vuelvo a mandar los reportes de las 9 y las 19.")


def silencia(p: Pedido) -> str:
    return _reportes(p, True)


def activa_reportes(p: Pedido) -> str:
    return _reportes(p, False)


MANEJADORES = {
    "ayuda": ayuda, "estado": estado, "hoy": hoy, "semana": semana, "oportunidades": oportunidades,
    "pendientes": pendientes, "urgentes": _urgentes, "contestaron": contestaron, "promesas": promesas,
    "reclamos": reclamos, "nuevos": nuevos, "medios": medios, "seguimiento": seguimiento, "ficha": ficha,
    "historial": historial_, "busca": busca, "notas": notas, "marcados": marcados, "nota": nota,
    "no_escribir": no_escribir_, "si_escribir": si_escribir, "lo_llevo": lo_llevo, "suelta": suelta,
    "atendido": atendido, "cerro": cerro, "dile": dile, "confirma": confirma, "cancela": cancela, "aprueba_borradores": aprueba_borradores,
    "descarta": descarta, "aprueba": aprueba, "descarta_ronda": descarta_ronda, "borradores": borradores,
    "rondas": rondas_, "ronda": ronda, "desenlace": desenlace_, "cola": cola, "enviados": enviados,
    "fallidos": fallidos, "canal": canal_, "enciende": enciende, "pausa": pausa, "ritmo": ritmo, "tope": tope,
    "cotiza": cotiza, "precios": precios, "perfil": perfil_, "propuestas": propuestas,
    "aprueba_perfil": aprueba_perfil, "faq": faq, "recuerda": recuerda, "gasto": gasto_,
    "disponible": disponible, "calendario": calendario_, "huecos": huecos, "aparta": aparta, "libera": libera,
    "reservas": reservas, "bitacora": bitacora, "administradoras": administradoras, "agrega_admin": agrega_admin,
    "quita_admin": quita_admin, "silencia": silencia, "activa_reportes": activa_reportes, "deshaz": deshaz,
}
