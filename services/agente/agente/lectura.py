"""Lo que el cliente ya escribió y el cotizador necesita: cuántos son y qué fechas.

Determinista y conservador: lo ambiguo no se lee. *"30, 31 de diciembre y 1 de
enero"* puede ser dos noches o tres; *"24 y 25 de diciembre"*, una o dos: no
hay fechas. Un número pelón (*"20"*) cuenta como personas solo si el negocio
acababa de preguntarlas. Sin fechas, el cotizador da la lista del grupo (por
noche y por fin de semana), no un total.

Medido contra las cotizaciones de Finca Emiliano (2026-07-29 → 2026-10-27):
la casa elige la propiedad por el tamaño del grupo, así que lo que hace falta
leer es el grupo (`docs/18`, D-030: en 96% de sus cifras el cliente no dijo la
propiedad).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from .conversacion import normalizar
from .historial import Mensaje

MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
         "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12}
_MES = r"(ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic)[a-z]*"
_ANIO = r"(?:\s*(?:de|del)?\s*(20\d\d))?"
#: Hora de México central, para leer "hoy" de un mensaje sin el reloj de pared.
ZONA = timezone(timedelta(hours=-6))

#: "del 23 al 27 de diciembre", "29 de diciembre al 2 de enero", "16-18 de octubre", "6 al 8 de nov 2026".
_DE = r"(?:de\.?\s*|d\s+)?"
_RANGO = re.compile(rf"\b(\d{{1,2}})(?:\s*{_DE}{_MES})?\s*(?:al|a|-)\s*(\d{{1,2}})\s*{_DE}{_MES}{_ANIO}")
#: "el 24 de diciembre" + "2 noches" / "una noche"
_UNA_FECHA = re.compile(rf"\b(\d{{1,2}})\s*{_DE}{_MES}{_ANIO}")
_NOCHES = re.compile(r"\b(\d{1,2}|una|dos|tres|cuatro|cinco)\s*noches?\b")
_PALABRA = {"una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5}

_MENORES = r"(\d{1,3}|un|una)\s*(?:nin[oa]s?|menor(?:es)?|jovenes|chicos|bebes?|adolescentes)"
_ADULTOS_Y = re.compile(rf"(\d{{1,3}})\s*(?:adultos?|personas?|mayores)\b(?:[\s,y+]*{_MENORES})?(?:[\s,y+]*{_MENORES})?")
_DE_A = re.compile(r"\b(?:de|entre)\s*(\d{1,3})\s*(?:a|y|-)\s*(\d{1,3})\s*(?:personas|pax|invitados|gente)?\b")
_SOMOS = re.compile(r"\b(?:somos|seriamos|seremos|vamos|van|son)\s+(?:como\s+|alrededor de\s+|aprox\w*\s+)?(\d{1,3})\b"
                    r"|\b(?:para|cupo de|las|los)\s+(\d{1,3})\s*(?:personas|pax|invitados|huespedes|gente)?\s*(?:aprox\w*)?\s*[?.!]*$"
                    r"|\b(\d{1,3})\s*(?:pax|huespedes|invitados|gente)\b")
_PELON = re.compile(r"^\s*(?:como\s+|aprox\w*\s+)?(\d{1,3})\s*(?:aprox\w*|personas?)?\s*[.!]*$")
_PREGUNTA_PERSONAS = re.compile(r"\bcuant[oa]s (?:personas|son|serian|vienen|huespedes|invitados)\b|\bpara cuant[oa]s\b")
MAXIMO_PERSONAS = 200


def personas_en(texto: str | None) -> int | None:
    """Cuántos son, dicho en un mensaje. *"8 adultos y 4 niños"* = 12; *"de 15 a 20"* = 20."""
    t = normalizar(texto or "")
    if not t:
        return None
    if (m := _ADULTOS_Y.search(t)):
        total = sum(1 if g in ("un", "una") else int(g) for g in m.groups() if g)
        return total if 0 < total <= MAXIMO_PERSONAS else None
    if (m := _DE_A.search(t)) and re.search(r"personas|pax|invitados|gente|somos|seriamos", t):
        n = max(int(m.group(1)), int(m.group(2)))
        return n if 0 < n <= MAXIMO_PERSONAS else None
    if (m := _SOMOS.search(t)):
        n = int(next(g for g in m.groups() if g))
        return n if 0 < n <= MAXIMO_PERSONAS else None
    return None


def personas(hilo: list[Mensaje]) -> int | None:
    """Lo último que el cliente dijo de cuántos son. Un número pelón cuenta solo
    si el negocio acababa de preguntar por las personas."""
    ultimo = None
    pregunto = False
    for m in hilo:
        if m.del_negocio:
            if m.texto:
                pregunto = bool(_PREGUNTA_PERSONAS.search(normalizar(m.texto)))
            continue
        if not m.texto:
            continue
        n = personas_en(m.texto)
        if n is None and pregunto:
            t = normalizar(m.texto)
            if (p := _PELON.match(t)) or (p := _DE_A.search(t)):
                n = max(int(g) for g in p.groups() if g)
                n = n if 0 < n <= MAXIMO_PERSONAS else None
        if n is not None:
            ultimo = n
            pregunto = False
    return ultimo


def _fecha(dia: int, mes: int, anio: int | None, hoy: date) -> date | None:
    """Sin año, la próxima vez que cae esa fecha (un cliente no cotiza el pasado)."""
    anios = [anio] if anio else [hoy.year, hoy.year + 1]
    for a in anios:
        try:
            f = date(a, mes, dia)
        except ValueError:
            return None
        if anio or f >= hoy - timedelta(days=1):
            return f
    return None


def fechas_en(texto: str | None, hoy: date) -> tuple[date, date] | None:
    """(llegada, salida) si el texto las dice sin ambigüedad; si no, None."""
    t = normalizar(texto or "")
    if (m := _RANGO.search(t)):
        d1, mes1, d2, mes2, anio = m.groups()
        mes2_n = MESES[mes2[:3]]
        mes1_n = MESES[mes1[:3]] if mes1 else (mes2_n if int(d1) < int(d2) else (mes2_n - 2) % 12 + 1)
        anio_n = int(anio) if anio else None
        salida = _fecha(int(d2), mes2_n, anio_n, hoy)
        if salida is None:
            return None
        llegada = _fecha(int(d1), mes1_n, salida.year - (1 if mes1_n > mes2_n else 0), hoy)
        if llegada is None or not 0 < (salida - llegada).days <= 30:
            return None
        return llegada, salida
    noches = _NOCHES.search(t)
    unas = _UNA_FECHA.findall(t)
    if noches and len(unas) == 1:
        d, mes, anio = unas[0]
        llegada = _fecha(int(d), MESES[mes[:3]], int(anio) if anio else None, hoy)
        n = _PALABRA.get(noches.group(1)) or int(noches.group(1))
        if llegada and 0 < n <= 30:
            return llegada, llegada + timedelta(days=n)
    return None


def hoy_de(m: Mensaje) -> date:
    return datetime.fromtimestamp(m.ts, ZONA).date()


def fechas(hilo: list[Mensaje]) -> tuple[date, date] | None:
    """Las últimas fechas que el cliente dijo sin ambigüedad."""
    ultimas = None
    for m in hilo:
        if not m.del_negocio and m.texto and (f := fechas_en(m.texto, hoy_de(m))):
            ultimas = f
    return ultimas


_PIDE_PRECIO = re.compile(r"\b(?:precio|precios|presio|costo|costos|costilla|cuanto|cotiza\w*|presupuesto|tarifa\w*)\b")


def pide_precio(texto: str | None) -> bool:
    return bool(_PIDE_PRECIO.search(normalizar(texto or "")))


_UNA_NOCHE = re.compile(r"\b(?:solo |nada mas |unicamente )?(?:1|una) noche\b")
_FIN_O_DOS = re.compile(r"\b(?:2|dos) noches\b|\bfin de semana\b|\bviernes a domingo\b|\bdel viernes al domingo\b")
_PREGUNTA_UNA = re.compile(r"\b(?:solo |nada mas )?(?:1|una) noche\s*\?|\b(?:solo |nada mas )?(?:1|una) noche$")
_SI = re.compile(r"^(?:si+|asi es|correcto|exacto|claro|aja|sip)\b")


def noches(hilo: list[Mensaje]) -> int | None:
    """Las noches que el cliente pidió sin dar fechas: 1, o 2 (*"fin de semana"*,
    *"2 noches"*). También el *"Sí"* a *"¿Solo 1 noche?"* del negocio."""
    ultimo = None
    pregunto_una = False
    for m in hilo:
        t = normalizar(m.texto or "")
        if m.del_negocio:
            if t:
                pregunto_una = bool(_PREGUNTA_UNA.search(t))
            continue
        if not t:
            continue
        if _UNA_NOCHE.search(t) or (pregunto_una and _SI.match(t)):
            ultimo = 1
        elif _FIN_O_DOS.search(t):
            ultimo = 2
        pregunto_una = False
    return ultimo
