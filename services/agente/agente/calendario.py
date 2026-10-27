"""El calendario de ocupación: qué noches de cada propiedad ya están tomadas.

Se lee por **iCal** (`.ics`), lo único que Airbnb, Booking.com y Google Calendar
exportan sin ser socio de la plataforma ni pagar un channel manager:

- Airbnb: Anuncio → Disponibilidad → "Exportar calendario". Eventos `Reserved`
  (reserva) o `Airbnb (Not available)` (bloqueo a mano).
- Booking.com: Extranet → Tarifas y disponibilidad → "Sincronizar calendarios" →
  exportar. Eventos `CLOSED - Not available`.
- Google Calendar: Configuración del calendario → "Dirección secreta en formato
  iCal". Cualquier evento de día completo, o que cruce la noche, la ocupa.

Las fuentes viven en el espacio (`calendario.json`, fuera de git: una URL de
exportación abre el calendario a quien la tenga):

    {"fuentes": [{"propiedad": "finca", "plataforma": "airbnb", "url": "https://..."}]}

Dos reglas (invariantes LXI y LXII de `MEMORY/CONSTITUCION.md`):

- Una noche es **libre** solo si *todas* las fuentes de esa propiedad
  respondieron con un calendario de verdad hace menos de `VIGENCIA_HORAS`. Sin
  fuente, con error, con un HTTP 200 que no es `VCALENDAR` o vieja: **no se
  sabe**, nunca libre. Airbnb y Booking tardan de 30 min a horas en publicar un
  cambio: "libre" sigue siendo un dato a confirmar por una persona.
- Una propiedad ocupada en esas fechas no sale en la cotización.

**No medido** contra los calendarios reales de Finca Emiliano: los formatos de
los tests son los que publican las plataformas, no una descarga suya. Lo
primero con las URLs es `python -m agente.calendario bajar <id>` y revisar.

    python -m agente.calendario fuente <id> <propiedad> <plataforma> <url>
    python -m agente.calendario bajar <id>
    python -m agente.calendario ver <id> [--desde AAAA-MM-DD] [--dias 30]
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .espacio import Espacio

ARCHIVO = "calendario.json"
CARPETA = "calendario"
VIGENCIA_HORAS = 12
ZONA = ZoneInfo("America/Mexico_City")
LIBRE, OCUPADA, NO_SE_SABE = "libre", "ocupada", "no_se_sabe"
_PLATAFORMA = re.compile(r"^[a-z0-9_-]{2,20}$")


# --------------------------------------------------------------------------- #
#  Lectura del .ics (RFC 5545, lo que usan las tres plataformas), sin paquetes #
# --------------------------------------------------------------------------- #
@dataclass
class Bloque:
    """Noches tomadas: de `desde` (primera noche) a `hasta` (día de salida, sin contar)."""
    desde: date
    hasta: date
    tipo: str          # reserva | bloqueo | evento
    titulo: str = ""
    uid: str = ""

    def noches(self) -> list[date]:
        return [self.desde + timedelta(days=i) for i in range((self.hasta - self.desde).days)]

    def a_dict(self) -> dict:
        return {"desde": self.desde.isoformat(), "hasta": self.hasta.isoformat(), "tipo": self.tipo,
                "titulo": self.titulo}


class NoEsCalendario(ValueError):
    """Lo que llegó no es un iCal (página de error o de inicio de sesión con HTTP 200)."""


def _lineas(texto: str) -> list[str]:
    """Desdobla las líneas plegadas (una línea que empieza con espacio continúa la anterior)."""
    salida: list[str] = []
    for linea in texto.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if linea[:1] in (" ", "\t") and salida:
            salida[-1] += linea[1:]
        elif linea:
            salida.append(linea)
    return salida


def _fecha(nombre_y_params: str, valor: str) -> tuple[date, bool]:
    """(día local, es de día completo). `20261225`, `20261225T150000Z` o con `TZID=`."""
    valor = valor.strip()
    if "T" not in valor:
        return datetime.strptime(valor[:8], "%Y%m%d").date(), True
    momento = datetime.strptime(valor.rstrip("Z")[:15], "%Y%m%dT%H%M%S")
    if valor.endswith("Z"):
        momento = momento.replace(tzinfo=timezone.utc)
    else:
        tz = re.search(r"TZID=([^;:]+)", nombre_y_params)
        try:
            momento = momento.replace(tzinfo=ZoneInfo(tz.group(1)) if tz else ZONA)
        except Exception:  # TZID que no es de la base IANA: hora local de México
            momento = momento.replace(tzinfo=ZONA)
    return momento.astimezone(ZONA).date(), False


def _tipo(titulo: str) -> str:
    t = titulo.lower()
    if "reserved" in t or "reservad" in t or "reserva" in t:
        return "reserva"
    if "not available" in t or "closed" in t or "no disponible" in t or "bloque" in t:
        return "bloqueo"
    return "evento"


def leer_ics(texto: str) -> list[Bloque]:
    """Los bloques de noches de un .ics. Lo cancelado no ocupa. Un evento con hora
    que empieza y acaba el mismo día (una visita, una junta) no ocupa la noche."""
    if "BEGIN:VCALENDAR" not in texto[:2000].upper():
        raise NoEsCalendario("no trae BEGIN:VCALENDAR")
    bloques: list[Bloque] = []
    actual: dict | None = None
    for linea in _lineas(texto):
        nombre, _, valor = linea.partition(":")
        clave = nombre.split(";")[0].upper()
        if clave == "BEGIN" and valor.upper() == "VEVENT":
            actual = {}
        elif clave == "END" and valor.upper() == "VEVENT" and actual is not None:
            if (b := _bloque(actual)) is not None:
                bloques.append(b)
            actual = None
        elif actual is not None and clave in ("DTSTART", "DTEND", "SUMMARY", "UID", "STATUS"):
            actual[clave] = (nombre, valor)
    return sorted(bloques, key=lambda b: (b.desde, b.hasta))


def _bloque(ev: dict) -> Bloque | None:
    if "DTSTART" not in ev or ev.get("STATUS", ("", ""))[1].strip().upper() == "CANCELLED":
        return None
    desde, de_dia = _fecha(*ev["DTSTART"])
    if "DTEND" in ev:
        hasta, _ = _fecha(*ev["DTEND"])
    else:
        hasta = desde + timedelta(days=1) if de_dia else desde
    if hasta <= desde:
        return None
    titulo = ev.get("SUMMARY", ("", ""))[1].replace("\\,", ",").replace("\\n", " ").strip()
    return Bloque(desde, hasta, _tipo(titulo), titulo, ev.get("UID", ("", ""))[1].strip())


# --------------------------------------------------------------------------- #
#  Fuentes por espacio y su descarga                                          #
# --------------------------------------------------------------------------- #
def fuentes(espacio: Espacio) -> list[dict]:
    return list((espacio.leer_json(ARCHIVO, {}) or {}).get("fuentes", []))


def agregar_fuente(espacio: Espacio, propiedad: str, plataforma: str, url: str) -> None:
    if not url.startswith("https://"):
        raise ValueError("la URL del calendario va con https://")
    if not _PLATAFORMA.match(plataforma) or not _PLATAFORMA.match(propiedad):
        raise ValueError("propiedad y plataforma: minúsculas, sin espacios")
    conf = espacio.leer_json(ARCHIVO, {}) or {}
    lista = [f for f in conf.get("fuentes", []) if (f["propiedad"], f["plataforma"]) != (propiedad, plataforma)]
    lista.append({"propiedad": propiedad, "plataforma": plataforma, "url": url})
    conf["fuentes"] = lista
    espacio.escribir_json(ARCHIVO, conf)


def _nombre(fuente: dict) -> str:
    return f"{fuente['propiedad']}-{fuente['plataforma']}"


def _descargar(url: str, timeout: float = 30) -> str:
    pedido = urllib.request.Request(url, headers={"User-Agent": "dged-agente/calendario"})
    with urllib.request.urlopen(pedido, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def bajar(espacio: Espacio, descargar=_descargar, ahora: datetime | None = None) -> list[dict]:
    """Descarga cada fuente y guarda lo que trajo con su estado. Una fuente que
    falla deja su estado en error: la copia anterior **no** se usa como si fuera
    nueva (su `leido` no cambia y envejece sola)."""
    ahora = ahora or datetime.now(timezone.utc)
    estados = espacio.leer_json(f"{CARPETA}/estado.json", {}) or {}
    for fuente in fuentes(espacio):
        nombre = _nombre(fuente)
        previo = estados.get(nombre, {})
        try:
            texto = descargar(fuente["url"])
            bloques = leer_ics(texto)
        except (OSError, urllib.error.URLError, NoEsCalendario, ValueError) as error:
            estados[nombre] = {**previo, "ok": False, "intento": ahora.isoformat(timespec="seconds"),
                               "error": f"{type(error).__name__}: {str(error)[:200]}"}
            continue
        espacio.escribir_json(f"{CARPETA}/{nombre}.json", [b.a_dict() for b in bloques])
        estados[nombre] = {"ok": True, "leido": ahora.isoformat(timespec="seconds"),
                           "intento": ahora.isoformat(timespec="seconds"), "bloques": len(bloques)}
    espacio.escribir_json(f"{CARPETA}/estado.json", estados)
    return [{"fuente": n, **e} for n, e in sorted(estados.items())]


# --------------------------------------------------------------------------- #
#  Ocupación y disponibilidad                                                 #
# --------------------------------------------------------------------------- #
@dataclass
class Disponibilidad:
    propiedad: str
    estado: str                      # libre | ocupada | no_se_sabe
    por_que: str = ""
    choques: list[dict] = field(default_factory=list)

    def a_dict(self) -> dict:
        return {"propiedad": self.propiedad, "estado": self.estado, "por_que": self.por_que,
                "choques": self.choques}


@dataclass
class Ocupacion:
    """Lo que se sabe del calendario de un espacio en un momento: por propiedad, sus
    fuentes y los bloques de las que están vigentes."""
    por_propiedad: dict[str, list[dict]]          # propiedad → [{fuente, ok, vigente, por_que}]
    bloques: dict[str, list[tuple[str, Bloque]]]  # propiedad → [(fuente, bloque)]

    @classmethod
    def de(cls, espacio: Espacio, ahora: datetime | None = None) -> Ocupacion:
        ahora = ahora or datetime.now(timezone.utc)
        estados = espacio.leer_json(f"{CARPETA}/estado.json", {}) or {}
        por_propiedad: dict[str, list[dict]] = {}
        bloques: dict[str, list[tuple[str, Bloque]]] = {}
        for fuente in fuentes(espacio):
            nombre, prop = _nombre(fuente), fuente["propiedad"]
            e = estados.get(nombre, {})
            por_que = ""
            if not e:
                por_que = f"{fuente['plataforma']} no se ha descargado"
            elif not e.get("ok"):
                por_que = f"{fuente['plataforma']} falló: {e.get('error', '')}"
            elif ahora - datetime.fromisoformat(e["leido"]) > timedelta(hours=VIGENCIA_HORAS):
                por_que = f"{fuente['plataforma']} se leyó hace más de {VIGENCIA_HORAS} h"
            por_propiedad.setdefault(prop, []).append({"fuente": nombre, "vigente": not por_que, "por_que": por_que})
            # Lo que una fuente vieja o caída decía sigue contando como ocupado (una
            # reserva no se borra porque el feed falle); lo que no sabe es lo libre.
            for d in espacio.leer_json(f"{CARPETA}/{nombre}.json", []) or []:
                b = Bloque(date.fromisoformat(d["desde"]), date.fromisoformat(d["hasta"]), d["tipo"], d.get("titulo", ""))
                bloques.setdefault(prop, []).append((fuente["plataforma"], b))
        return cls(por_propiedad, bloques)

    @property
    def configurada(self) -> bool:
        return bool(self.por_propiedad)

    def disponibilidad(self, propiedad: str, llegada: date, salida: date) -> Disponibilidad:
        """Si las noches de `llegada` a `salida` (sin contarla) están libres en esa propiedad."""
        if propiedad == "ambas":
            partes = [self.disponibilidad(p, llegada, salida) for p in sorted(self.por_propiedad)]
            if not partes:
                return Disponibilidad(propiedad, NO_SE_SABE, "sin calendario")
            choques = [c for p in partes for c in p.choques]
            if choques:
                return Disponibilidad(propiedad, OCUPADA, "una de las casas está ocupada", choques)
            dudas = [p.por_que for p in partes if p.estado == NO_SE_SABE]
            return Disponibilidad(propiedad, NO_SE_SABE, "; ".join(dudas)) if dudas \
                else Disponibilidad(propiedad, LIBRE)
        choques = [{"fuente": f, **b.a_dict()} for f, b in self.bloques.get(propiedad, [])
                   if b.desde < salida and llegada < b.hasta]
        if choques:
            return Disponibilidad(propiedad, OCUPADA, "ya hay noches tomadas en esas fechas", choques)
        estado = self.por_propiedad.get(propiedad)
        if not estado:
            return Disponibilidad(propiedad, NO_SE_SABE, f"{propiedad} no tiene calendario conectado")
        dudas = [e["por_que"] for e in estado if not e["vigente"]]
        if dudas:
            return Disponibilidad(propiedad, NO_SE_SABE, "; ".join(dudas))
        return Disponibilidad(propiedad, LIBRE)

    def noches(self, desde: date, dias: int) -> dict[str, list[dict]]:
        """Por propiedad, cada noche del rango: libre, ocupada (con de dónde) o no se sabe."""
        salida: dict[str, list[dict]] = {}
        for prop in sorted(self.por_propiedad):
            filas = []
            for i in range(dias):
                noche = desde + timedelta(days=i)
                d = self.disponibilidad(prop, noche, noche + timedelta(days=1))
                filas.append({"noche": noche.isoformat(), "estado": d.estado,
                              "de": sorted({c["fuente"] for c in d.choques}) or None})
            salida[prop] = filas
        return salida


def de_la_cotizacion(oc: Ocupacion, cotizacion: dict | None) -> list[Disponibilidad]:
    """La disponibilidad de cada propiedad que una cotización ofrece con fechas
    (la de una propiedad o la de grupo, con sus opciones). Sin fechas: []."""
    if not cotizacion or not cotizacion.get("llegada") or not cotizacion.get("salida"):
        return []
    try:
        llegada, salida = date.fromisoformat(cotizacion["llegada"]), date.fromisoformat(cotizacion["salida"])
    except (TypeError, ValueError):
        return []
    props = [o.get("propiedad") for o in cotizacion.get("opciones") or []] or [cotizacion.get("propiedad")]
    return [oc.disponibilidad(p, llegada, salida) for p in props if p]


def apartada(espacio: Espacio, cotizacion: dict | None) -> str:
    """'' si nada de lo que ofrece la cotización está ocupado hoy; si no, qué.
    Se revisa al enviar: entre que se redactó y que una persona la aprobó, otra
    plataforma pudo vender esas noches (invariante LXIII)."""
    oc = Ocupacion.de(espacio)
    if not oc.configurada:
        return ""
    ocupadas = [d.propiedad for d in de_la_cotizacion(oc, cotizacion) if d.estado == OCUPADA]
    return f"fechas ya apartadas en el calendario: {', '.join(ocupadas)}" if ocupadas else ""


REFRESCO_MINUTOS = 30


def refrescar_todos(raiz=None) -> int:
    """Baja el calendario de cada espacio que tenga fuentes. Lo corre el servidor
    cada `REFRESCO_MINUTOS`; si un iCal falla, ese espacio queda en "no se sabe"
    hasta el siguiente intento, y el servidor sigue."""
    from .espacio import EspacioInvalido, raiz_por_defecto

    raiz = raiz or raiz_por_defecto()
    n = 0
    if not raiz.exists():
        return 0
    for carpeta in sorted(p for p in raiz.iterdir() if p.is_dir()):
        try:
            espacio = Espacio(carpeta.name, raiz)
        except EspacioInvalido:
            continue
        if fuentes(espacio):
            try:
                bajar(espacio)
                n += 1
            except Exception as error:  # un espacio roto no detiene a los demás
                print(f"calendario {carpeta.name}: {type(error).__name__}: {error}", file=sys.stderr)
    return n


# --------------------------------------------------------------------------- #
#  Línea de comandos                                                          #
# --------------------------------------------------------------------------- #
def _espacio_local(cliente_id: str) -> Espacio:
    from .local import _espacio
    return _espacio(cliente_id)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m agente.calendario")
    sub = p.add_subparsers(dest="orden", required=True)
    f = sub.add_parser("fuente", help="agrega o cambia el iCal de una propiedad en una plataforma")
    f.add_argument("cliente_id"), f.add_argument("propiedad"), f.add_argument("plataforma"), f.add_argument("url")
    b = sub.add_parser("bajar", help="descarga cada iCal y deja su estado")
    b.add_argument("cliente_id")
    v = sub.add_parser("ver", help="noches libres, ocupadas y sin saber")
    v.add_argument("cliente_id"), v.add_argument("--desde"), v.add_argument("--dias", type=int, default=30)
    a = p.parse_args(argv)
    espacio = _espacio_local(a.cliente_id)
    if a.orden == "fuente":
        agregar_fuente(espacio, a.propiedad, a.plataforma, a.url)
        print(f"{a.propiedad}-{a.plataforma} guardada en {espacio.ruta(ARCHIVO)}")
    elif a.orden == "bajar":
        for e in bajar(espacio):
            print(f"{e['fuente']:<24} {'ok' if e.get('ok') else 'FALLÓ'}  "
                  f"{e.get('bloques', '') if e.get('ok') else e.get('error', '')}")
    else:
        desde = date.fromisoformat(a.desde) if a.desde else datetime.now(ZONA).date()
        oc = Ocupacion.de(espacio)
        if not oc.configurada:
            print("sin fuentes: python -m agente.calendario fuente <id> <propiedad> <plataforma> <url>")
            return 1
        marca = {LIBRE: "·", OCUPADA: "■", NO_SE_SABE: "?"}
        for prop, filas in oc.noches(desde, a.dias).items():
            print(f"{prop:<8} " + "".join(marca[x["estado"]] for x in filas))
        print(f"desde {desde.isoformat()}, {a.dias} noches · libre  ■ ocupada  ? no se sabe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
