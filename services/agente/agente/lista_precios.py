"""La lista de precios del negocio, leída de las cotizaciones que ya dio por WhatsApp.

El dueño no tiene la lista escrita (vive en su cabeza y en imágenes); lo que sí
hay son cientos de cotizaciones escritas a clientes. Aquí se leen, sin modelo:

1. **Observar** (`observaciones`): cada monto que una persona del negocio
   escribió, partido en cláusulas (*"Con 6 habitaciones 22,000 el fin de semana
   / Con 9 habitaciones 28,000"* son dos), con su concepto (hospedaje, alberca,
   visita, habitación suelta, anticipo, depósito), su unidad (noche o fin de
   semana), la propiedad (la que la cláusula nombra o la última presentación de
   propiedad que el negocio mandó en esa plática), el grupo (lo que dice la
   cláusula, o lo último que el cliente dijo de cuántos son: `lectura.personas`)
   y las fechas del cliente.
2. **Agregar** (`agregar`): por propiedad × unidad × temporada × tamaño de
   grupo, el monto que más se repite, con su n, su acuerdo y los otros montos.
   **Nada se promedia**: el precio de la lista es uno que la casa escribió.
3. **Proponer** (`a_perfil`): las celdas con acuerdo suficiente se vuelven
   reglas `grupo` del perfil, cada una con la cita literal del negocio que trae
   el monto y, si el grupo lo dijo el cliente, la cita del cliente que lo prueba
   (`origen.grupo`, que `perfil.validar` revisa). Lo que no tiene acuerdo queda
   en `a_decidir`: lo resuelve el dueño, no el código.

La propuesta no se enciende sola: pasa por `perfil.proponer` y la aprueba quien
dice el alta. Los datos leídos son de clientes finales: todo lo que escribe esta
pieza va a `datos/espacios/<id>/lista_precios/` (fuera de git).
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from . import historial, lectura
from .conversacion import normalizar
from .espacio import Espacio
from .historial import Mensaje
from .perfil import numeros

CARPETA = "lista_precios"
#: Para que una celda entre a la propuesta: el monto que más se repite gana con
#: al menos esta parte de las veces y se vio en al menos estas pláticas.
ACUERDO_MINIMO = 0.6
PLATICAS_MINIMAS = 2
#: Un monto pelón (sin unidad ni contexto) menor a esto no se lee como hospedaje.
HOSPEDAJE_MINIMO = 3_000
#: Lo que cuesta un escalón más en la lista, en cotizaciones que coinciden: un
#: escalón nuevo tiene que explicar al menos una cotización más que sin él.
CASTIGO_POR_ESCALON = 1.0

_AMBAS = re.compile(r"\blas dos\b|\blas 2\b|\bambas\b|\b(?:2|dos) (?:propiedades|casas)\b")
_HABITACIONES = re.compile(r"\b(\d{1,2})\s*habitaciones\b")
_PERSONAS_NEGOCIO = re.compile(r"\b(?:para|por|hasta|de)\s+(\d{1,3})\s*personas\b|\b(\d{1,3})\s*personas\b")
_MONTO = re.compile(r"(?<![\d:/])\$?\s*(\d{1,3}(?:[.,]\d{3})+(?:,\d{1,2}(?!\d))?|\d+(?:[.,]\d{1,2}(?!\d))?)(\s*mil\b)?(?![\d:%])")
_NOCHE = re.compile(r"\bn(?:oc|co|o)he\b|\bnoches?\b|\bnocje\b")
_FIN = re.compile(r"\bfin de semana\b|\bel fin\b|\bfin\b(?! de ano)|\bviernes a domingo\b")
_ANTICIPO = re.compile(r"%|\bapart\w*|\banticipo\b|\bpagos?\b|\brestar\w*|\befectivo\b|\bfactura\b|\biva\b|\bcuenta\b"
                       r"|\bdepositad\w*|\bme dio\b|\bproporcional\b")
_DEPOSITO = re.compile(r"\bdeposito en garantia\b|\bgarantia\b")
_ALBERCA = re.compile(r"\balberca\b|\bcalefacc\w*|\bcaldera\b|\bclimatiz\w*")
_VISITA = re.compile(r"\bvisitas?\b")
_HABITACION_SUELTA = re.compile(r"\bla habitacion\b|\bhabitacion adicional\b|\bpor habitacion\b")
_OTRO = re.compile(r"\bmesas?\b|\bsillas?\b|\bcarpa\b|\bdesayuno\b|\bcomida\b|\balimentos?\b|\bpadre\b|\bmisa\b|\bdj\b"
                   r"|\bpista\b|\banimacion\b|\binflable\b|\btransporte\b|\bhieleras?\b|\bmenu\b|\bplatillos?\b"
                   r"|\bmontaje\b|\badicionales\b|\bhoras?\b|\bhrs\b|\bmariachi\b|\bbanquete\b|\bmeseros?\b")
_DIA = re.compile(r"\bel dia\b|\bpor dia\b|\bpor el dia\b|\bal dia\b|\bpor 8 hrs\b|\bdia\b")
_FIN_DE_ANO = re.compile(r"\bfin de ano\b|\bano nuevo\b|\bnavidad\b|\bnochebuena\b|\b(?:24|25|31) de dic\w*")
_URL = re.compile(r"https?://\S+|www\.\S+")
_CUENTA_BANCO = re.compile(r"\b\d{4}\s\d{4}\b|\bbanco\b|\bclabe\b|\btarjeta\b")


@dataclass
class Observacion:
    id: str                       # el mensaje del negocio
    hilo: str
    ts: int
    cita: str                     # la cláusula, literal del mensaje
    concepto: str                 # hospedaje | alberca | visita | habitacion | anticipo | deposito
    monto_centavos: int | None = None
    pct: int | None = None
    unidad: str | None = None     # noche | fin_de_semana | dia | persona | None
    propiedad: str | None = None
    personas: int | None = None
    grupo: dict | None = None     # {"id", "cita"}: el mensaje del cliente que dice cuántos son
    habitaciones: int | None = None
    llegada: str | None = None
    salida: str | None = None
    fin_de_ano: bool = False      # el cliente habló de fin de año / Navidad

    def a_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
#  Leer un mensaje                                                             #
# --------------------------------------------------------------------------- #
def montos(texto: str) -> list[int]:
    """Los montos en pesos de un texto, en orden. Las dos formas mexicanas:
    *"12.000"* y *"$600,00"*; *"5mil"* = 5000. Horas, porcentajes y años fuera."""
    salida = []
    for m in _MONTO.finditer(_URL.sub(" ", texto)):
        crudo, mil = m.group(1), m.group(2)
        grupos = re.split(r"[.,]", crudo)
        if len(grupos) > 1 and len(grupos[-1]) in (1, 2):
            grupos = grupos[:-1]
        if len(grupos) > 1 and not all(len(g) == 3 for g in grupos[1:]):
            continue
        valor = int("".join(grupos))
        if mil:
            valor *= 1000
        if re.fullmatch(r"20[0-3]\d", crudo) or valor < 100:
            continue
        salida.append(valor)
    return salida


def clausulas(texto: str) -> list[str]:
    """El mensaje en pedazos con un monto cada uno, literales. Una línea sin monto
    se pega a la anterior (*"12,000 el / Fin de semana"*)."""
    lineas = [x.strip() for x in texto.split("\n") if x.strip()]
    juntas: list[str] = []
    for linea in lineas:
        if juntas and (not montos(linea) or not montos(juntas[-1])):
            juntas[-1] += "\n" + linea
        else:
            juntas.append(linea)
    salida = []
    for pedazo in juntas:
        # "5500 la noche y el costo de la alberca 900": dos montos, dos cláusulas
        partes = re.split(r"\s+y\s+(?=[^\d\n]*\d)", pedazo)
        if len(partes) > 1 and all(montos(p) for p in partes):
            salida.extend(partes)
        else:
            salida.append(pedazo)
    return salida


def _cerca(clausula: str) -> str:
    """Desde la línea del primer monto hasta el final: ahí están su concepto y su
    unidad (*"Precio $ 10,000 por noche"* dentro de una plantilla de presentación
    que también habla de la alberca)."""
    lineas = clausula.split("\n")
    for i, linea in enumerate(lineas):
        if montos(linea):
            return "\n".join(lineas[i:])
    return clausula


def _monto_de(cerca: str) -> int | None:
    """El monto pegado a su unidad: en *"36,000 es decir 9,000 la noche"* la noche
    vale 9,000; en *"10,000 la noche pero podría bajarles a 9,000"*, 10,000."""
    t = cerca.casefold()
    unidad = re.search(r"n(?:oc|co|o)he|nocje|fin de semana|el fin\b|el d[ií]a|por persona", t)
    if unidad:
        antes = montos(cerca[:unidad.start()])
        if antes:
            return antes[-1]
    todos = montos(cerca)
    return todos[0] if todos else None


def concepto_de(t: str, monto: int | None, unidad: str | None, todo: str = "", previo: str = "") -> str | None:
    """`t`: desde el monto (concepto y unidad); `todo`: la cláusula entera (pagos);
    `previo`: lo último del cliente (*"¿y la alberca?"* → *"900 el día"*)."""
    todo = todo or t
    if previo and _ALBERCA.search(normalizar(previo)) and _DIA.search(t) and (monto or 0) < HOSPEDAJE_MINIMO:
        return "alberca"
    if _DEPOSITO.search(todo):
        return "deposito"
    if _ANTICIPO.search(todo):
        return "anticipo"
    if _ALBERCA.search(t):
        return "alberca"
    if _VISITA.search(t):
        return "visita"
    if _HABITACION_SUELTA.search(t):
        return "habitacion"
    if _OTRO.search(t):
        return None
    if monto is not None and monto >= HOSPEDAJE_MINIMO:
        return "hospedaje"
    return None


_PRESENTA = re.compile(r"\bhabitaciones\b|\bcapacidad\b|\btengo\b|\bopcion\b|\bdisponib\w*|\bcaben\b"
                       r"|\b(?:la|esta|otra) (?:quinta|finca)\b")


def propiedad_en(texto: str) -> str | None:
    """La propiedad que un mensaje del negocio presenta. Nombrarla no basta: la
    bienvenida (*"Gracias por comunicarte con Finca Emiliano"*) lleva el nombre del
    negocio y no presenta nada; *"Somos Finca Emiliano. Capacidad para 37"*,
    *"Quinta Emiliano es nuestra opción"* o *"Solo tengo la quinta"* sí."""
    t = normalizar(texto)
    if _AMBAS.search(t):
        return "ambas"
    quinta, finca = bool(re.search(r"\bquinta\b", t)), bool(re.search(r"\bfinca\b", t))
    if quinta == finca or not _PRESENTA.search(t):
        return None
    return "quinta" if quinta else "finca"


def _nombrada_en(clausula: str) -> str | None:
    """En la cláusula del precio basta nombrarla: *"La quinta 5,000 la noche"*."""
    t = normalizar(clausula)
    q, f = bool(re.search(r"\bquinta\b", t)), bool(re.search(r"\bfinca\b", t))
    return ("quinta" if q else "finca") if q != f else None


def propiedad_en_platica(hilo: list[Mensaje]) -> str | None:
    """La propiedad de la que se está hablando: la última que el cliente nombró
    o que el negocio presentó."""
    actual = None
    for m in hilo:
        if not m.texto:
            continue
        if m.del_negocio:
            actual = propiedad_en(m.texto) or actual
        else:
            t = normalizar(m.texto)
            q, f = bool(re.search(r"\bla quinta\b", t)), bool(re.search(r"\bla finca\b", t))
            if q != f:
                actual = "quinta" if q else "finca"
    return actual


def _unidad(t: str, previo_cliente: str) -> str | None:
    if _NOCHE.search(t):
        return "noche"
    if _FIN.search(t):
        return "fin_de_semana"
    c = normalizar(previo_cliente)
    if re.search(r"\b(?:solo |nada mas )?(?:1|una) noche\b", c):
        return "noche"
    if re.search(r"\bfin de semana\b|\bviernes a domingo\b|\bdel viernes al domingo\b", c):
        return "fin_de_semana"
    return None


def _unidad_por_fechas(fechas: tuple[date, date] | None) -> str | None:
    """Sin unidad escrita, la dicen las fechas del cliente: una noche, o de viernes
    a domingo."""
    if not fechas:
        return None
    llegada, salida = fechas
    if (salida - llegada).days == 1:
        return "noche"
    if (salida - llegada).days == 2 and llegada.weekday() == 4:
        return "fin_de_semana"
    return None


def observaciones(hilos: dict[str, list[Mensaje]]) -> list[Observacion]:
    salida: list[Observacion] = []
    for hilo, ms in hilos.items():
        propiedad = None
        for i, m in enumerate(ms):
            if not m.del_negocio or not m.texto:
                continue
            nombrada = propiedad_en(m.texto)
            if not montos(m.texto) or _CUENTA_BANCO.search(normalizar(m.texto)):
                propiedad = nombrada or propiedad
                continue
            prefijo = ms[:i]
            previo = "\n".join(x.texto or "" for x in prefijo[-4:] if not x.del_negocio)
            grupo_msg = _quien_dijo_personas(prefijo)
            fechas = lectura.fechas(prefijo)
            fin_de_ano = any(_FIN_DE_ANO.search(normalizar(x.texto or "")) for x in prefijo if not x.del_negocio)
            for cl in clausulas(m.texto):
                cerca = _cerca(cl)
                t, todo = normalizar(cerca), normalizar(cl)
                unidad = _unidad(t, previo)
                monto = _monto_de(cerca)
                concepto = concepto_de(t, monto, unidad, todo, previo.split("\n")[-1] if previo else "")
                if concepto is None or (monto is None and "%" not in t):
                    continue
                o = Observacion(id=m.id, hilo=hilo, ts=m.ts, cita=cerca, concepto=concepto,
                                propiedad=propiedad_en(cl) or _nombrada_en(cl) or nombrada or propiedad,
                                fin_de_ano=fin_de_ano)
                if fechas:
                    o.llegada, o.salida = fechas[0].isoformat(), fechas[1].isoformat()
                if (h := _HABITACIONES.search(t)):
                    o.habitaciones = int(h.group(1))
                elif (h := _HABITACIONES.search(todo)):
                    o.habitaciones, o.cita = int(h.group(1)), cl
                if concepto == "anticipo":
                    pct = re.search(r"(\d{1,2})\s*%", cl)
                    if pct:
                        o.pct, o.unidad = int(pct.group(1)), None
                    else:
                        o.monto_centavos = monto * 100 if monto else None
                    salida.append(o)
                    continue
                o.monto_centavos = monto * 100
                if concepto == "alberca":
                    o.unidad = "dia" if _DIA.search(t) else None
                elif concepto == "visita":
                    o.unidad = "persona" if re.search(r"\bpersona\b", t) else None
                elif concepto == "habitacion":
                    o.unidad = "noche"
                    p = re.search(r"\bpara (\d{1,2}) personas\b", t)
                    o.personas = int(p.group(1)) if p else None
                else:
                    o.unidad = unidad or _unidad_por_fechas(fechas)
                    p = _PERSONAS_NEGOCIO.search(t) or _PERSONAS_NEGOCIO.search(todo)
                    if p:
                        o.personas = int(next(g for g in p.groups() if g))
                        if not _PERSONAS_NEGOCIO.search(t):
                            o.cita = cl
                    elif grupo_msg is not None:
                        o.personas = lectura.personas_en(grupo_msg.texto) or lectura.personas(prefijo)
                        o.grupo = {"id": grupo_msg.id, "cita": grupo_msg.texto}
                    if o.habitaciones and o.habitaciones >= 6 and o.propiedad in (None, "quinta"):
                        o.propiedad = o.propiedad or "finca"
                salida.append(o)
            propiedad = nombrada or propiedad
    return sorted(salida, key=lambda o: (o.ts, o.id, o.cita))


def _quien_dijo_personas(prefijo: list[Mensaje]) -> Mensaje | None:
    """El mensaje del cliente del que sale `lectura.personas(prefijo)`."""
    n = lectura.personas(prefijo)
    if n is None:
        return None
    for i in range(len(prefijo) - 1, -1, -1):
        m = prefijo[i]
        if not m.del_negocio and m.texto and lectura.personas(prefijo[:i + 1]) == n \
                and lectura.personas(prefijo[:i]) != n:
            return m
    return None


# --------------------------------------------------------------------------- #
#  Temporada                                                                   #
# --------------------------------------------------------------------------- #
_MINIMO = re.compile(r"\bminimo\s*/?\s*(\d)\s*noches\b|\b(\d)\s*noches minimo\b|\bsolo por (\d) noches\b")
_ALTA = re.compile(r"\btemporada alta\b|\besa temporada\b")
NOMBRE_ALTA = "fin_de_ano"


def temporada_observada(hilos: dict[str, list[Mensaje]]) -> tuple[list[dict], list[dict]]:
    """La temporada alta como la dice la casa: las noches de las estancias a las que
    les escribió *"mínimo 3 noches"* o *"temporada alta"*, de la primera a la última.
    Es lo observado, no lo que el dueño decidió: va `a_confirmar`.

    Devuelve (temporadas, reglas de estancia mínima)."""
    noches: list[date] = []
    minimos: Counter = Counter()
    citas: dict[int, Mensaje] = {}
    alta: Mensaje | None = None
    for ms in hilos.values():
        for i, m in enumerate(ms):
            if not (m.del_negocio and m.texto):
                continue
            t = normalizar(m.texto)
            minimo = _MINIMO.search(t)
            if not (minimo or _ALTA.search(t)):
                continue
            if _ALTA.search(t) and (alta is None or m.ts > alta.ts):
                alta = m
            if minimo:
                n = int(next(g for g in minimo.groups() if g))
                minimos[n] += 1
                if n not in citas or m.ts > citas[n].ts:
                    citas[n] = m
            if (f := lectura.fechas(ms[:i])):
                noches += [f[0] + timedelta(days=k) for k in range((f[1] - f[0]).days)]
    if not noches or alta is None:
        return [], []
    desde, hasta = min(noches), max(noches)
    origen_alta = {"tipo": "mensaje", "id": alta.id, "cita": _linea_con(alta.texto, _ALTA)}
    temporada = {"nombre": NOMBRE_ALTA, "desde": f"{desde:%m-%d}", "hasta": f"{hasta:%m-%d}", "fin_de_ano": True,
                 "a_confirmar": True, "evidencia": {"noches_vistas": len(noches)}, "origen": origen_alta}
    reglas = []
    if minimos:
        n, veces = minimos.most_common(1)[0]
        m = citas[n]
        reglas.append({"tipo": "minimo_noches", "noches": n, "temporada": NOMBRE_ALTA,
                       "evidencia": {"n": sum(minimos.values()), "acuerdo": round(veces / sum(minimos.values()), 2)},
                       "origen": {"tipo": "mensaje", "id": m.id, "cita": _linea_con(m.texto, _MINIMO)}})
    return [temporada], reglas


def _linea_con(texto: str, patron: re.Pattern) -> str:
    """La línea literal que dice lo que se cita (una plantilla entera no es cita)."""
    lineas = [x for x in texto.split("\n") if x.strip()]
    return next((x.strip() for x in lineas if patron.search(normalizar(x))), texto.strip())


def temporada_de(o: Observacion, temporadas: list[dict]) -> str | None:
    """La temporada de la estancia del cliente (la de su llegada), si dio fechas;
    si no, la que nombró (*"fin de año"*) si coincide con una temporada."""
    from .cotizador import temporada_de as _de

    if o.llegada:
        return _de(date.fromisoformat(o.llegada), temporadas)
    if o.fin_de_ano:
        return next((t["nombre"] for t in temporadas if t.get("fin_de_ano")), None)
    return None


# --------------------------------------------------------------------------- #
#  La lista                                                                    #
# --------------------------------------------------------------------------- #
@dataclass
class Celda:
    propiedad: str
    concepto: str
    unidad: str | None
    temporada: str | None
    personas: int | None
    montos: Counter = field(default_factory=Counter)
    platicas: set = field(default_factory=set)
    obs: list = field(default_factory=list)
    desde: int | None = None

    @property
    def n(self) -> int:
        return sum(self.montos.values())

    @property
    def moda(self) -> tuple[int, int]:
        """(monto, veces). Empate: el más reciente de los empatados."""
        tope = max(self.montos.values())
        empatados = {mo for mo, v in self.montos.items() if v == tope}
        ultimo = max((o for o in self.obs if o.monto_centavos in empatados), key=lambda o: o.ts)
        return ultimo.monto_centavos, tope

    @property
    def acuerdo(self) -> float:
        return self.moda[1] / self.n if self.n else 0.0

    @property
    def entra(self) -> bool:
        return self.acuerdo >= ACUERDO_MINIMO and len(self.platicas) >= PLATICAS_MINIMAS

    def a_dict(self) -> dict:
        monto, veces = self.moda
        return {"propiedad": self.propiedad, "concepto": self.concepto, "unidad": self.unidad,
                "temporada": self.temporada, "personas": self.personas, "monto_centavos": monto,
                "n": self.n, "platicas": len(self.platicas), "acuerdo": round(self.acuerdo, 2),
                "otros": {str(k // 100): v for k, v in self.montos.most_common() if k != monto},
                "entra": self.entra}


def agregar(obs: list[Observacion], temporadas: list[dict]) -> list[Celda]:
    """Una celda por propiedad × concepto × unidad × temporada × personas. Una
    plática cuenta una vez por celda y monto (una plantilla repetida a la misma
    persona no es otra cotización)."""
    celdas: dict[tuple, Celda] = {}
    vistos: set[tuple] = set()
    for o in obs:
        if o.concepto in ("anticipo", "deposito") or o.monto_centavos is None or not o.propiedad:
            continue
        if o.concepto == "hospedaje" and (o.unidad is None or o.personas is None):
            continue
        temporada = temporada_de(o, temporadas) if o.concepto in ("hospedaje", "habitacion") else None
        clave = (o.propiedad, o.concepto, o.unidad, temporada,
                 o.personas if o.concepto in ("hospedaje", "habitacion") else None)
        if (o.hilo, o.monto_centavos) + clave in vistos:
            continue
        vistos.add((o.hilo, o.monto_centavos) + clave)
        c = celdas.setdefault(clave, Celda(*clave))
        c.montos[o.monto_centavos] += 1
        c.platicas.add(o.hilo)
        c.obs.append(o)
    return sorted(celdas.values(), key=lambda c: (c.propiedad, c.concepto, c.unidad or "", c.temporada or "",
                                                  c.personas or 0))


def _junta(celdas: list[Celda]) -> Celda:
    """Varias celdas de una tabla en una banda: "de `desde` hasta `personas`"."""
    b = Celda(celdas[0].propiedad, celdas[0].concepto, celdas[0].unidad, celdas[0].temporada, celdas[-1].personas)
    for c in celdas:
        b.montos.update(c.montos)
        b.platicas |= c.platicas
        b.obs += c.obs
    b.desde = celdas[0].desde if celdas[0].desde is not None else celdas[0].personas
    return b


def bandas(tabla: list[Celda]) -> list[Celda]:
    """Los escalones de una tabla (propiedad × unidad × temporada), por tamaño de grupo.

    Programación dinámica sobre los tamaños vistos: se eligen los cortes que
    hacen que más cotizaciones de la casa coincidan con el monto de su escalón,
    pagando `CASTIGO_POR_ESCALON` por cada escalón (sin castigo, cada tamaño sería
    su propio escalón y la lista no generalizaría), y con montos que **no bajan**
    al crecer el grupo (un grupo más grande no paga menos en una lista)."""
    tabla = sorted(tabla, key=lambda c: c.personas)
    n = len(tabla)
    # mejor[j] = {monto del último escalón: (puntos, cortes)} cubriendo tabla[:j]
    mejor: list[dict] = [dict() for _ in range(n + 1)]
    mejor[0][0] = (0.0, [])
    for j in range(1, n + 1):
        for i in range(j):
            banda = _junta(tabla[i:j])
            monto, veces = banda.moda
            for previo, (puntos, cortes) in mejor[i].items():
                if monto < previo:
                    continue
                total = puntos + veces - CASTIGO_POR_ESCALON
                if monto not in mejor[j] or total > mejor[j][monto][0]:
                    mejor[j][monto] = (total, cortes + [(i, j)])
    if not mejor[n]:
        return []
    _, cortes = max(mejor[n].values(), key=lambda x: x[0])
    salida = []
    for i, j in cortes:
        b = _junta(tabla[i:j])
        if b.entra:
            # "hasta N": el grupo más grande que pagó el monto de la lista, no el
            # más grande que se vio (un grupo de 120 no cabe porque alguien preguntó)
            b.personas = max(o.personas for o in b.obs if o.monto_centavos == b.moda[0])
        salida.append(b)
    return salida


def tablas(celdas: list[Celda]) -> list[Celda]:
    """Todas las bandas de hospedaje, tabla por tabla."""
    por_tabla: dict[tuple, list[Celda]] = defaultdict(list)
    for c in celdas:
        if c.concepto == "hospedaje":
            por_tabla[(c.propiedad, c.unidad, c.temporada)].append(c)
    return [b for clave in sorted(por_tabla, key=lambda k: tuple(x or "" for x in k))
            for b in bandas(por_tabla[clave])]


def _origen(c: Celda, monto: int | None = None) -> dict:
    """La cita más reciente de la banda con el monto de la lista y con el tamaño
    de grupo del escalón (el renglón dice "hasta N": N tiene que estar probado)."""
    monto = c.moda[0] if monto is None else monto
    candidatas = [x for x in c.obs if x.monto_centavos == monto and x.personas == c.personas] \
        or [x for x in c.obs if x.personas == c.personas]
    if monto == -1:
        # sin monto en la lista: la cita prueba el tamaño de grupo, no un precio
        candidatas = [x for x in c.obs if x.personas == c.personas]
    o = max(candidatas, key=lambda x: x.ts)
    origen = {"tipo": "mensaje", "id": o.id, "cita": o.cita}
    if o.grupo and str(c.personas) not in numeros(o.cita):
        origen["grupo"] = o.grupo
    return origen


def _evidencia(c: Celda) -> dict:
    ev = {"n": c.n, "platicas": len(c.platicas), "acuerdo": round(c.acuerdo, 2),
          "otros": {str(k // 100): v for k, v in c.montos.most_common() if k != c.moda[0]}}
    if c.desde is not None and c.desde != c.personas:
        ev["desde_personas"] = c.desde
    return ev


def a_perfil(celdas: list[Celda], obs: list[Observacion], temporadas: list[dict]) -> tuple[list[dict], list[dict]]:
    """(reglas para el perfil, lo que queda a decidir del dueño).

    Una banda sin acuerdo también entra, como `a_decidir` y sin monto: así el
    cotizador no salta al escalón de arriba (cobrarle a 12 personas lo de 20) ni
    al de abajo; dice que ese precio lo pone el dueño."""
    reglas: list[dict] = []
    a_decidir: list[dict] = []
    for c in tablas(celdas):
        r = {"tipo": "grupo", "propiedad": c.propiedad, "unidad": c.unidad, "personas": c.personas}
        if c.temporada:
            r["temporada"] = c.temporada
        if c.entra:
            r["monto_centavos"] = c.moda[0]
            hab = {x.habitaciones for x in c.obs if x.monto_centavos == c.moda[0] and x.habitaciones}
            origen = _origen(c)
            if len(hab) == 1 and str(next(iter(hab))) in numeros(origen["cita"]):
                r["habitaciones"] = hab.pop()
        else:
            r["a_decidir"] = True
            origen = _origen(c, monto=-1)
            a_decidir.append({**c.a_dict(), "desde_personas": c.desde or c.personas})
        r["evidencia"], r["origen"] = _evidencia(c), origen
        reglas.append(r)
    for c in celdas:
        if c.concepto in ("alberca", "visita", "habitacion") and c.entra:
            r = {"tipo": "extra", "concepto": c.concepto, "propiedad": c.propiedad, "unidad": c.unidad,
                 "monto_centavos": c.moda[0], "evidencia": _evidencia(c), "origen": _origen(c)}
            if c.concepto == "habitacion" and c.personas:
                r["personas"] = c.personas
            reglas.append(r)
    pcts = Counter(o.pct for o in obs if o.concepto == "anticipo" and o.pct)
    if pcts:
        pct, veces = pcts.most_common(1)[0]
        if veces / sum(pcts.values()) >= ACUERDO_MINIMO:
            o = max((x for x in obs if x.pct == pct), key=lambda x: x.ts)
            for prop in sorted({r["propiedad"] for r in reglas if r["tipo"] == "grupo"}):
                reglas.append({"tipo": "anticipo", "propiedad": prop, "pct": pct,
                               "evidencia": {"n": sum(pcts.values()), "acuerdo": round(veces / sum(pcts.values()), 2)},
                               "origen": {"tipo": "mensaje", "id": o.id, "cita": o.cita}})
    return reglas, a_decidir


# --------------------------------------------------------------------------- #
#  Lo que se escribe                                                           #
# --------------------------------------------------------------------------- #
def leer(espacio: Espacio, hilos: dict[str, list[Mensaje]] | None = None,
         temporadas: list[dict] | None = None) -> dict:
    """La lista completa: observaciones, celdas, reglas propuestas y lo a decidir."""
    hilos = hilos if hilos is not None else historial.hilos(espacio)
    vistas, minimos = temporada_observada(hilos)
    if temporadas is None:
        temporadas = temporadas_del_espacio(espacio) or vistas
    obs = observaciones(hilos)
    celdas = agregar(obs, temporadas)
    reglas, a_decidir = a_perfil(celdas, obs, temporadas)
    propiedades = sorted({r["propiedad"] for r in reglas if r["tipo"] == "grupo" and r["propiedad"] != "ambas"})
    nombres = {t["nombre"] for t in temporadas}
    reglas += [{**r, "propiedad": p} for r in minimos if r["temporada"] in nombres for p in propiedades]
    return {"cliente_id": espacio.cliente_id, "observaciones": [o.a_dict() for o in obs],
            "celdas": [c.a_dict() for c in celdas], "reglas": reglas, "a_decidir": a_decidir,
            "temporadas": temporadas,
            "medido": {"cotizaciones": len(obs), "platicas": len({o.hilo for o in obs}),
                       "hospedaje": sum(o.concepto == "hospedaje" for o in obs),
                       "hospedaje_con_grupo_y_unidad": sum(o.concepto == "hospedaje" and o.personas is not None
                                                           and o.unidad is not None and o.propiedad is not None
                                                           for o in obs)}}


def reglas_de(hilos: dict[str, list[Mensaje]], obs: list[Observacion], temporadas: list[dict],
              minimos: list[dict]) -> list[dict]:
    celdas = agregar(obs, temporadas)
    reglas, _ = a_perfil(celdas, obs, temporadas)
    propiedades = sorted({r["propiedad"] for r in reglas if r["tipo"] == "grupo" and r["propiedad"] != "ambas"})
    nombres = {t["nombre"] for t in temporadas}
    return reglas + [{**r, "propiedad": p} for r in minimos if r["temporada"] in nombres for p in propiedades]


def para_la_vara(espacio: Espacio, activo: dict | None, material: list[Mensaje]):
    """(perfil con la lista armada del material, perfil por plática sin esa plática).

    El material es el de desarrollo (`vara.material_de_desarrollo`): la lista no
    ve el holdout ni el embargo. Para medir una plática se vuelve a armar sin sus
    cotizaciones: su propio precio no vota (como `vara.sin_la_platica` para las
    guardadas). Los renglones que no prueban su origen no entran."""
    from . import perfil

    hilos: dict[str, list[Mensaje]] = {}
    for m in sorted(material, key=lambda x: (x.ts, x.id)):
        hilos.setdefault(m.hilo, []).append(m)
    temporadas, minimos = temporada_observada(hilos)
    temporadas = (activo or {}).get("temporadas") or temporadas
    obs = observaciones(hilos)
    base = {**(activo or {}), "temporadas": temporadas}
    completo = {**base, "reglas": list((activo or {}).get("reglas", []) or []) + reglas_de(hilos, obs, temporadas, minimos)}
    completo, _ = perfil.validar(espacio, completo)
    cache: dict[str, dict] = {}

    def por_hilo(hilo: str) -> dict:
        if hilo not in hilos:
            return completo
        if hilo not in cache:
            sin = [o for o in obs if o.hilo != hilo]
            sin_hilos = {k: v for k, v in hilos.items() if k != hilo}
            t_sin, m_sin = temporada_observada(sin_hilos)
            t_sin = (activo or {}).get("temporadas") or t_sin
            reglas = list((activo or {}).get("reglas", []) or []) + reglas_de(sin_hilos, sin, t_sin, m_sin)
            cache[hilo] = {**base, "temporadas": t_sin, "reglas": reglas}
        return cache[hilo]

    return completo, por_hilo


def temporadas_del_espacio(espacio: Espacio) -> list[dict]:
    """Las temporadas del perfil activo o las de `lista_precios/temporadas.json`
    (las escribe una persona). Si no hay, `leer` usa la observada, `a_confirmar`."""
    from . import perfil

    activo = perfil.activo(espacio) or {}
    return activo.get("temporadas") or espacio.leer_json(f"{CARPETA}/temporadas.json", []) or []


def escribir(espacio: Espacio, lista: dict) -> dict:
    espacio.escribir_json(f"{CARPETA}/lista.json", lista)
    propuesta = {"nombre": "lista de precios leída de sus cotizaciones",
                 "perfil": {"reglas": lista["reglas"], "temporadas": lista["temporadas"]}}
    espacio.escribir_json(f"{CARPETA}/propuesta.json", propuesta)
    return {"lista": str(espacio.ruta(f"{CARPETA}/lista.json")),
            "propuesta": str(espacio.ruta(f"{CARPETA}/propuesta.json"))}


def tabla(lista: dict) -> str:
    """La lista para leerla: sin teléfonos ni textos de clientes, solo montos del negocio."""
    from .cotizador import pesos

    def unidad(u: str | None) -> str:
        return {"noche": "la noche", "fin_de_semana": "el fin de semana", "dia": "el día",
                "persona": "por persona"}.get(u or "", "?")

    lineas = [f"cotizaciones leídas: {lista['medido']}"]
    for r in lista["reglas"]:
        ev = r.get("evidencia", {})
        desde = ev.get("desde_personas")
        quien = (f"de {desde} a {r['personas']} personas" if desde else f"hasta {r['personas']} personas") \
            if r.get("personas") else ""
        hab = f" con {r['habitaciones']} habitaciones" if r.get("habitaciones") else ""
        cuanto = (f"{r['pct']}%" if "pct" in r else "A DECIDIR" if r.get("a_decidir")
                  else f"{r['noches']} noches" if "noches" in r else pesos(r["monto_centavos"]))
        lineas.append(f"  {r['propiedad']:<7} {r['tipo']:<8} {r.get('concepto', ''):<10} "
                      f"{r.get('temporada') or 'normal':<11} {quien}{hab}: {cuanto}"
                      f"{' ' + unidad(r.get('unidad')) if r.get('unidad') else ''}"
                      f"  (n={ev.get('n')}, pláticas={ev.get('platicas', '-')}, acuerdo={ev.get('acuerdo')}"
                      f"{', otros ' + str(ev['otros']) if ev.get('otros') else ''})")
    return "\n".join(lineas)


if __name__ == "__main__":
    import sys

    from .local import _espacio

    esp = _espacio(sys.argv[1])
    resultado = leer(esp)
    print(json.dumps(escribir(esp, resultado), ensure_ascii=False, indent=1))
    print(tabla(resultado))
