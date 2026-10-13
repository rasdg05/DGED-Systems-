"""Texto por página con pypdf, y la comparación literal de citas.

Un PDF sin capa de texto (un escaneo) NO se le pasa al modelo: se reporta como
"requiere OCR". Leerlo sería pedirle al modelo que adivine.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Una página con menos caracteres visibles que esto se trata como sin texto: un
# escaneo suele traer, a lo más, un número de página o basura de la capa oculta.
MIN_CARACTERES = 20

ESPACIOS = re.compile(r"\s+")


def normalizar(texto: str) -> str:
    """Colapsa cualquier corrida de espacios (incluidos saltos y NBSP) en uno."""
    return ESPACIOS.sub(" ", texto or "").strip()


def cita_literal(cita: str, texto_pagina: str) -> bool:
    """¿La cita aparece tal cual en la página, salvo por los espacios?"""
    cita_n = normalizar(cita)
    return bool(cita_n) and cita_n in normalizar(texto_pagina)


@dataclass
class Documento:
    nombre: str
    ruta: Path
    paginas: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def paginas_sin_texto(self) -> list[int]:
        return [i + 1 for i, texto in enumerate(self.paginas) if len(ESPACIOS.sub("", texto or "")) < MIN_CARACTERES]

    @property
    def requiere_ocr(self) -> bool:
        return self.error is None and bool(self.paginas) and len(self.paginas_sin_texto) == len(self.paginas)

    @property
    def legible(self) -> bool:
        return self.error is None and bool(self.paginas) and not self.requiere_ocr

    def texto(self, pagina: int) -> str:
        if 1 <= pagina <= len(self.paginas):
            return self.paginas[pagina - 1]
        return ""


def leer_pdf(ruta: Path, nombre: str | None = None) -> Documento:
    from pypdf import PdfReader

    documento = Documento(nombre=nombre or ruta.name, ruta=ruta)
    try:
        lector = PdfReader(str(ruta))
        if lector.is_encrypted:
            documento.error = "PDF cifrado: no se puede leer sin la contraseña"
            return documento
        documento.paginas = [(pagina.extract_text() or "") for pagina in lector.pages]
        if not documento.paginas:
            documento.error = "PDF sin páginas"
    except Exception as error:  # PDF dañado o que no es PDF: se reporta, no se adivina
        documento.error = f"no se pudo leer el PDF ({type(error).__name__})"
    return documento


@dataclass
class Carpeta:
    documentos: list[Documento]
    no_soportados: list[str]


def leer_carpeta(carpeta: Path) -> Carpeta:
    documentos, no_soportados = [], []
    for ruta in sorted(p for p in carpeta.rglob("*") if p.is_file()):
        relativo = ruta.relative_to(carpeta).as_posix()
        if any(parte.startswith(".") for parte in ruta.relative_to(carpeta).parts):
            continue
        if ruta.suffix.lower() == ".pdf":
            documentos.append(leer_pdf(ruta, relativo))
        else:
            no_soportados.append(relativo)
    return Carpeta(documentos=documentos, no_soportados=no_soportados)
