"""Genera el cuarto de datos de MUESTRA: seis PDF ficticios con errores plantados.

Nada aquí es de una persona o empresa real. Cada página lleva la marca
"DOCUMENTO FICTICIO — MUESTRA DGED" arriba y abajo.

Errores plantados (los cruces deben encontrar exactamente estos):

- P1  m²: el contrato de la Nave 2 renta 9,200 m²; la escritura dice 8,500 m².
- P2  vencimiento: el contrato de la Nave 1 vence el 31 de marzo de 2027
      (dentro de 12 meses desde la fecha de corte de los tests, 2026-10-13).
- P3  garantía: el contrato de la Nave 2 no pacta depósito ni fianza.
- P4  permiso vencido: la licencia de uso de suelo venció el 30 de junio de 2025.
- P5  inquilino sin contrato: la relación de rentas trae a "Inquilino Ficticio
      Gamma" en la Nave 3 y en el cuarto no hay contrato suyo.

El oficio de suministro dice una carga en kW: eso se TRANSCRIBE "según el
oficio", nunca se vuelve un hecho (D-003).

Uso:  python services/dataroom/muestra/generar_muestra.py [carpeta_destino]
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

MARCA = "DOCUMENTO FICTICIO — MUESTRA DGED"
DESTINO = Path(__file__).resolve().parent / "cuarto"

CONTRATO_NAVE_1 = [
    [
        "CONTRATO DE ARRENDAMIENTO DE NAVE INDUSTRIAL",
        "Que celebran por una parte Arrendadora Muestra Uno, S.A. de C.V. (en lo sucesivo, el Arrendador) "
        "y por la otra Inquilino Ficticio Alfa, S.A. de C.V. (en lo sucesivo, el Arrendatario).",
        "PRIMERA. Objeto. El Arrendador da en arrendamiento al Arrendatario la Nave 1 del Parque Industrial "
        "Ficticio Uno, ubicada en Avenida de la Muestra 100, Municipio de Ejemplo, Estado de Muestra.",
        "SEGUNDA. Superficie. La Nave 1 tiene una superficie rentable de 12,000 m² de construcción.",
        "TERCERA. Renta. El Arrendatario pagará una renta mensual de USD 66,000.00 (sesenta y seis mil "
        "dólares de los Estados Unidos de América) más IVA.",
        "CUARTA. Vigencia. El arrendamiento inicia el 1 de abril de 2022 y vence el 31 de marzo de 2027.",
    ],
    [
        "QUINTA. Incrementos. La renta se incrementará en cada aniversario del contrato en 3% anual.",
        "SEXTA. Depósito en garantía. El Arrendatario entrega un depósito en garantía equivalente a dos meses de renta.",
        "SÉPTIMA. Mantenimiento. El mantenimiento de la nave y de las áreas comunes corre por cuenta del Arrendatario.",
        "OCTAVA. Impuesto predial. El impuesto predial es a cargo del Arrendador.",
        "NOVENA. Seguros. El Arrendatario contratará el seguro de contenidos y de responsabilidad civil; "
        "el Arrendador asegura el edificio.",
        "DÉCIMA. Terminación anticipada. El Arrendatario podrá terminar anticipadamente el contrato pagando "
        "una pena equivalente a seis meses de renta.",
    ],
]

CONTRATO_NAVE_2 = [
    [
        "CONTRATO DE ARRENDAMIENTO DE NAVE INDUSTRIAL",
        "Que celebran por una parte Arrendadora Muestra Uno, S.A. de C.V. (en lo sucesivo, el Arrendador) "
        "y por la otra Inquilino Ficticio Beta, S.A. de C.V. (en lo sucesivo, el Arrendatario).",
        "PRIMERA. Objeto. El Arrendador da en arrendamiento al Arrendatario la Nave 2 del Parque Industrial "
        "Ficticio Uno, ubicada en Avenida de la Muestra 100, Municipio de Ejemplo, Estado de Muestra.",
        "SEGUNDA. Superficie. La Nave 2 tiene una superficie rentable de 9,200 m² de construcción.",
        "TERCERA. Renta. El Arrendatario pagará una renta mensual de MXN 780,000.00 (setecientos ochenta mil "
        "pesos mexicanos) más IVA.",
        "CUARTA. Vigencia. El arrendamiento inicia el 1 de julio de 2023 y vence el 30 de junio de 2033.",
    ],
    [
        "QUINTA. Incrementos. La renta se actualizará cada año conforme al Índice Nacional de Precios al Consumidor.",
        "SEXTA. Mantenimiento. El mantenimiento de la nave corre por cuenta del Arrendatario.",
        "SÉPTIMA. Impuesto predial. El impuesto predial es a cargo del Arrendador.",
        "OCTAVA. Seguros. El Arrendador asegura el edificio y el Arrendatario asegura sus contenidos.",
        "NOVENA. Terminación anticipada. Ninguna de las partes podrá terminar anticipadamente el contrato "
        "durante los primeros cinco años.",
    ],
]

ESCRITURA = [
    [
        "ESCRITURA PÚBLICA NÚMERO CERO (FICTICIA)",
        "Ante el Notario Público Ficticio Número Cero del Estado de Muestra comparece Arrendadora Muestra Uno, "
        "S.A. de C.V., propietaria del inmueble denominado Parque Industrial Ficticio Uno.",
        "El terreno tiene una superficie de 45,000 m², ubicado en Avenida de la Muestra 100, Municipio de Ejemplo.",
        "Sobre el terreno se encuentran construidas las siguientes naves:",
        "Nave 1 con una superficie construida de 12,000 m².",
        "Nave 2 con una superficie construida de 8,500 m².",
        "Nave 3 con una superficie construida de 6,000 m².",
        "Según el certificado de libertad de gravámenes ficticio que se agrega al apéndice, el inmueble se "
        "encuentra libre de gravámenes.",
    ],
]

PERMISOS = [
    [
        "LICENCIA DE USO DE SUELO",
        "Autoridad: Dirección de Desarrollo Urbano del Municipio de Ejemplo.",
        "Titular: Arrendadora Muestra Uno, S.A. de C.V.",
        "Se autoriza el uso de suelo industrial para las Naves 1, 2 y 3 del Parque Industrial Ficticio Uno.",
        "Fecha de emisión: 15 de junio de 2020.",
        "Esta licencia es vigente hasta el 30 de junio de 2025.",
    ],
    [
        "DICTAMEN DE PROTECCIÓN CIVIL",
        "Autoridad: Coordinación de Protección Civil del Estado de Muestra.",
        "Titular: Arrendadora Muestra Uno, S.A. de C.V.",
        "Se dictamina favorablemente el programa interno para las Naves 1, 2 y 3 del Parque Industrial Ficticio Uno.",
        "Fecha de emisión: 1 de junio de 2025.",
        "Este dictamen es vigente hasta el 31 de mayo de 2028.",
    ],
]

RELACION_RENTAS = [
    [
        "RELACIÓN DE RENTAS ENTREGADA POR EL VENDEDOR",
        "Parque Industrial Ficticio Uno. Corte al 30 de septiembre de 2026.",
        "Inquilino Ficticio Alfa, S.A. de C.V. - Nave 1 - 12,000 m² - USD 66,000.00 mensuales",
        "Inquilino Ficticio Beta, S.A. de C.V. - Nave 2 - 9,200 m² - MXN 780,000.00 mensuales",
        "Inquilino Ficticio Gamma, S.A. de C.V. - Nave 3 - 6,000 m² - MXN 510,000.00 mensuales",
    ],
]

OFICIO_SUMINISTRO = [
    [
        "OFICIO DE FACTIBILIDAD DE SUMINISTRO (FICTICIO)",
        "Emisor: Suministrador Eléctrico Ficticio, en el lugar de la empresa suministradora.",
        "Asunto: Factibilidad de servicio para el Parque Industrial Ficticio Uno.",
        "Se informa que el servicio solicitado se atenderá en media tensión, tarifa GDMTH.",
        "La carga solicitada de 1,500 kW queda sujeta a la ejecución de obras de refuerzo en la red por cuenta "
        "del solicitante.",
        "Fecha: 3 de febrero de 2026.",
    ],
]

DOCUMENTOS = {
    "contrato_nave_1.pdf": CONTRATO_NAVE_1,
    "contrato_nave_2.pdf": CONTRATO_NAVE_2,
    "escritura_parque.pdf": ESCRITURA,
    "permisos.pdf": PERMISOS,
    "relacion_rentas.pdf": RELACION_RENTAS,
    "oficio_suministro.pdf": OFICIO_SUMINISTRO,
}


def _pdf(paginas: list[list[str]]) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    # invariant: sin fecha ni id aleatorio, el mismo texto da el mismo archivo.
    lienzo = canvas.Canvas(buffer, pagesize=letter, invariant=1)
    ancho, alto = letter
    for parrafos in paginas:
        lienzo.setFont("Helvetica-Bold", 9)
        lienzo.drawCentredString(ancho / 2, alto - 40, MARCA)
        lienzo.drawCentredString(ancho / 2, 30, MARCA)
        y = alto - 80
        for i, parrafo in enumerate(parrafos):
            fuente = "Helvetica-Bold" if i == 0 and parrafo.isupper() else "Helvetica"
            lienzo.setFont(fuente, 10)
            for linea in simpleSplit(parrafo, fuente, 10, ancho - 144):
                lienzo.drawString(72, y, linea)
                y -= 14
            y -= 8
        lienzo.showPage()
    lienzo.save()
    return buffer.getvalue()


def pdf_escaneado() -> bytes:
    """Un PDF de una página que solo trae una imagen: como un escaneo sin OCR."""
    from PIL import Image, ImageDraw
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    imagen = Image.new("L", (850, 1100), 255)
    dibujo = ImageDraw.Draw(imagen)
    dibujo.text((60, 40), "DOCUMENTO FICTICIO - MUESTRA DGED (escaneo)", fill=0)
    for y in range(120, 1000, 30):
        dibujo.line((60, y, 790, y), fill=120, width=2)
    buffer = io.BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=letter, invariant=1)
    lienzo.drawImage(ImageReader(imagen), 0, 0, width=letter[0], height=letter[1])
    lienzo.showPage()
    lienzo.save()
    return buffer.getvalue()


def generar(destino: Path = DESTINO) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    escritos = []
    for nombre, paginas in DOCUMENTOS.items():
        ruta = destino / nombre
        ruta.write_bytes(_pdf(paginas))
        escritos.append(ruta)
    return escritos


if __name__ == "__main__":
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else DESTINO
    for ruta in generar(carpeta):
        print(ruta)
