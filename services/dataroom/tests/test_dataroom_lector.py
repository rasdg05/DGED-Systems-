"""El lector del cuarto de datos, sin red ni clave (cliente grabado).

Invariantes que cuidan estos tests:
- Todo valor que sale trae documento, página y cita, y la cita está literal
  (salvo espacios) en el texto de ESA página; si no, se descarta.
- Los cruces sobre la muestra ficticia encuentran exactamente los errores plantados.
- Un PDF sin texto se reporta "requiere OCR" y no se le manda al modelo.
- Sin ANTHROPIC_API_KEY el CLI se detiene con un mensaje claro.
- Nunca se afirma capacidad eléctrica ni MW fuera de "según el oficio" (D-003).
"""
from __future__ import annotations

import csv
import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest
from dataroom import cruces, extraccion, leer
from dataroom.esquemas import NUMERO, TEXTO, TIPOS, TRANSCRIPCION, Campo, esquema_extraccion
from dataroom.grabado import ClienteGrabado
from dataroom.textos import Documento, cita_literal, leer_carpeta, leer_pdf

RAIZ = Path(__file__).resolve().parent.parent
MUESTRA = RAIZ / "muestra"
CUARTO = MUESTRA / "cuarto"
GRABADAS = MUESTRA / "respuestas_grabadas.json"
CORTE = date(2026, 10, 13)


