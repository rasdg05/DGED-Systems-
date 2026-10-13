"""Cruces deterministas entre documentos. Aquí no hay modelo: solo valores verificados.

Cada bandera trae evidencia con documento, página y cita. Una AUSENCIA (contrato
sin garantía) no tiene cita: su evidencia dice qué páginas se leyeron, y si el
valor existía pero se descartó por cita no literal, lo dice en vez de afirmar
que no existe.
"""
from __future__ import annotations

import calendar
import re
import unicodedata
from collections import defaultdict
from datetime import date

from .extraccion import Resultado, Valor

ALTA, MEDIA = "alta", "media"
ORDEN_SEVERIDAD = {ALTA: 0, MEDIA: 1}
TOLERANCIA_M2 = 0.01  # 1 %: redondeos de escritura contra contrato no son bandera

SUFIJOS_SOCIETARIOS = re.compile(
    r"\b(s\s*a\s*p\s*i|s\s*a\s*b|s\s*a|s\s*de\s*r\s*l|s\s*c|de\s*c\s*v|de|c\s*v)\b"
)


def sumar_meses(fecha: date, meses: int) -> date:
    mes = fecha.month - 1 + meses
    anio = fecha.year + mes // 12
    mes = mes % 12 + 1
    return date(anio, mes, min(fecha.day, calendar.monthrange(anio, mes)[1]))


def _llano(texto: str) -> str:
    sin_acentos = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", sin_acentos)).strip()


def clave_nave(texto: str) -> str:
    """'Nave 2', 'NAVE  2', 'nave no. 2' -> 'nave 2'."""
    llano = _llano(texto)
    m = re.search(r"\bnave\s*(?:no\s*|num\s*|numero\s*)?(\w+)", llano)
    return f"nave {m.group(1)}" if m else llano


def clave_inquilino(texto: str) -> str:
    """Razón social sin acentos, signos ni sufijo societario."""
    llano = _llano(texto)
    sin_sufijo = SUFIJOS_SOCIETARIOS.sub(" ", llano)
    return re.sub(r"\s+", " ", sin_sufijo).strip()


def _bandera(codigo: str, severidad: str, detalle: str, evidencia: list[dict]) -> dict:
    return {"bandera": codigo, "severidad": severidad, "detalle": detalle, "evidencia": evidencia}


def _ausencia(resultado: Resultado, campo: str, paginas: int) -> dict:
    descartados = [d for d in resultado.descartados if d.campo == campo]
    if descartados:
        nota = f"el modelo propuso un valor pero su cita no se verificó ({descartados[0].motivo}); se trata como no localizado"
    else:
        nota = f"no se localizó en las {paginas} página(s) leídas"
    return {"documento": resultado.documento, "pagina": None, "cita": None, "nota": nota}


def _nombre(valores: dict[str, Valor], campo: str, defecto: str) -> str:
    valor = valores.get(campo)
    return valor.valor if valor else defecto


