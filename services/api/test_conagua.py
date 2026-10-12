"""El libro del SMN puede llegar como página de error con HTTP 200.

Medido el 2026-10-12 (docs/verificacion-2026-10-12.md): desde un centro de
datos, smn.conagua.gob.mx contesta 200 text/html con 730 bytes ("This page
can't be displayed"). El código lo guardaba como .xlsx y el arranque del API
tronaba con BadZipFile: el servicio entero no levantaba por una fuente.
"""
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(__file__))

from atlas.connectors import conagua

PAGINA_DE_ERROR = (
    b'<!DOCTYPE html><html><head><title>Error</title></head><body><H2>Error</H2>'
    b"This page can't be displayed. Contact support for additional information."
    b"</body></html>"
)


def _respuesta(body, status=200, content_type="text/html; charset=UTF-8"):
    return lambda url, timeout=25, headers=None, data=None: {
        "ok": True,
        "status": status,
        "url": url,
        "content_type": content_type,
        "body": body,
    }


def _libro_minimo():
    # Libro .xlsx real (ZIP + XML) con una columna de fecha y un municipio.
    shared = (
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<si><t>19039</t></si><si><t>Monterrey</t></si><si><t>Nuevo León</t></si><si><t>D1</t></si></sst>"
    )
    sheet = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        '<row r="1"><c r="G1"><v>46295</v></c></row>'
        '<row r="2"><c r="A2" t="s"><v>0</v></c><c r="D2" t="s"><v>1</v></c>'
        '<c r="E2" t="s"><v>2</v></c><c r="G2" t="s"><v>3</v></c></row>'
        "</sheetData></worksheet>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        book.writestr("xl/sharedStrings.xml", shared)
        book.writestr("xl/worksheets/sheet1.xml", sheet)
        book.writestr("relleno.txt", "x" * 2000)
    return buffer.getvalue()


def test_pagina_de_error_con_200_no_tumba_el_arranque(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_CACHE", str(tmp_path))
    monkeypatch.setattr(conagua, "fetch", _respuesta(PAGINA_DE_ERROR))
    result = conagua.load_drought()
    assert result["ok"] is False
    assert result["table"] == {}
    assert "no es un libro" in result["error"]
    # Y la página de error no se queda en caché disfrazada de libro.
    assert not (tmp_path / "MunicipiosSequia.xlsx").exists()


def test_cache_corrupta_se_vuelve_a_pedir(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_CACHE", str(tmp_path))
    (tmp_path / "MunicipiosSequia.xlsx").write_bytes(PAGINA_DE_ERROR * 20)
    monkeypatch.setattr(conagua, "fetch", _respuesta(_libro_minimo(), content_type="application/vnd.ms-excel"))
    result = conagua.load_drought()
    assert result["ok"] is True
    assert result["table"]["19039"]["category"] == "D1"


def test_libro_viejo_bueno_se_usa_marcado_como_rancio(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_CACHE", str(tmp_path))
    (tmp_path / "MunicipiosSequia.xlsx").write_bytes(_libro_minimo())
    monkeypatch.setattr(conagua, "fetch", _respuesta(PAGINA_DE_ERROR))
    result = conagua.load_drought(force=True)
    assert result.get("stale") is True
    assert result["table"]["19039"]["category"] == "D1"
    assert "no es un libro" in result["error"]


def _libro_con_cortes(filas):
    """filas: [(cvegeo, [valor por corte])]; None deja la celda vacía."""
    cortes = [46265, 46280, 46295]  # 2026-08-31, 2026-09-15, 2026-09-30
    letras = ["J", "K", "L"]
    strings = []

    def s(texto):
        strings.append(texto)
        return len(strings) - 1

    encabezado = "".join(f'<c r="{l}1"><v>{c}</v></c>' for l, c in zip(letras, cortes))
    cuerpo = []
    for n, (clave, valores) in enumerate(filas, start=2):
        celdas = f'<c r="A{n}" t="s"><v>{s(clave)}</v></c>'
        for l, valor in zip(letras, valores):
            if valor is None:
                celdas += f'<c r="{l}{n}" s="3"/>'
            else:
                celdas += f'<c r="{l}{n}" t="s"><v>{s(valor)}</v></c>'
        cuerpo.append(f'<row r="{n}">{celdas}</row>')
    shared = (
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + "".join(f"<si><t>{t}</t></si>" for t in strings)
        + "</sst>"
    )
    sheet = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        f'<row r="1">{encabezado}</row>' + "".join(cuerpo) + "</sheetData></worksheet>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        book.writestr("xl/sharedStrings.xml", shared)
        book.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


def test_celda_vacia_en_el_ultimo_corte_es_sin_sequia(tmp_path):
    # Medido 2026-10-12: Celaya (11007) tenía vacío el corte 2026-09-30 y el
    # código reportaba el D0 de 2025-05-31. La hoja NOTAS del SMN da "Sin
    # Sequía" sin clave: vacío es sin sequía, no "sin dato".
    libro = tmp_path / "MunicipiosSequia.xlsx"
    libro.write_bytes(_libro_con_cortes([
        ("11007", ["D0", None, None]),
        ("19006", [None, None, "D0"]),
        ("05027", ["D1", "D0", None]),
    ]))
    tabla = conagua._load_rows(libro)["table"]
    assert tabla["11007"]["category"] == "NONE"
    assert tabla["11007"]["as_of"] == "2026-09-30"
    assert tabla["19006"]["category"] == "D0"
    assert tabla["05027"]["category"] == "NONE"
    # Todas las filas llevan la fecha del corte, ninguna una fecha vieja.
    assert {fila["as_of"] for fila in tabla.values()} == {"2026-09-30"}
