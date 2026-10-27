"""El cotizador: la única pieza que pone una cifra, con las reglas del negocio como datos.

Heredado de Gestor Morelos (el bot nunca cotiza solo; el número lo hace el
código), pero sin reglas escritas en Python: las reglas son renglones del
perfil aprobado, cada uno con su origen (`perfil.py`).

Tipos de regla (sección `reglas` del perfil), todos con `propiedad`:

- `noche`: `monto_centavos` por noche; opcionales `temporada` y `dias`
  (`fin_de_semana` = noches de viernes y sábado, `entre_semana` = las demás).
- `persona_extra`: `monto_centavos` por persona y noche arriba de `personas`.
- `evento`: `monto_centavos` fijo por evento; opcional `temporada`.
- `minimo_noches`: `noches`; opcional `temporada`.
- `capacidad`: `personas` máximo.
- `anticipo`: `pct` del total.
- `deposito`: `monto_centavos` reembolsable, aparte del total.

Lo que falta no se adivina: si una noche no tiene regla, o dos reglas igual de
específicas dan montos distintos, la cotización sale incompleta, sin total y
con lo que falta escrito. Así lo pide `CLAUDE.md`: un factor sin respuesta no
entra al número.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")
FIN_DE_SEMANA = {4, 5}  # noches de viernes y sábado (weekday de la fecha de la noche)


def pesos(centavos: int) -> str:
    entero, cent = divmod(centavos, 100)
    return f"${entero:,}" + (f".{cent:02d}" if cent else "")


@dataclass
class Cotizacion:
    propiedad: str
    llegada: date
    salida: date
    personas: int
    evento: bool
    renglones: list[tuple[str, int]] = field(default_factory=list)
    anticipo_pct: int | None = None
    deposito_centavos: int | None = None
    faltan: list[str] = field(default_factory=list)

    @property
    def completa(self) -> bool:
        return not self.faltan

    @property
    def noches(self) -> int:
        return (self.salida - self.llegada).days

    @property
    def total(self) -> int | None:
        return sum(m for _, m in self.renglones) if self.completa else None

    @property
    def anticipo(self) -> int | None:
        if self.total is None or self.anticipo_pct is None:
            return None
        return (self.total * self.anticipo_pct + 50) // 100

    def texto(self) -> str:
        """El mensaje con la cifra, escrito por código. Sin total si falta algo."""
        fechas = _rango(self.llegada, self.salida)
        cabeza = (f"{self.propiedad.capitalize()}, {fechas} ({self.noches} "
                  f"{'noche' if self.noches == 1 else 'noches'}, {self.personas} personas"
                  f"{', con evento' if self.evento else ''})")
        if not self.completa:
            return cabeza + ": falta confirmar " + "; ".join(self.faltan) + "."
        partes = [f"{cabeza}: {pesos(self.total)}."]
        if self.anticipo is not None:
            partes.append(f"Anticipo de {self.anticipo_pct}%: {pesos(self.anticipo)}.")
        if self.deposito_centavos is not None:
            partes.append(f"Depósito reembolsable: {pesos(self.deposito_centavos)}.")
        return " ".join(partes)

    def a_dict(self) -> dict:
        return {"propiedad": self.propiedad, "llegada": self.llegada.isoformat(),
                "salida": self.salida.isoformat(), "personas": self.personas, "evento": self.evento,
                "renglones": self.renglones, "total": self.total, "anticipo_pct": self.anticipo_pct,
                "anticipo": self.anticipo, "deposito": self.deposito_centavos, "faltan": self.faltan,
                "texto": self.texto()}


def _rango(llegada: date, salida: date) -> str:
    if llegada.year == salida.year and llegada.month == salida.month:
        return f"del {llegada.day} al {salida.day} de {MESES[salida.month - 1]} de {salida.year}"
    return (f"del {llegada.day} de {MESES[llegada.month - 1]} de {llegada.year} "
            f"al {salida.day} de {MESES[salida.month - 1]} de {salida.year}")


def _md(texto: str) -> tuple[int, int]:
    mes, dia = texto.split("-")
    return int(mes), int(dia)


def temporada_de(dia: date, temporadas: list[dict]) -> str | None:
    clave = (dia.month, dia.day)
    for t in temporadas:
        desde, hasta = _md(t["desde"]), _md(t["hasta"])
        dentro = desde <= clave <= hasta if desde <= hasta else (clave >= desde or clave <= hasta)
        if dentro:
            return t["nombre"]
    return None


def _de(reglas: list[dict], tipo: str, propiedad: str) -> list[dict]:
    return [r for r in reglas if r.get("tipo") == tipo and r.get("propiedad") == propiedad]


def _elegir(candidatas: list[dict], temporada: str | None, dias: str | None, campo: str):
    """La regla más específica que aplica. (valor, '') o (None, por qué)."""
    aplican = [r for r in candidatas
               if r.get("temporada") in (None, temporada) and r.get("dias") in (None, dias)]
    if not aplican:
        return None, "sin regla"
    mejor = max(int(r.get("temporada") is not None) + int(r.get("dias") is not None) for r in aplican)
    top = {r.get(campo) for r in aplican
           if int(r.get("temporada") is not None) + int(r.get("dias") is not None) == mejor}
    if len(top) > 1:
        return None, "dos reglas chocan"
    return top.pop(), ""


def cotizar(perfil: dict, propiedad: str, llegada: date, salida: date, personas: int,
            evento: bool = False) -> Cotizacion:
    reglas = perfil.get("reglas", []) or []
    temporadas = perfil.get("temporadas", []) or []
    c = Cotizacion(propiedad=propiedad, llegada=llegada, salida=salida, personas=personas, evento=evento)
    if c.noches <= 0:
        c.faltan.append("fechas válidas (la salida va después de la llegada)")
        return c
    if not any(r.get("propiedad") == propiedad for r in reglas):
        c.faltan.append(f"las tarifas de {propiedad}")
        return c

    cap, _ = _elegir(_de(reglas, "capacidad", propiedad), None, None, "personas")
    if cap is not None and personas > cap:
        c.faltan.append(f"{personas} personas pasan la capacidad de {cap}")

    temporada_llegada = temporada_de(llegada, temporadas)
    minimo, _ = _elegir(_de(reglas, "minimo_noches", propiedad), temporada_llegada, None, "noches")
    if minimo is not None and c.noches < minimo:
        c.faltan.append(f"mínimo de {minimo} noches")

    extra_regla = _de(reglas, "persona_extra", propiedad)
    for i in range(c.noches):
        noche = llegada + timedelta(days=i)
        temporada = temporada_de(noche, temporadas)
        dias = "fin_de_semana" if noche.weekday() in FIN_DE_SEMANA else "entre_semana"
        monto, por_que = _elegir(_de(reglas, "noche", propiedad), temporada, dias, "monto_centavos")
        etiqueta = f"noche del {noche.day} de {MESES[noche.month - 1]}"
        if monto is None:
            c.faltan.append(f"tarifa de la {etiqueta} ({por_que})")
            continue
        c.renglones.append((etiqueta, monto))
        if extra_regla:
            regla = min(extra_regla, key=lambda r: r.get("personas", 0))
            extra = personas - int(regla.get("personas", 0))
            if extra > 0:
                c.renglones.append((f"{extra} personas extra, {etiqueta}", extra * regla["monto_centavos"]))

    if evento:
        monto, por_que = _elegir(_de(reglas, "evento", propiedad), temporada_llegada, None, "monto_centavos")
        if monto is None:
            c.faltan.append(f"tarifa de evento ({por_que})")
        else:
            c.renglones.append(("evento", monto))

    c.anticipo_pct, _ = _elegir(_de(reglas, "anticipo", propiedad), None, None, "pct")
    c.deposito_centavos, _ = _elegir(_de(reglas, "deposito", propiedad), None, None, "monto_centavos")
    return c


# --------------------------------------------------------------------------- #
#  Por grupo: la casa elige la propiedad por el tamaño del grupo               #
# --------------------------------------------------------------------------- #
#: Regla `grupo` (la arma `lista_precios` con las cotizaciones del negocio):
#: `propiedad`, `unidad` (`noche` | `fin_de_semana`), `personas` (el escalón:
#: "hasta N"), `monto_centavos`, opcionales `temporada` y `habitaciones`. Con
#: `a_decidir` no trae monto: ese escalón lo pone el dueño, y el cotizador no
#: salta al de arriba ni al de abajo.
UNIDADES = {"noche": "la noche", "fin_de_semana": "el fin de semana"}


def es_fin_de_semana(llegada: date, salida: date) -> bool:
    """Viernes a domingo: las dos noches que la casa cobra como "el fin de semana"."""
    return llegada.weekday() == 4 and (salida - llegada).days == 2


@dataclass
class Opcion:
    propiedad: str
    personas: int                 # el grupo
    escalon: int | None = None    # "hasta N personas"
    habitaciones: int | None = None
    temporada: str | None = None
    unidad: str | None = None
    unitario: int | None = None   # centavos por noche o por fin de semana
    veces: int = 1                # noches (o 1 fin de semana)
    faltan: list[str] = field(default_factory=list)

    @property
    def completa(self) -> bool:
        return not self.faltan and self.unitario is not None

    @property
    def total(self) -> int | None:
        return self.unitario * self.veces if self.completa else None

    def a_dict(self) -> dict:
        return {"propiedad": self.propiedad, "personas": self.personas, "escalon": self.escalon,
                "habitaciones": self.habitaciones, "temporada": self.temporada, "unidad": self.unidad,
                "unitario": self.unitario, "veces": self.veces, "total": self.total, "faltan": self.faltan}


@dataclass
class CotizacionGrupo:
    personas: int
    llegada: date | None = None
    salida: date | None = None
    opciones: list[Opcion] = field(default_factory=list)
    faltan: list[str] = field(default_factory=list)
    anticipo_pct: int | None = None

    @property
    def completas(self) -> list[Opcion]:
        return [o for o in self.opciones if o.completa]

    @property
    def completa(self) -> bool:
        """Hay al menos una opción con precio y nada general falta."""
        return bool(self.completas) and not self.faltan

    @property
    def noches(self) -> int | None:
        return (self.salida - self.llegada).days if self.llegada and self.salida else None

    def texto(self) -> str:
        """Escrito por código, una línea por opción, la más económica primero (como
        la casa: *"O si quiere algo más económico…"*). Lo que falta no lleva cifra."""
        if not self.completa:
            return "Falta confirmar " + "; ".join(self.faltan or [f for o in self.opciones for f in o.faltan]) + "."
        lineas = []
        for o in self.completas:
            nombre = o.propiedad.capitalize() if o.propiedad != "ambas" else "Las dos casas"
            hab = f" con {o.habitaciones} habitaciones" if o.habitaciones else ""
            if self.llegada and self.salida:
                fechas = _rango(self.llegada, self.salida)
                noches = f"{self.noches} {'noche' if self.noches == 1 else 'noches'}"
                lineas.append(f"{nombre}, {fechas} ({noches}, {self.personas} personas{hab}): {pesos(o.total)}.")
            else:
                lineas.append(f"{nombre} para {self.personas} personas{hab}: {pesos(o.unitario)} "
                              f"{UNIDADES.get(o.unidad, '')}.".replace(" .", "."))
        if self.anticipo_pct:
            lineas.append(f"Se aparta con el {self.anticipo_pct}% y el resto al llegar.")
        return "\n".join(lineas)

    def a_dict(self) -> dict:
        return {"modo": "grupo", "personas": self.personas,
                "llegada": self.llegada.isoformat() if self.llegada else None,
                "salida": self.salida.isoformat() if self.salida else None,
                "opciones": [o.a_dict() for o in self.opciones], "faltan": self.faltan,
                "anticipo_pct": self.anticipo_pct, "completa": self.completa, "texto": self.texto()}


def _escalon(reglas: list[dict], personas: int) -> tuple[dict | None, str]:
    """El escalón más chico que cabe al grupo. (regla, '') o (None, por qué)."""
    caben = [r for r in reglas if int(r.get("personas") or 0) >= personas]
    if not caben:
        return None, "no cabe"
    menor = min(int(r["personas"]) for r in caben)
    top = [r for r in caben if int(r["personas"]) == menor]
    if any(r.get("a_decidir") for r in top):
        return None, "a decidir"
    if len({r.get("monto_centavos") for r in top}) > 1:
        return None, "dos reglas chocan"
    return top[0], ""


def _de_la_tabla(reglas: list[dict], propiedad: str, unidad: str, temporada: str | None) -> list[dict]:
    """Las reglas de la tabla de esa temporada. Si la propiedad no tiene ninguna
    tabla para esa temporada, la normal; si tiene alguna (aunque de otra unidad),
    no: la temporada tiene sus precios y no se mezclan con los de la normal."""
    suyas = [r for r in reglas if r.get("tipo") == "grupo" and r.get("propiedad") == propiedad]
    if temporada and any(r.get("temporada") == temporada for r in suyas):
        return [r for r in suyas if r.get("unidad") == unidad and r.get("temporada") == temporada]
    return [r for r in suyas if r.get("unidad") == unidad and not r.get("temporada")]


def _unidades(reglas: list[dict], propiedad: str, temporada: str | None, noches: int | None) -> list[str]:
    """En qué unidad se cotiza sin fechas: la que pidió el cliente (una noche, o el
    fin de semana) o, si no dijo, la que esa propiedad usa más en su lista."""
    if noches == 1:
        return ["noche"]
    if noches == 2:
        return ["fin_de_semana", "noche"]
    peso = {u: sum((r.get("evidencia") or {}).get("n", 1) for r in _de_la_tabla(reglas, propiedad, u, temporada))
            for u in UNIDADES}
    return sorted(UNIDADES, key=lambda u: -peso[u])


def _opcion(perfil: dict, propiedad: str, personas: int, llegada: date | None, salida: date | None,
            nombrada: str | None = None, noches: int | None = None) -> Opcion | None:
    """La opción de una propiedad, o None si el grupo no cabe en ella."""
    reglas = perfil.get("reglas", []) or []
    temporadas = perfil.get("temporadas", []) or []
    temporada = temporada_de(llegada, temporadas) if llegada else nombrada
    o = Opcion(propiedad=propiedad, personas=personas, temporada=temporada)
    if llegada and salida:
        noches = (salida - llegada).days
        nombres = {temporada_de(llegada + timedelta(days=i), temporadas) for i in range(noches)}
        if len(nombres) > 1:
            o.faltan.append("una estancia que cruza dos temporadas")
            return o
        unidades = ["fin_de_semana", "noche"] if es_fin_de_semana(llegada, salida) else ["noche"]
        o.veces = noches
    else:
        unidades = _unidades(reglas, propiedad, temporada, noches)
    hubo_tabla = False
    for unidad in unidades:
        tabla = _de_la_tabla(reglas, propiedad, unidad, temporada)
        if not tabla:
            continue
        hubo_tabla = True
        r, por_que = _escalon(tabla, personas)
        if r is None:
            if por_que == "no cabe":
                continue
            o.unidad = unidad
            o.faltan.append(f"el precio de {propiedad} para {personas} personas {UNIDADES[unidad]} ({por_que})")
            return o
        o.unidad, o.unitario, o.escalon = unidad, int(r["monto_centavos"]), int(r["personas"])
        o.habitaciones = r.get("habitaciones")
        if unidad == "fin_de_semana":
            o.veces = 1
        elif not llegada and noches:
            o.veces = noches
        break
    if o.unitario is None and not o.faltan:
        if not hubo_tabla:
            return None
        if llegada and salida and not any(_de_la_tabla(reglas, propiedad, "noche", temporada)):
            o.faltan.append(f"la tarifa por noche de {propiedad}")
            return o
        return None  # hay tablas, pero el grupo no cabe en ninguna
    if llegada and salida and o.completa:
        minimo, _ = _elegir([r for r in reglas if r.get("tipo") == "minimo_noches"
                             and r.get("propiedad") in (None, propiedad)], temporada, None, "noches")
        if minimo is not None and (salida - llegada).days < int(minimo):
            o.faltan.append(f"mínimo de {minimo} noches en {propiedad}")
    return o


def cotizar_grupo(perfil: dict, personas: int, llegada: date | None = None,
                  salida: date | None = None, temporada: str | None = None,
                  propiedad: str | None = None, noches: int | None = None) -> CotizacionGrupo:
    """Las opciones para un grupo, por propiedad, con la lista del negocio.

    Con fechas, el total de la estancia (viernes a domingo al precio de fin de
    semana; si no, por noche). Sin fechas, el precio de la lista para ese grupo
    (por fin de semana o por noche), sin total; `temporada` es la que el cliente
    nombró sin fechas (*"para fin de año"*) y `noches` las que pidió (1 o 2).
    `propiedad` es de la que se está hablando: si el grupo cabe en ella, solo esa
    (la casa cotiza lo que ya presentó). Lo que falta no se adivina."""
    c = CotizacionGrupo(personas=personas, llegada=llegada, salida=salida)
    if personas <= 0:
        c.faltan.append("cuántas personas son")
        return c
    if llegada and salida and salida <= llegada:
        c.faltan.append("fechas válidas (la salida va después de la llegada)")
        return c
    reglas = perfil.get("reglas", []) or []
    propiedades = sorted({r["propiedad"] for r in reglas if r.get("tipo") == "grupo" and r.get("propiedad")})
    if not propiedades:
        c.faltan.append("la lista de precios por grupo")
        return c
    cabe_en_una = any(r.get("tipo") == "grupo" and r.get("propiedad") != "ambas"
                      and int(r.get("personas") or 0) >= personas for r in reglas)
    for propiedad_ in propiedades:
        if propiedad_ == "ambas" and cabe_en_una:
            continue  # "las dos casas" solo si el grupo no cabe en una
        o = _opcion(perfil, propiedad_, personas, llegada, salida, temporada, noches)
        if o is not None:
            c.opciones.append(o)
    if propiedad and any(o.propiedad == propiedad and o.completa for o in c.opciones):
        c.opciones = [o for o in c.opciones if o.propiedad == propiedad]
    c.opciones.sort(key=lambda o: (not o.completa, o.total if o.total is not None else o.unitario or 0))
    if c.completas:
        c.opciones = c.completas  # lo que falta de otra propiedad no detiene a la que sí tiene precio
    if not c.opciones:
        c.faltan.append(f"dónde caben {personas} personas")
    elif not c.completas:
        c.faltan.extend(f for o in c.opciones for f in o.faltan)
    anticipos = {r.get("pct") for r in reglas if r.get("tipo") == "anticipo" and r.get("pct")
                 and r.get("propiedad") in {o.propiedad for o in c.completas}}
    if len(anticipos) == 1:
        c.anticipo_pct = int(anticipos.pop())
    return c


def extra(perfil: dict, concepto: str, propiedad: str | None) -> dict | None:
    """El precio de un extra de la lista (*"La alberca 2,000 el día"*) para la
    propiedad de la que se habla; sin propiedad, solo si es uno solo."""
    reglas = [r for r in perfil.get("reglas", []) or [] if r.get("tipo") == "extra" and r.get("concepto") == concepto
              and r.get("monto_centavos") is not None]
    if propiedad:
        reglas = [r for r in reglas if r.get("propiedad") == propiedad]
    return reglas[0] if len({r["monto_centavos"] for r in reglas}) == 1 else None