def cruzar(resultados: list[Resultado], paginas_por_documento: dict[str, int], fecha_corte: date, meses: int = 12) -> list[dict]:
    banderas: list[dict] = []
    horizonte = sumar_meses(fecha_corte, meses)
    contratos = [r for r in resultados if r.tipo == "contrato_renta"]

    # 1. m² de escritura contra contratos, por nave.
    rentado: dict[str, list[Valor]] = defaultdict(list)
    for contrato in contratos:
        nave, superficie = contrato.campos.get("identificador_nave"), contrato.campos.get("superficie_m2")
        if nave and superficie:
            rentado[clave_nave(nave.valor)].append(superficie)
    for escritura in (r for r in resultados if r.tipo == "escritura"):
        for renglon in escritura.renglones:
            nave, construida = renglon.get("identificador_nave"), renglon.get("superficie_construida_m2")
            if not (nave and construida) or clave_nave(nave.valor) not in rentado:
                continue
            superficies = rentado[clave_nave(nave.valor)]
            total = sum(v.numero for v in superficies)
            if abs(total - construida.numero) <= TOLERANCIA_M2 * construida.numero:
                continue
            mayor = total > construida.numero
            banderas.append(_bandera(
                "superficie_no_cuadra",
                ALTA if mayor else MEDIA,
                f"{nave.valor}: los contratos rentan {total:,.2f} m² y la escritura dice {construida.numero:,.2f} m² construidos"
                + (" (se renta más de lo que la escritura ampara)." if mayor else "."),
                [construida.evidencia(), *[v.evidencia() for v in superficies]],
            ))

    # 2. Vencimientos de contratos y 3. garantías.
    for contrato in contratos:
        inquilino = _nombre(contrato.campos, "inquilino", contrato.documento)
        identidad = [v.evidencia() for k, v in contrato.campos.items() if k in ("inquilino",)]
        vence = contrato.campos.get("fecha_vencimiento")
        if vence is None:
            banderas.append(_bandera(
                "contrato_sin_vencimiento", MEDIA,
                f"{inquilino}: no se localizó una fecha de vencimiento verificable.",
                [*identidad, _ausencia(contrato, "fecha_vencimiento", paginas_por_documento.get(contrato.documento, 0))],
            ))
        elif vence.fecha < fecha_corte:
            banderas.append(_bandera(
                "contrato_vencido", ALTA,
                f"{inquilino}: el contrato venció el {vence.fecha.isoformat()}, antes de la fecha de corte {fecha_corte.isoformat()}.",
                [vence.evidencia()],
            ))
        elif vence.fecha <= horizonte:
            banderas.append(_bandera(
                "contrato_vence_pronto", ALTA,
                f"{inquilino}: el contrato vence el {vence.fecha.isoformat()}, dentro de {meses} meses desde {fecha_corte.isoformat()}.",
                [vence.evidencia()],
            ))
        if "garantia" not in contrato.campos:
            banderas.append(_bandera(
                "contrato_sin_garantia", MEDIA,
                f"{inquilino}: no se localizó depósito en garantía, fianza ni carta de crédito.",
                [*identidad, _ausencia(contrato, "garantia", paginas_por_documento.get(contrato.documento, 0))],
            ))

    # 4. Permisos vencidos o por vencer.
    for permiso in (r for r in resultados if r.tipo == "permiso"):
        for renglon in permiso.renglones:
            vigencia = renglon.get("vigencia_hasta")
            if vigencia is None:
                continue
            nombre = _nombre(renglon, "tipo_permiso", permiso.documento)
            if vigencia.fecha < fecha_corte:
                banderas.append(_bandera(
                    "permiso_vencido", ALTA,
                    f"{nombre}: vigente solo hasta el {vigencia.fecha.isoformat()}; vencido a la fecha de corte {fecha_corte.isoformat()}.",
                    [vigencia.evidencia()],
                ))
            elif vigencia.fecha <= horizonte:
                banderas.append(_bandera(
                    "permiso_vence_pronto", MEDIA,
                    f"{nombre}: vence el {vigencia.fecha.isoformat()}, dentro de {meses} meses.",
                    [vigencia.evidencia()],
                ))

    # 5. Inquilinos de la relación de rentas sin contrato en el cuarto.
    con_contrato = {clave_inquilino(c.campos["inquilino"].valor) for c in contratos if "inquilino" in c.campos}
    for lista in (r for r in resultados if r.tipo == "lista_rentas"):
        for renglon in lista.renglones:
            inquilino = renglon.get("inquilino")
            if inquilino and clave_inquilino(inquilino.valor) not in con_contrato:
                banderas.append(_bandera(
                    "inquilino_sin_contrato", ALTA,
                    f"{inquilino.valor} aparece en la relación de rentas y no hay contrato suyo leído en el cuarto de datos.",
                    [inquilino.evidencia()],
                ))

    banderas.sort(key=lambda b: (ORDEN_SEVERIDAD[b["severidad"]], b["bandera"], b["detalle"]))
    return banderas


def transcripciones_de_suministro(resultados: list[Resultado]) -> list[dict]:
    """Lo que dicen los oficios de suministro, siempre como 'según el oficio' (D-003)."""
    salida = []
    for oficio in (r for r in resultados if r.tipo == "oficio_cfe"):
        for campo in ("emisor", "tipo_servicio", "lo_que_dice", "fecha"):
            valor = oficio.campos.get(campo)
            if valor:
                ev = valor.evidencia()
                salida.append({
                    **ev,
                    "campo": campo,
                    "texto": f"Según el oficio ({ev['documento']}, p. {ev['pagina']}): «{ev['cita']}»",
                })
    return salida
