# Verificación — 2026-10-12

Qué se midió de verdad sobre Atlas (`atlas-live-0.1.0`) y qué no. Medido desde
un contenedor de centro de datos con salida HTTPS por un proxy que intercepta
TLS. Lo que depende de esa red está marcado.

## Resumen

| Pregunta de `MEMORY/ESTADO.md` | Resultado |
|---|---|
| ¿Califica en vivo contra INEGI y CONAGUA? | **Sí, 10 de 10 sitios**, publicables, después de arreglar tres bugs (abajo). |
| ¿Levanta con `docker compose up --build` en menos de 40 min? | **Sí, en ~1 min** (20 s de imágenes + 39 s hasta `/api/health`), pero **solo con un override del sandbox**. Tal como está en el repo no se pudo levantar desde esta red (causas abajo, ninguna del proyecto). |
| ¿Postgres recibe filas? | **Sí**: 10 filas en `atlas_score` tras calificar los 10. PostGIS 16-3.4. |

## 1. Sin Docker (uvicorn, puerto 8092)

- Requisitos: `fastapi==0.115.6`, `uvicorn==0.34.0` (Python 3.13.16 local).
- **Primer arranque: falló.** `MunicipiosSequia.xlsx` llegó como HTTP 200
  `text/html` de 730 bytes ("This page can't be displayed", página de WAF) y
  `_load_rows` tronó con `BadZipFile`: **el API entero no levantaba**. Bug 1.
- Con el arreglo: arranque en frío (sin caché) **20.4 s** hasta `/api/health`;
  con caché caliente **4.9 s**. `/api/health` → `droughtRows: 2478`,
  `droughtAsOf: 2026-09-30`.

### `/api/sources` (2026-10-12, ~18:43 UTC)

| Fuente | ok | Detalle |
|---|---|---|
| INEGI WMS (`wms61`) | sí | GetCapabilities 200, 266 KB. |
| INEGI Catálogo Único (`wscatgeo/v2`) | sí | 5 estados (05, 11, 19, 22, 24). Marco Geoestadístico diciembre 2025. |
| SMN `MunicipiosSequia.xlsx` | **intermitente** | 2,150,283 bytes, 2,478 municipios, corte 2026-09-30, cuando contesta. Ver §4. |
| CONAGUA ArcGIS | no | Hoy **403**, no redirección (el cementerio dice redirección el 2026-10-10). |
| datos.gob.mx CKAN | sí hoy | 200 JSON en el arranque; con `curl` un minuto antes dio 403. Una sola observación: no revive nada (el cementerio pide dos días). |
| DENUE | modo ventana | Sin `INEGI_TOKEN`: muestra del GeoServer, no puntúa (D-008). |
| SAKBÉ | sin clave | "Clave NO autorizada". No puntúa. |
| Base de datos | no | Sin `DATABASE_URL` en este modo. |

### Los diez sitios, en vivo (código arreglado)

Factores: sequía (SMN) · inundación (INEGI c463/c424) · uso de suelo (INEGI c783).
DENUE y ruta **ausentes** en los diez (sin claves); no entran al número.
`coverage` = 1.0 en todos porque los pesos se reparten solo entre los tres
factores que existen sin clave (`_weights`).

| Sitio | Municipio (polígono INEGI) | Sequía 2026-09-30 | Inund. | Uso de suelo (serie VII) | Score | Antes del arreglo | Publicable | Latencia |
|---|---|---|---|---|---|---|---|---|
| apodaca-industrial | Apodaca, NL (19006) | D0 → 78 | no → 84 | Asentamientos humanos → 70 | **77.4** | 77.4 | sí | 2.13 s |
| pesqueria-kia | Pesquería, NL (19041) | D0 → 78 | no → 84 | Agricultura de riego anual → 52 | **72.0** | 72.0 | sí | 1.94 s |
| salinas-hofusan | **General Zuazua**, NL (19025) | D0 → 78 | no → 84 | Veg. secundaria matorral espinoso → 48 | **70.8** | 70.8 | sí | 2.26 s |
| garcia-poniente | García, NL (19018) | D0 → 78 | no → 84 | Asentamientos humanos → 70 | **77.4** | 77.4 | sí | 2.08 s |
| ramos-arizpe | Ramos Arizpe, Coah. (05027) | sin sequía → 92 | no → 84 | Asentamientos humanos → 70 | **83.0** | 77.4 (D0 del 2026-09-15) | sí | 1.97 s |
| puerto-interior | Silao, Gto. (11037) | D0 → 78 | no → 84 | Agricultura de riego anual y semip. → 52 | **72.0** | 72.0 | sí | 2.09 s |
| el-marques | El Marqués, Qro. (22011) | sin sequía → 92 | no → 84 | Agricultura de temporal anual → 52 | **77.6** | 72.0 (D0 del 2026-08-31) | sí | 1.75 s |
| celaya | Celaya, Gto. (11007) | sin sequía → 92 | no → 84 | Asentamientos humanos → 70 | **83.0** | 77.4 (D0 del **2025-05-31**) | sí | 2.11 s |
| slp-industrial | San Luis Potosí, SLP (24028) | sin sequía → 92 | no → 84 | Asentamientos humanos → 70 | **83.0** | 77.4 (D0 del **2025-06-30**) | sí | 1.69 s |
| leon-sur | León, Gto. (11020) | D0 → 78 | no → 84 | Asentamientos humanos → 70 | **77.4** | 77.4 | sí | 2.25 s |