def _generador():
    spec = importlib.util.spec_from_file_location("generar_muestra", MUESTRA / "generar_muestra.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _grabadas() -> dict:
    return json.loads(GRABADAS.read_text(encoding="utf-8"))


def _correr(carpeta: Path, destino: Path, client=None, corte: date = CORTE, meses: int = 12) -> dict:
    client = client or ClienteGrabado(_grabadas())
    return leer.correr(carpeta, destino, client, extraccion.DEFAULT_MODEL, corte, meses, "grabado")


@pytest.fixture(scope="module")
def muestra(tmp_path_factory):
    destino = tmp_path_factory.mktemp("salida")
    return destino, _correr(CUARTO, destino)


def _doc(*paginas: str) -> Documento:
    return Documento(nombre="d.pdf", ruta=Path("d.pdf"), paginas=list(paginas))


def _v(valor, pagina, cita):
    return {"valor": valor, "pagina": pagina, "cita": cita}


# --- la cita literal ------------------------------------------------------------

def test_cita_literal_ignora_solo_los_espacios():
    pagina = "La Nave 2 tiene una superficie\nrentable de 9,200 m²   de construcción."
    assert cita_literal("superficie rentable de 9,200 m² de construcción", pagina)
    assert not cita_literal("superficie rentable de 9200 m² de construcción", pagina)
    assert not cita_literal("Superficie rentable", pagina)  # mayúscula distinta: no es literal
    assert not cita_literal("   ", pagina)


def test_valor_con_cita_parafraseada_se_descarta():
    doc = _doc("SEXTA. El Arrendatario entrega un depósito en garantía equivalente a dos meses de renta.")
    campo = Campo("garantia", TEXTO, "")
    valor, descartado = extraccion.verificar(doc, "contrato_renta", campo, _v("Dos meses", 1, "El inquilino deja dos meses de depósito."))
    assert valor is None and descartado and "literal" in descartado.motivo
    valor, descartado = extraccion.verificar(doc, "contrato_renta", campo, _v("Dos meses", 1, "depósito en garantía equivalente a dos meses"))
    assert valor and descartado is None
    assert valor.evidencia() == {"documento": "d.pdf", "pagina": 1, "cita": "depósito en garantía equivalente a dos meses"}


def test_cita_de_otra_pagina_se_descarta():
    doc = _doc("Página uno sin nada relevante aquí.", "vence el 31 de marzo de 2027")
    campo = TIPOS["contrato_renta"].campos[8]
    assert campo.nombre == "fecha_vencimiento"
    assert extraccion.verificar(doc, "contrato_renta", campo, _v("2027-03-31", 1, "vence el 31 de marzo de 2027"))[1]
    assert extraccion.verificar(doc, "contrato_renta", campo, _v("2027-03-31", 3, "vence el 31 de marzo de 2027"))[1]
    assert extraccion.verificar(doc, "contrato_renta", campo, _v("2027-03-31", 2, "vence el 31 de marzo de 2027"))[0]


def test_cifra_y_fecha_tienen_que_estar_en_su_cita():
    doc = _doc("La Nave 2 tiene una superficie rentable de 9,200 m². Vence el 30 de junio de 2033.")
    m2 = Campo("superficie_m2", NUMERO, "")
    vence = TIPOS["contrato_renta"].campos[8]
    assert extraccion.verificar(doc, "contrato_renta", m2, _v("9200", 1, "superficie rentable de 9,200 m²"))[0].numero == 9200
    assert extraccion.verificar(doc, "contrato_renta", m2, _v("9500", 1, "superficie rentable de 9,200 m²"))[1]
    assert extraccion.verificar(doc, "contrato_renta", vence, _v("2033-06-30", 1, "Vence el 30 de junio de 2033."))[0]
    assert extraccion.verificar(doc, "contrato_renta", vence, _v("2033-07-30", 1, "Vence el 30 de junio de 2033."))[1]
    assert extraccion.verificar(doc, "contrato_renta", vence, _v("30/06/2033", 1, "Vence el 30 de junio de 2033."))[1]


def test_transcripcion_no_admite_parafrasis():
    doc = _doc("la otra Inquilino Ficticio Beta, S.A. de C.V. (en lo sucesivo, el Arrendatario)")
    campo = Campo("inquilino", TRANSCRIPCION, "")
    cita = "la otra Inquilino Ficticio Beta, S.A. de C.V."
    assert extraccion.verificar(doc, "contrato_renta", campo, _v("Inquilino Ficticio Beta, S.A. de C.V.", 1, cita))[0]
    assert extraccion.verificar(doc, "contrato_renta", campo, _v("Beta Ficticio SA", 1, cita))[1]


def test_toda_cita_que_sale_esta_literal_en_su_pagina(muestra):
    """La invariante, sobre la salida entera de la muestra: ninguna cita se escapa."""
    _destino, hallazgos = muestra
    textos = {d.nombre: d for d in leer_carpeta(CUARTO).documentos}
    evidencias = [ev for b in hallazgos["banderas"] for ev in b["evidencia"] if ev.get("cita")]
    evidencias += [campo for fila in hallazgos["rent_roll"] for campo in fila["campos"].values()]
    evidencias += hallazgos["transcripciones_suministro"]
    assert len(evidencias) > 30
    for ev in evidencias:
        assert ev["documento"] and ev["pagina"] >= 1 and ev["cita"], ev
        assert cita_literal(ev["cita"], textos[ev["documento"]].texto(ev["pagina"])), ev


def test_la_cita_parafraseada_de_la_muestra_se_descarta(muestra):
    destino, hallazgos = muestra
    assert [(d["documento"], d["campo"]) for d in hallazgos["descartados"]] == [("contrato_nave_1.pdf", "seguro")]
    with (destino / "rent_roll.csv").open(encoding="utf-8") as archivo:
        filas = {f["documento"]: f for f in csv.DictReader(archivo)}
    assert filas["contrato_nave_1.pdf"]["seguro"] == ""
    assert filas["contrato_nave_1.pdf"]["superficie_m2"] == "12000"
    assert filas["contrato_nave_2.pdf"]["fecha_vencimiento"] == "2033-06-30"
    assert "Lo que no se revisó" in (destino / "memo.md").read_text(encoding="utf-8")


# --- los cruces sobre la muestra ------------------------------------------------

PLANTADOS = {
    ("superficie_no_cuadra", "alta", "superficie_no_cuadra:escritura_parque.pdf"),
    ("contrato_vence_pronto", "alta", "contrato_vence_pronto:contrato_nave_1.pdf"),
    ("contrato_sin_garantia", "media", "contrato_sin_garantia:contrato_nave_2.pdf"),
    ("permiso_vencido", "alta", "permiso_vencido:permisos.pdf"),
    ("inquilino_sin_contrato", "alta", "inquilino_sin_contrato:relacion_rentas.pdf"),
}


def _firma(bandera: dict) -> tuple[str, str, str]:
    return bandera["bandera"], bandera["severidad"], f"{bandera['bandera']}:{bandera['evidencia'][0]['documento']}"


def test_los_cruces_encuentran_exactamente_los_errores_plantados(muestra):
    _destino, hallazgos = muestra
    assert {_firma(b) for b in hallazgos["banderas"]} == PLANTADOS
    assert len(hallazgos["banderas"]) == len(PLANTADOS)
    por_codigo = {b["bandera"]: b for b in hallazgos["banderas"]}
    assert "9,200.00" in por_codigo["superficie_no_cuadra"]["detalle"] and "8,500.00" in por_codigo["superficie_no_cuadra"]["detalle"]
    assert "Gamma" in por_codigo["inquilino_sin_contrato"]["detalle"]
    assert "2025-06-30" in por_codigo["permiso_vencido"]["detalle"]
    assert "Beta" in por_codigo["contrato_sin_garantia"]["detalle"]


def test_el_horizonte_decide_que_vence_pronto(tmp_path):
    lejos = _correr(CUARTO, tmp_path / "a", corte=date(2025, 1, 1), meses=12)
    codigos = {b["bandera"] for b in lejos["banderas"]}
    assert "contrato_vence_pronto" not in codigos and "permiso_vencido" not in codigos
    assert "permiso_vence_pronto" in codigos  # la licencia vence 2025-06-30, dentro de 12 meses
    tarde = _correr(CUARTO, tmp_path / "b", corte=date(2027, 4, 1), meses=12)
    assert "contrato_vencido" in {b["bandera"] for b in tarde["banderas"]}


def test_una_garantia_descartada_no_se_afirma_inexistente(tmp_path):
    grabadas = _grabadas()
    grabadas["contrato_nave_1.pdf"]["extraccion"]["campos"]["garantia"] = _v("Dos meses", 2, "Depósito de dos meses, según el inquilino.")
    hallazgos = _correr(CUARTO, tmp_path, ClienteGrabado(grabadas))
    sin_garantia = [b for b in hallazgos["banderas"] if b["bandera"] == "contrato_sin_garantia" and "Alfa" in b["detalle"]]
    assert sin_garantia
    notas = [ev.get("nota", "") for ev in sin_garantia[0]["evidencia"]]
    assert any("no se verificó" in nota for nota in notas)


def test_claves_de_nave_y_de_inquilino():
    assert cruces.clave_nave("NAVE  2") == cruces.clave_nave("Nave 2") == cruces.clave_nave("nave No. 2") == "nave 2"
    assert cruces.clave_inquilino("Inquilino Ficticio Beta, S.A. de C.V.") == cruces.clave_inquilino("INQUILINO FICTICIO BETA SA DE CV")
    assert cruces.clave_inquilino("Inquilino Ficticio Beta") != cruces.clave_inquilino("Inquilino Ficticio Gamma")
    assert cruces.sumar_meses(date(2026, 8, 31), 6) == date(2027, 2, 28)


# --- PDF sin texto, sin clave, rechazo ---------------------------------------------

def test_pdf_sin_texto_requiere_ocr_y_no_va_al_modelo(tmp_path):
    carpeta = tmp_path / "cuarto"
    carpeta.mkdir()
    (carpeta / "anexo_escaneado.pdf").write_bytes(_generador().pdf_escaneado())
    (carpeta / "notas.txt").write_text("no es pdf", encoding="utf-8")
    documento = leer_pdf(carpeta / "anexo_escaneado.pdf")
    assert documento.requiere_ocr and not documento.legible
    cliente = ClienteGrabado({"anexo_escaneado.pdf": {"tipo": "contrato_renta", "extraccion": {}}})
    hallazgos = _correr(carpeta, tmp_path / "salida", cliente)
    assert cliente.llamadas == []
    motivos = {n["documento"]: n["motivo"] for n in hallazgos["no_revisado"]}
    assert "requiere OCR" in motivos["anexo_escaneado.pdf"]
    assert "no soportado" in motivos["notas.txt"]
    assert hallazgos["banderas"] == [] and hallazgos["rent_roll"] == []
    memo = (tmp_path / "salida" / "memo.md").read_text(encoding="utf-8")
    assert "anexo_escaneado.pdf: requiere OCR" in memo


def test_pdf_danado_se_reporta(tmp_path):
    (tmp_path / "roto.pdf").write_bytes(b"esto no es un pdf")
    documento = leer_pdf(tmp_path / "roto.pdf")
    assert documento.error and not documento.legible


def test_sin_clave_el_cli_duerme_con_mensaje_claro(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    codigo = leer.main([str(CUARTO), "--salida", str(tmp_path / "salida")])
    assert codigo == leer.SIN_CLAVE
    error = capsys.readouterr().err
    assert "ANTHROPIC_API_KEY" in error and "dormido" in error
    assert not (tmp_path / "salida").exists()


def test_cli_con_respuestas_grabadas(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    codigo = leer.main([str(CUARTO), "--salida", str(tmp_path), "--fecha-corte", "2026-10-13", "--respuestas-grabadas", str(GRABADAS)])
    assert codigo == 0
    assert "5 banderas (4 altas)" in capsys.readouterr().out
    assert {p.name for p in tmp_path.iterdir()} == {"rent_roll.csv", "hallazgos.json", "memo.md"}


def test_un_rechazo_del_modelo_deja_el_documento_sin_revisar(tmp_path):
    hallazgos = _correr(CUARTO, tmp_path, ClienteGrabado(_grabadas(), stop_reason="refusal"))
    assert hallazgos["banderas"] == []
    assert len(hallazgos["no_revisado"]) == 6
    assert all("declinó" in n["motivo"] for n in hallazgos["no_revisado"])


def test_la_llamada_usa_el_modelo_fijo_y_salida_estructurada():
    cliente = ClienteGrabado(_grabadas())
    documento = leer_pdf(CUARTO / "contrato_nave_1.pdf")
    resultado = extraccion.leer_documento(cliente, extraccion.DEFAULT_MODEL, documento)
    assert resultado.tipo == "contrato_renta"
    assert extraccion.DEFAULT_MODEL == "claude-opus-5-5"
    clasificacion, extraccion_llamada = cliente.llamadas
    for llamada in (clasificacion, extraccion_llamada):
        assert llamada["model"] == "claude-opus-5-5"
        assert llamada["output_config"]["format"]["type"] == "json_schema"
        assert llamada["fallbacks"] == "default"
        assert '<documento nombre="contrato_nave_1.pdf">' in llamada["messages"][0]["content"]
    assert extraccion_llamada["output_config"]["format"]["schema"] == esquema_extraccion(TIPOS["contrato_renta"])


# --- D-003: nunca MW como hecho -----------------------------------------------------

def test_ningun_esquema_tiene_campo_de_capacidad():
    prohibidas = ("mw", "kw", "kva", "capacidad", "carga", "megawatt", "potencia")
    for tipo in TIPOS.values():
        for campo in (*tipo.campos, *tipo.renglones):
            assert not any(p in campo.nombre.lower() for p in prohibidas), (tipo.nombre, campo.nombre)


def test_capacidad_fuera_de_un_oficio_se_retira(tmp_path):
    carpeta = tmp_path / "cuarto"
    carpeta.mkdir()
    texto = "La Nave 9 cuenta con 2.5 MW disponibles para el arrendatario."
    (carpeta / "contrato.pdf").write_bytes(_generador()._pdf([["CONTRATO DE ARRENDAMIENTO", texto]]))
    grabadas = {"contrato.pdf": {"tipo": "contrato_renta", "extraccion": {"campos": {
        "identificador_nave": _v("Nave 9", 1, "La Nave 9 cuenta con 2.5 MW disponibles"),
        "ubicacion": _v("Nave con 2.5 MW disponibles", 1, texto),
    }}}}
    hallazgos = _correr(carpeta, tmp_path / "salida", ClienteGrabado(grabadas))
    assert len(hallazgos["descartados"]) == 2
    assert all("D-003" in d["motivo"] for d in hallazgos["descartados"])
    assert all(d["valor"] == "[retirado]" and d["cita"] == "[retirado]" for d in hallazgos["descartados"])
    for archivo in ("memo.md", "hallazgos.json", "rent_roll.csv"):
        assert not extraccion.AFIRMACION_MW.search((tmp_path / "salida" / archivo).read_text(encoding="utf-8")), archivo


def test_lo_del_oficio_solo_sale_como_segun_el_oficio(muestra):
    destino, hallazgos = muestra
    transcripciones = hallazgos["transcripciones_suministro"]
    assert any("1,500 kW" in t["cita"] for t in transcripciones)
    assert all(t["texto"].startswith("Según el oficio (") for t in transcripciones)
    for linea in (destino / "memo.md").read_text(encoding="utf-8").splitlines():
        if extraccion.AFIRMACION_MW.search(linea):
            assert linea.startswith("- Según el oficio ("), linea
    sin_transcripciones = {k: v for k, v in hallazgos.items() if k != "transcripciones_suministro"}
    assert not extraccion.AFIRMACION_MW.search(json.dumps(sin_transcripciones, ensure_ascii=False))
    assert not extraccion.AFIRMACION_MW.search((destino / "rent_roll.csv").read_text(encoding="utf-8"))


# --- la muestra es ficticia y reproducible ----------------------------------------

def test_la_muestra_es_ficticia_marcada_y_reproducible(tmp_path):
    generador = _generador()
    actuales = {d.nombre: d for d in leer_carpeta(CUARTO).documentos}
    assert 4 <= len(actuales) <= 6
    for documento in actuales.values():
        for numero, texto in enumerate(documento.paginas, start=1):
            assert generador.MARCA in texto, (documento.nombre, numero)
    generador.generar(tmp_path)
    regenerados = {d.nombre: d.paginas for d in leer_carpeta(tmp_path).documentos}
    assert regenerados == {nombre: d.paginas for nombre, d in actuales.items()}
