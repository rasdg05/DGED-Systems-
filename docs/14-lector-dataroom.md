# Lector del cuarto de datos (MVP)

El primer entregable de la revisión de adquisiciones (D-013,
`docs/11-revision-adquisiciones.md`): leer el cuarto de datos de una nave o un
portafolio y devolver rent roll, banderas rojas y lo que no se revisó, **cada
dato con documento, página y cita literal**. Vive aislado en
`services/dataroom/`; no toca `services/api/`.

## Cómo se corre

```bash
pip install -r services/dataroom/requirements.txt
cd services/dataroom
export ANTHROPIC_API_KEY=...            # sin ella, el lector duerme
python -m dataroom.leer /ruta/al/cuarto --salida /ruta/salida \
    --fecha-corte 2026-10-13 --meses 12
```

Sin `ANTHROPIC_API_KEY` sale con código 2 y un mensaje claro, sin leer nada.
Para la muestra ficticia, sin clave ni red:

```bash
python -m dataroom.leer muestra/cuarto --salida /tmp/muestra \
    --fecha-corte 2026-10-13 --respuestas-grabadas muestra/respuestas_grabadas.json
```

Salida: `rent_roll.csv` (un renglón por contrato, cada campo con su página),
`hallazgos.json` (banderas con severidad y evidencia, rent roll con citas,
transcripciones de oficios de suministro, valores descartados y lo no revisado)
y `memo.md` (banderas rojas priorizadas y **Lo que no se revisó**).

## Cómo funciona

1. **Texto por página con pypdf** (`dataroom/textos.py`). Una página con menos
   de 20 caracteres visibles cuenta como sin texto. Un PDF sin texto en ninguna
   página es un escaneo: se reporta **"requiere OCR"** y **no se le manda al
   modelo**. Un PDF cifrado o dañado se reporta con su motivo.
2. **Clasificación y extracción con Claude** (`dataroom/extraccion.py`):
   `claude-opus-5-5` (cambiable con `DATAROOM_MODEL`), salida estructurada con
   `output_config.format` (JSON Schema fijo por tipo, `dataroom/esquemas.py`),
   esfuerzo `high`, respaldo del servidor ante un rechazo (`fallbacks:
   "default"`). El texto del documento va entre etiquetas como material, no
   como instrucciones. Tipos y campos:
   - **contrato de renta**: inquilino, arrendador, nave, ubicación, m², renta
     mensual y moneda, inicio, vencimiento, incrementos, garantía, quién paga
     mantenimiento, predial y seguro, terminación anticipada;
   - **escritura**: propietario, ubicación, superficie de terreno, gravámenes
     mencionados y, por nave, superficie construida;
   - **permiso / licencia / dictamen**: titular y, por permiso, tipo, alcance,
     autoridad, emisión y vigencia;
   - **oficio de suministro (CFE)**: emisor, tipo de servicio, lo que dice el
     papel y fecha, **todo como transcripción**;
   - **relación de rentas** del vendedor: inquilino, nave, m², renta, moneda.
   Lo que no es de ningún tipo queda como "tipo sin esquema" en lo no revisado.
3. **Candados** (en código, después del modelo). Cada valor trae `valor`,
   `pagina` y `cita`, y se **descarta con su motivo** si: la página no existe;
   la cita no aparece literal en el texto de esa página (normalizando solo
   espacios: mayúsculas, acentos y signos cuentan); un campo de transcripción
   (nombres, naves, oficios) no está dentro de su cita; una cifra no está en su
   cita; una fecha no viene AAAA-MM-DD o no se lee en su cita; o, fuera de un
   oficio de suministro, el valor o su cita afirma capacidad eléctrica o MW.
   Un descartado no entra a ningún cruce y se lista en el memo.
4. **Cruces deterministas** (`dataroom/cruces.py`, sin modelo):
   - m² de escritura contra la suma de contratos de la misma nave (tolerancia
     1 %): rentar más de lo construido es **alta**, menos es **media**;
   - contratos vencidos o que vencen dentro de N meses (alta) y contratos sin
     vencimiento verificable (media);
   - contratos sin garantía localizada (media). Si el modelo propuso una
     garantía y su cita no se verificó, la evidencia lo dice: no se afirma que
     no exista;
   - permisos vencidos (alta) o por vencer dentro de N meses (media);
   - inquilinos de la relación de rentas sin contrato en el cuarto (alta),
     comparando la razón social sin acentos, signos ni sufijo societario.
5. **Oficios de suministro** salen siempre como `Según el oficio (doc, p. N):
   «cita»`, en su propia sección. Nunca como hecho, nunca en el rent roll, nunca
   en una bandera (D-003).

## Invariantes (con su test)

Todas en `services/dataroom/tests/test_dataroom_lector.py`, sin red ni clave
(cliente grabado, `dataroom/grabado.py`):