- Errores: **0 de 10**. Latencia por calificación: 1.69–2.26 s (n=10).
- En Docker los diez dieron **los mismos números** (latencia 1.77–2.36 s).
- La inundación "no" en los diez es respuesta real: el WMS dijo
  `Search returned no results.` en c463 y c424. Para comprobar que la capa sí
  marca, se consultó Tlacotalpan, Ver. (18.61, −95.66): c424 devolvió
  `Feature 1691`. Villahermosa (17.99, −92.93) y el cauce del Santa Catarina en
  Monterrey (25.668, −100.31) dieron sin resultados: la capa no cubre todo lo
  que uno esperaría que fuera inundable. Es la capa, no el código.
- **Para el dueño:** el punto de `salinas-hofusan` (25.869, −100.214) cae en el
  polígono de **General Zuazua**, no de Salinas Victoria. No se tocó la semilla.
- `/api/examples` guarda solo las **últimas 12 llamadas** (≈2.4 sitios); no
  incluye la URL del SMN. Muestra guardada (Docker, León/SLP/Celaya):
  - `https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/11` (ok)
  - `https://gaia.inegi.org.mx/NLB/tunnel/wms/wms61?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=c783&QUERY_LAYERS=c783&CRS=EPSG%3A4326&BBOX=21.06%2C-101.67%2C21.099999999999998%2C-101.63000000000001&WIDTH=101&HEIGHT=101&I=50&J=50&INFO_FORMAT=text%2Fhtml&FEATURE_COUNT=1` (ok)
  - `https://gaia.inegi.org.mx/NLB/tunnel/wms/wms61?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=c424&QUERY_LAYERS=c424&CRS=EPSG%3A4326&BBOX=21.06%2C-101.67%2C21.099999999999998%2C-101.63000000000001&WIDTH=101&HEIGHT=101&I=50&J=50&INFO_FORMAT=text%2Fplain&FEATURE_COUNT=1` (ok)
  - `https://gaia.inegi.org.mx/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo&LAYERS=denue%3Aindustrias_manufactureras&QUERY_LAYERS=denue%3Aindustrias_manufactureras&SRS=EPSG%3A4326&BBOX=-101.68%2C21.049999999999997%2C-101.62%2C21.11&WIDTH=101&HEIGHT=101&X=50&Y=50&INFO_FORMAT=application%2Fjson&FEATURE_COUNT=5` (ok, ventana)
  - `https://gaia.inegi.org.mx/sakbe_v3.1/genera_token.jsp` (no: sin clave)
  - Sequía: `https://smn.conagua.gob.mx/tools/RESOURCES/Monitor%20de%20Sequia%20en%20Mexico/MunicipiosSequia.xlsx`

## 2. Con Docker

Daemon: no corría; se inició `dockerd` en segundo plano (Docker 29.8.2,
Compose v5.6.0, overlayfs, cgroup v1).

| Intento | Resultado | Tiempo |
|---|---|---|
| `docker compose up --build -d` tal cual | **Falló**: Docker Hub respondió **429 Too Many Requests** a `python:3.12-slim` (límite anónimo desde IP compartida). | 17 s |
| Imágenes por `mirror.gcr.io` (python 3.12-slim 179 MB, postgis 16-3.4 853 MB), re-etiquetadas | Descarga cronometrada | 4.8 s + 14.9 s |
| Build tal cual con imágenes locales | **Falló**: `pip` contra pypi.org con `CERTIFICATE_VERIFY_FAILED` (el proxy del sandbox intercepta TLS). | 14 s |
| Override del sandbox (CA del proxy, `network: host`, variables de proxy), build sin caché | **Levantó.** `compose up` devolvió a los 20.6 s; `/api/health` en 8080 a los **39.2 s**; `pip install` 8.8 s. | **39.2 s** (+19.7 s de imágenes = **~59 s**) |
| Rebuild con el arreglo de reintento (caché de capas) | Levantó; SMN contestó al arrancar; 10/10 calificados. | 32.6 s |

