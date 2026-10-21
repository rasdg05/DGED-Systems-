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