| Invariante | Test |
|---|---|
| Todo valor que sale trae documento, página y cita, y la cita está literal en el texto de esa página | `test_toda_cita_que_sale_esta_literal_en_su_pagina`, `test_valor_con_cita_parafraseada_se_descarta`, `test_cita_de_otra_pagina_se_descarta` |
| Cifras, fechas y transcripciones tienen que estar en su cita | `test_cifra_y_fecha_tienen_que_estar_en_su_cita`, `test_transcripcion_no_admite_parafrasis` |
| Los cruces sobre la muestra encuentran exactamente los errores plantados | `test_los_cruces_encuentran_exactamente_los_errores_plantados` |
| PDF sin texto → "requiere OCR", sin llamar al modelo | `test_pdf_sin_texto_requiere_ocr_y_no_va_al_modelo` |
| Sin `ANTHROPIC_API_KEY`, el CLI duerme con mensaje claro y no escribe nada | `test_sin_clave_el_cli_duerme_con_mensaje_claro` |
| Ningún esquema tiene campo de capacidad; MW fuera de un oficio se retira, ni en los descartes se repite; lo del oficio solo sale "según el oficio" | `test_ningun_esquema_tiene_campo_de_capacidad`, `test_capacidad_fuera_de_un_oficio_se_retira`, `test_lo_del_oficio_solo_sale_como_segun_el_oficio` |
| La muestra es ficticia, marcada en cada página y reproducible por su script | `test_la_muestra_es_ficticia_marcada_y_reproducible` |

## La muestra

`services/dataroom/muestra/cuarto/`: seis PDF ficticios generados por
`muestra/generar_muestra.py` (reportlab, reproducible byte a byte), cada página
con "DOCUMENTO FICTICIO — MUESTRA DGED". Nada es de una persona o empresa real;
el oficio de suministro lo emite un "Suministrador Eléctrico Ficticio", no CFE.
Errores plantados: m² de la Nave 2 (9,200 contrato contra 8,500 escritura),
contrato de la Nave 1 que vence el 2027-03-31, contrato de la Nave 2 sin
garantía, licencia de uso de suelo vencida el 2025-06-30 e inquilino "Gamma" en
la relación de rentas sin contrato. `muestra/respuestas_grabadas.json` trae lo
que contestaría el modelo, con **una cita parafraseada a propósito** (seguro de
la Nave 1) para que se vea el descarte. El escaneo de prueba se genera en el
test (`generar_muestra.pdf_escaneado`), no vive en la carpeta.

## Confidencialidad

Un cuarto de datos es información confidencial del vendedor, entregada al
comprador bajo NDA. Antes de leer el primero de un cliente:

- **NDA** firmado con el cliente (y que su NDA con el vendedor permita
  compartirlo con asesores como DGED).
- **Espacio por cliente**: una carpeta de entrada y una de salida por mandato;
  nada se mezcla entre clientes. El lector no guarda copia del texto fuera de
  la carpeta de salida y no escribe el texto de los documentos en logs.
- **Borrado al cierre**: al terminar el mandato se borran entrada, salida y
  cualquier copia local; se deja constancia escrita del borrado.
- **Términos comerciales de la API de Anthropic**, a revisar y dejar por escrito
  antes de procesar documentos de un cliente (no se asumen aquí):
  - si los datos enviados por la API se usan o no para entrenar modelos bajo
    los términos comerciales vigentes de la organización;
  - cuánto tiempo se retienen entradas y salidas por defecto, y si la
    organización tiene o puede pedir **retención cero (ZDR)**; y si el modelo
    elegido es elegible para esa retención;
  - si hace falta un acuerdo de tratamiento de datos (DPA) y en qué región se
    procesa (`inference_geo`), por si el cliente lo pide;
  - qué dice el NDA del cliente sobre subencargados: la API es uno.
  Si algo de esto no cuadra con el NDA, el documento no se procesa.

## Límites

- Solo PDF con capa de texto. Escaneos, imágenes y planos: **requiere OCR**
  (no hay OCR en este MVP). Tablas complejas pueden extraerse con el orden
  roto; si la cita deja de ser literal, el valor se descarta (se pierde, no se
  inventa).
- Un documento por llamada, con salida de hasta 16,000 tokens: una relación de
  rentas muy larga puede cortarse; entonces el documento queda "no revisado"
  entero, no a medias.
- La cita prueba que el texto **dice** algo, no que el resumen del modelo
  (campos de texto libre como "incrementos") sea completo. Las cifras, fechas,
  nombres y naves sí se comprueban contra la cita; los resúmenes se leen junto a
  su cita.
- Los cruces comparan naves por su identificador ("Nave 2") e inquilinos por
  razón social normalizada. Un cuarto que nombra distinto la misma nave en dos
  documentos no se cruza: queda sin bandera, no con una falsa.
- No hay catastro, Registro Público ni conversión de moneda. El memo lo dice en
  "Lo que no se revisó".
- n = 1 cuarto de datos (ficticio). Ningún cliente real todavía: la precisión de
  la extracción sobre documentos reales **no está medida**.