- El override vive fuera del repo (scratchpad): CA de `/root/.ccr`,
  `network_mode: host` y `DATABASE_URL` a `127.0.0.1:5432`. **No cambia nada del
  proyecto**; en una máquina con salida directa a Docker Hub y pypi no hace falta.
  Lo que no se midió: `docker compose up --build` tal cual desde una red sin
  proxy. El criterio de 40 min se cumple con holgura en lo medido; que se
  cumpla tal cual en otra red es inferencia, no medición.
- Postgres/PostGIS sano (healthcheck), `010_runtime.sql` creó `atlas_site` y
  `atlas_score`. `/api/sources` → `database.ok: true`.
- Tras calificar: `select count(*) from atlas_score` = **10**, con composite y
  sequía iguales a la tabla de arriba.
- En el primer arranque en Docker el SMN devolvió la página de WAF:
  `/api/health` contestó con `droughtRows: null` y `POST /score` dio **503**
  hasta reiniciar. Bug 3.
- `docker compose down -v`: contenedores, red y volúmenes borrados.

## 3. Bugs arreglados (cada uno con su test, rojo sin el arreglo)

1. **Una página de error con 200 tumbaba el arranque**
   (`connectors/conagua.py::load_drought`). Se guardaba como `.xlsx` y
   `BadZipFile` mataba el startup. Ahora: el cuerpo tiene que empezar con `PK`;
   si no, `ok: false` con el error dicho, sin escribir la caché; una caché que
   no es ZIP se vuelve a pedir; un libro viejo bueno se usa marcado `stale`.
   Test: `services/api/test_conagua.py` (3 tests).
2. **Sequía rancia reportada como actual** (`conagua._load_rows`). Caminaba
   hacia atrás hasta la última celda llena. En la hoja NOTAS del propio libro,
   "Sin Sequía" **no tiene clave**: la celda vacía es sin sequía. En el corte
   2026-09-30, **955 de 2,478** municipios están vacíos; el código les ponía la
   última categoría que tuvieron (85 filas con fecha de **2024-07-15**). Cuatro
   de los diez sitios cambiaban de número (Celaya y SLP con D0 de 2025).
   Ahora se lee solo el último corte; vacío → `NONE`. No se tocaron pesos ni
   puntajes. Test: `test_conagua.py::test_celda_vacia_en_el_ultimo_corte_es_sin_sequia`.
3. **Sin reintento del SMN** (`main.py`). Se cargaba solo al arrancar; con el
   WAF al arranque, 503 para siempre. Ahora `POST /score` reintenta una vez si
   no hay tabla. Test: `services/api/test_reintento_sequia.py` (2 tests).
   El reintento en vivo no se ejercitó (el SMN contestó en el arranque del
   rebuild); lo cubre el test.
4. **Inundación: una respuesta no reconocida contaba como "no inundable"**
   (`connectors/inegi.py::flood_at`). Todo lo que no fuera "no results" ni
   "Feature" caía al final como `known: true, hit: false` → 84 puntos sin
   dato. No ocurrió hoy (INEGI contestó bien los diez); es el mismo patrón del
   bug 1. Ahora es `known: false` y el sitio deja de ser publicable.
   Test: `services/api/test_inegi_flood.py` (3 tests).

## 4. SMN intermitente

12 descargas con `curl`, cada ~5 s (18:50–18:51 UTC): **3** entregaron el
libro (2,150,283 bytes) y **9** la página de WAF de 730 bytes, todas con HTTP
200. Con n=12 no se estima una tasa; sí se ve que es intermitente desde esta
red. No se sabe si pasa igual desde una IP mexicana o residencial.

## 5. Lo que sigue sin medir

- `docker compose up --build` tal cual, desde una red sin proxy ni límite de Docker Hub.
- DENUE conteo y SAKBÉ minutos (sin `INEGI_TOKEN` ni `SAKBE_TOKEN`).
- El comportamiento del SMN desde otra red (§4).
