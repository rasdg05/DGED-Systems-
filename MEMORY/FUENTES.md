# Fuentes medidas — catálogo

> Una fuente se **mide** antes de escribir su código: ¿responde desde un
> servidor?, ¿cada cuándo publica?, ¿trae dato de verdad para un punto de
> México? Aquí va lo que se midió, con el valor que devolvió. Las MUERTAS
> también van a `CEMENTERIO.md`. Para volver a medir:
>
> ```bash
> python3 herramientas/medir_fuentes.py --salida medicion.json          # Apodaca y Silao
> python3 herramientas/medir_fuentes.py --punto 25.78,-100.19
> ```

**Medición:** 2026-10-12, entre 18:33 y 18:50 UTC, con peticiones reales
(curl y `urllib`, tiempo máximo 20 s; Overpass 45 s). Puntos: **Apodaca NL
(25.78, -100.19)** y **Silao Gto (20.95, -101.43)**.

**Desde dónde se midió (importa):** un contenedor en la nube detrás de un proxy
de salida con IP compartida. Ahí (1) los puertos no estándar (8080, 8082, 8443)
no pasan, (2) algunos hosts cortan la conexión en el proxy
(`overpass-api.de`, `download.geofabrik.de`, `atlasnacionalderiesgos.gob.mx`) y
(3) la IP compartida agota cuotas diarias por IP (Open-Meteo). Por eso hay un
cuarto y un quinto veredicto: **NO CONCLUYE** (no hubo respuesta HTTP: no se
midió) y **CUOTA** (respondió 429). *"No medido" no es "medido y no funcionó"*:
lo que dice NO CONCLUYE se vuelve a medir desde el servidor de producción antes
de enterrarlo.

**Un HTTP 200 no es un dato.** El SMN contesta 200 con una página de error de su
WAF (730 bytes de HTML). El script revisa el contenido, no el código.

## Tabla

| Clave | Fuente | HTTP | Latencia | Clave | Veredicto | Valor observado (resumen) |
|---|---|---|---|---|---|---|
| `usgs.sismos` | USGS FDSN event | 200 | 1.8–2.5 s | no | **VIVA** | Apodaca: 19 sismos M≥4 a ≤200 km desde 1976; Silao: 21 |
| `nasa.power` | NASA POWER climatología | 200 | 0.5–0.6 s | no | **VIVA** | Apodaca T2M 22.68 °C, 1.74 mm/día; Silao 17.28 °C, 1.83 mm/día |
| `stac.earthsearch.s2` | Element84 Earth Search, sentinel-2-l2a | 200 | 0.3–0.6 s | no | **VIVA** | Escena del 2026-10-10; nubes 24.3 % (Apodaca), 78.5 % (Silao) |
| `stac.planetary.s2` | Microsoft Planetary Computer STAC | 200 | 0.5–0.8 s | no (búsqueda) | **VIVA** | Misma fecha; nubes 24.3 % y 81.5 % |
| `stac.copdem30` | Copernicus DEM GLO-30 (Earth Search) | 200 | 0.2 s | no | **VIVA** | Mosaicos `N25_00_W101_00` y `N20_00_W102_00` |
| `worldbank.mex` | World Bank API v2 | 200 | 0.16–0.18 s | no | **VIVA** | Acceso a electricidad 99.8 % (2024); empleo industrial 24.52 % (2025) |
| `inegi.catgeo` | INEGI Catálogo Único `wscatgeo/v2` | 200 | 0.4–0.8 s | no | **VIVA** | Apodaca 19006, 656,464 hab.; Silao 11037, 203,556 hab. |
| `jrc.ghsl` | JRC GHSL BUILT-S R2023A (descarga) | 200 | 1.0–1.6 s | no | **VIVA** | 375 mosaicos .zip listados |
| `osm.overpass` | OSM Overpass (espejo `maps.mail.ru`) | 200 / 504 | 10.9–20.8 s | no | **VIVA, intermitente** | Apodaca: 44 subestaciones a ≤10 km, la más cercana a 1.09 km (115 kV) |
| `openmeteo.pronostico` | Open-Meteo forecast | 200 / 429 / sin respuesta | 0.8–1.0 s | no | **CUOTA** (y solo no comercial) | Silao: lluvia 4.5 / 4.3 / 0.7 mm, Tmáx 24.3–25.4 °C |
| `openmeteo.elevacion` | Open-Meteo elevation | 200 / 429 | 0.5–0.8 s | no | **CUOTA** (y solo no comercial) | 433 m (Apodaca), 1,781 m (Silao) |
| `openmeteo.archivo` | Open-Meteo historical archive | 429 | 0.5–0.6 s | no | **CUOTA** | `Daily API request limit exceeded` en todos los intentos |
| `smn.sequia_xlsx` | SMN `MunicipiosSequia.xlsx` | 200 | 0.25–0.5 s | no | **VIVA, intermitente** | xlsx de 2,150,283 bytes en 4 de 30 intentos; el resto, página del WAF |
| `banxico.sie` | Banxico SIE API | 400 | 0.3–0.4 s | **sí** | **CON CLAVE** | `Token inválido` |
| `inegi.bie` | INEGI Indicadores (BIE/BISE) | 400 | 0.7–0.8 s | **sí** | **CON CLAVE** | Sin token válido: `ErrorCode:100` |
| `nasa.firms` | NASA FIRMS área | 400 | 0.2–0.3 s | **sí** | **CON CLAVE** | `Invalid MAP_KEY.` |
| `smn.webservices` | SMN pronóstico por municipio | 200 (WAF) | 0.3–0.7 s | no | **MUERTA** | 0 de 30 intentos con dato: siempre la página del WAF |
| `conagua.sigagis` | CONAGUA ArcGIS REST | 302 → 403 | 0.2–0.7 s | — | **MUERTA** | No devuelve JSON (ya estaba en el cementerio) |
| `datosgob.ckan` | datos.gob.mx CKAN | 403 | 0.2–0.5 s | — | **MUERTA** | `Access Denied` en 3 de 3 |
| `cenace.pml` | CENACE SW-PML, `ws01.cenace.gob.mx:8082` | sin respuesta | — | no (según su manual) | **NO CONCLUYE** | Puerto 8082: el proxy corta la conexión |
| `osm.geofabrik` | Geofabrik, extracto de México | sin respuesta | — | no | **NO CONCLUYE** | El proxy corta la conexión |
| `cenapred.anr` | Atlas Nacional de Riesgos (portada) | sin respuesta | — | — | **NO CONCLUYE** | El proxy corta la conexión |
| `ssn.unam` | SSN UNAM, catálogo `:8080` | sin respuesta | — | — | **NO CONCLUYE** | Tiempo agotado, puerto 8080 |

## Detalle por fuente

### `usgs.sismos` — USGS Earthquake Catalog (FDSN) — VIVA
- URL: `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude=25.78&longitude=-100.19&maxradiuskm=200&starttime=1976-01-01&minmagnitude=4&orderby=magnitude&limit=5`
  (y `/count?` con los mismos filtros, sin `limit` ni `orderby`).
- Valor: **Apodaca**, 19 eventos M≥4 a ≤200 km desde 1976. El mayor fue M4.6, "3 km NNE of
  Saltillo", del 2000-06-15, a 89 km. **Silao**, 21 eventos. El mayor fue M5.3,
  "4 km WSW of Tepuxtepec", del 1979-02-22, a 162 km.
- Frecuencia: catálogo continuo (minutos para eventos nuevos). Licencia: dominio público (USGS).
- Uso: contexto de sismicidad instrumental. **No sustituye** la regionalización sísmica
  CFE (`cfe.sismico`), que es la que trae zona A–D. La cobertura de M<4 en México es
  incompleta en ComCat. Para eso está el SSN, que aquí no concluyó.

### `nasa.power` — NASA POWER, climatología por punto — VIVA
- URL: `https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=T2M,T2M_MAX,PRECTOTCORR,ALLSKY_SFC_SW_DWN,WS10M&community=RE&longitude=-100.19&latitude=25.78&format=JSON`
- Valor anual (`ANN`) en **Apodaca**: T2M 22.68 °C, T2M_MAX 45.36 °C, PRECTOTCORR 1.74
  mm/día, ALLSKY_SFC_SW_DWN 5.44 kWh/m²/día y WS10M 3.88 m/s. En **Silao**: 17.28 °C,
  36.48 °C, 1.83 mm/día, 5.98 kWh/m²/día y 3.73 m/s.
- Periodo, según la propia respuesta: *"January 2001 - December 2025"* (fuente MERRA-2
  para meteorología). Es una climatología fija y se renueva cuando NASA rehace el
  periodo. API v2.10.1. Sin clave.
- Uso: calor extremo y radiación como contexto. Es una celda de ~0.5°, no del predio.

### `stac.earthsearch.s2` — Sentinel-2 L2A en Earth Search (Element84) — VIVA
- URL: `POST https://earth-search.aws.element84.com/v1/search` con
  `{"collections":["sentinel-2-l2a"],"intersects":{"type":"Point","coordinates":[-100.19,25.78]},"limit":1,"sortby":[{"field":"properties.datetime","direction":"desc"}]}`
- Valor: en Apodaca, `S2C_14RLP_20261010_0_L2A` del 2026-10-10 a las 17:26 UTC, con nubosidad
  de 24.3 %. En Silao, `S2C_13QHD_20261010_0_L2A`, con 78.5 %. Trae bandas COG
  (`blue`, `cloud`, `coastal`…) en S3 público.
- Frecuencia: revisita de unos 5 días. Licencia: datos Copernicus, libres y abiertos.
- Uso: la figura de cambio de suelo del memo (`docs/02-fuentes.md`), **no entra al número**.

### `stac.planetary.s2` — Microsoft Planetary Computer — VIVA
- URL: `POST https://planetarycomputer.microsoft.com/api/stac/v1/search` (misma consulta).
- Valor: en Apodaca, `S2C_MSIL2A_20261010T171231_R112_T14RLP_…`, con 24.3 % de nubes. En
  Silao, `…T14QKJ…`, con 81.5 %. La búsqueda no pide clave; los assets se firman con un
  token SAS (no se midió la firma).

### `stac.copdem30` — Copernicus DEM GLO-30 — VIVA
- URL: Earth Search, colección `cop-dem-glo-30`. Mosaicos `Copernicus_DSM_COG_10_N25_00_W101_00_DEM`
  y `…_N20_00_W102_00_DEM`. `HEAD` del COG en `copernicus-dem-30m.s3.amazonaws.com` → 200.
- Leer el píxel o la pendiente exige GDAL o rasterio (no stdlib). Es la alternativa
  global a `inegi.cem` para la pendiente en 300 m.

### `worldbank.mex` — World Bank API — VIVA
- URL: `https://api.worldbank.org/v2/country/MEX/indicator/EG.ELC.ACCS.ZS?format=json&mrnev=1`
- Valor: EG.ELC.ACCS.ZS = 99.8 (2024); NY.GDP.MKTP.CD = 1,832,641,364,775.52 USD (2025);
  SL.IND.EMPL.ZS = 24.52 % (2025). `lastupdated` 2026-10-08. CC BY 4.0.
- Uso: nacional. Sirve de contexto para el memo y **no rankea predios**.

### `inegi.catgeo` — Catálogo Único de claves geoestadísticas — VIVA
- URL: `https://gaia.inegi.org.mx/wscatgeo/v2/mgem/19` (y `/11`). Con geometría:
  `/wscatgeo/v2/geo/mgem/19`, que pesa 2.29 MB y tardó 2.5 s.
- Valor: NL tiene 51 municipios; Apodaca (`19006`) tiene 656,464 hab. Guanajuato tiene 46;
  Silao de la Victoria (`11037`) tiene 203,556 hab. Metadatos: *"Marco Geoestadístico,
  diciembre de 2025"* y *"Censo de Población y Vivienda, 2020"*.
- Ya está en producción (`catgeo.py`). Esta es la primera medición en vivo
  desde esta copia (`ESTADO.md` la tenía como no medida).

### `jrc.ghsl` — Global Human Settlement Layer — VIVA (descarga)
- URL: `https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_BUILT_S_GLOBE_R2023A/GHS_BUILT_S_E2030_GLOBE_R2023A_54009_100/V1-0/tiles/`
- Valor: 375 mosaicos `.zip` listados. Es un raster por mosaico, sin API por punto, y
  leerlo exige GDAL. CC BY 4.0. Las épocas son quinquenales.
- Uso posible: superficie construida alrededor del predio. No se midió el valor en el punto.

### `osm.overpass` — OpenStreetMap vía Overpass — VIVA, intermitente
- URL: `POST https://maps.mail.ru/osm/tools/overpass/api/interpreter` con
  `nwr(around:10000,…)["power"="substation"]`, `way(around:5000,…)["power"="line"]`,
  `way(around:10000,…)["railway"="rail"]` y `nwr(around:30000,…)["aeroway"="aerodrome"]`.
- **Apodaca** (base OSM del 2026-10-12T18:48:51Z):
  - 44 subestaciones a ≤10 km, 37 con `voltage`. La más cercana está a 1.09 km (115 kV).
  - Tramos de línea a ≤5 km: 48 de 115 kV, 8 de 230 kV y 5 de 400 kV.
  - 126 tramos de vía férrea a ≤10 km.
  - Aeropuertos: MTY a 8.13 km y NTR a 10.59 km.
- **Silao**:
  - 17 subestaciones, 15 con `voltage`. La más cercana está a 1.69 km (115 kV).
  - Tramos de línea: 12 de 115 kV y 1 de 230 kV.
  - 120 tramos de vía férrea.
  - Aeropuerto: BJX a 7.17 km.
- Disponibilidad: `overpass-api.de` cortó la conexión en todos los intentos (~9).
  `maps.mail.ru` respondió en 5 de 8 intentos por punto (otros: 504 o tiempo agotado
  a 45 s). `overpass.kumi.systems` y `overpass.private.coffee` agotaron el tiempo. n < 30: no concluye
  sobre la tasa.
- Lectura: en estos dos puntos, 52 de 61 subestaciones traen `voltage`. Dos puntos
  no concluyen para el país. Siguen siendo **candidatos sin capacidad** (D-003,
  Constitución V). Para producción conviene el extracto de Geofabrik (ya previsto en
  `docs/02-fuentes.md`), que aquí no concluyó.
- Licencia: ODbL.

### `openmeteo.*` — Open-Meteo — CUOTA, y la API gratuita es solo no comercial
- URLs: `https://api.open-meteo.com/v1/forecast?latitude=…&daily=precipitation_sum,temperature_2m_max,…`,
  `https://archive-api.open-meteo.com/v1/archive?…` y `https://api.open-meteo.com/v1/elevation?…`
- Valor (cuando respondió):
  - Apodaca: elevación 433 m. Del 2026-10-12 al 14, lluvia 0 / 0 / 0 mm y Tmáx 32.3 / 33.3 / 31.6 °C.
  - Silao: elevación 1,781 m. Lluvia 4.5 / 4.3 / 0.7 mm y Tmáx 24.3 / 24.3 / 25.4 °C.
- El archivo histórico respondió **429** *"Daily API request limit exceeded. Please try
  again tomorrow."* en todos los intentos. El pronóstico y la elevación alternaron entre
  200, 429 y el *handshake* agotado. La cuota es por IP y la IP del proxy es compartida.
- **Términos** (`https://open-meteo.com/en/terms`, leídos el 2026-10-12): *"You may only
  use the free API services for non-commercial purposes"*. Los límites son menos de
  10,000 llamadas al día, 5,000 por hora y 600 por minuto, con datos CC BY 4.0.
  **Atlas es comercial**: la API gratuita no sirve para producción. Hace falta el plan
  de pago o alojar Open-Meteo nosotros (es código abierto). Esa decisión es del dueño.

### `smn.sequia_xlsx` — Monitor de Sequía, `MunicipiosSequia.xlsx` — VIVA, intermitente
- URL: `https://smn.conagua.gob.mx/tools/RESOURCES/Monitor%20de%20Sequia%20en%20Mexico/MunicipiosSequia.xlsx`
- Valor: xlsx (firma `PK`) de 2,150,283 bytes, en **4 de 30** intentos seguidos (con
  1 s entre intentos, 18:44–18:45 UTC). En corridas sueltas, 1 de 5 y 2 de 5. El resto
  de los intentos contestó **HTTP 200 con la página de error del WAF** (730 bytes, *"This page can't be
  displayed"*), con cualquier User-Agent probado.
- Publica cada mes (quincenal en temporada). Es **la fuente de sequía del score**
  (Constitución I).
- **Hallazgo para el conector** (`services/api/atlas/connectors/conagua.py`, que no
  toca este agente): el conector debe exigir la firma `PK` y reintentar. Debe conservar
  la última copia buena en caché en vez de sobrescribirla con la página del WAF.
  Necesita un test que lo cuide.

### `banxico.sie` — Banxico SIE — CON CLAVE
- URL: `https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno`
- Sin token responde 400: *"Token inválido (...) Para obtener un token consultar la url
  adjunta"* → `https://www.banxico.org.mx/SieAPIRest/service/v1/token`.
- **Cómo se pide**: en esa URL, con un correo, y es gratuito. Va en la cabecera
  `Bmx-Token`. El script la lee de `BANXICO_TOKEN`.

### `inegi.bie` — INEGI API de Indicadores (BIE/BISE) — CON CLAVE
- URL: `https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/1002000001/es/0700/false/BISE/2.0/{TOKEN}?type=json`
- Con un token falso responde 400 `ErrorCode:100` (*"No se encontraron resultados"*).
  El error no dice "token". Que exige clave lo dice la documentación del INEGI
  (`https://www.inegi.org.mx/servicios/api_indicadores.html`).
- **Cómo se pide**: en `https://www.inegi.org.mx/app/desarrolladores/generatoken/Usuarios/token_Verify`
  (respondió 200), con un correo. **Es otro token que el de DENUE**. El script lo lee de
  `INEGI_BIE_TOKEN`.

### `nasa.firms` — NASA FIRMS (focos de calor) — CON CLAVE
- URL: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/{oeste,sur,este,norte}/5`
  (el rango válido es de 1 a 5 días).
- Con `DEMO_KEY` responde 400 `Invalid MAP_KEY.`
- **Cómo se pide**: en `https://firms.modaps.eosdis.nasa.gov/api/map_key/`, gratis con un
  correo (*"The key will be sent to your email"*). El script la lee de `FIRMS_MAP_KEY`.
- Uso posible: incendios cercanos como contexto, casi en tiempo real.

### `smn.webservices` — SMN pronóstico por municipio — MUERTA (desde un servidor)
- URL: `https://smn.conagua.gob.mx/webservices/?method=1`
- **0 de 30** intentos seguidos trajeron dato, y tampoco ninguno de los ~40 sueltos. Siempre
  devolvió HTTP 200 con la página del WAF (730 B). Una sola vez respondió 301.
- Reemplazo para el pronóstico: ninguno gratuito y comercial medido hoy (Open-Meteo es
  no comercial).

### `conagua.sigagis` — CONAGUA ArcGIS REST — MUERTA (re-confirmada)
- URL: `https://sigagis.conagua.gob.mx/ArcGIS/rest/services?f=pjson`. Con curl dio 302 a
  una página "Loading" y con `urllib`, 403. No devuelve JSON. Ya estaba en el cementerio
  desde el 2026-10-10.
- La disponibilidad de acuíferos sigue sin fuente legible por máquina medida. Se cita
  el acuerdo publicado en el DOF (`docs/02-fuentes.md`).

### `datosgob.ckan` — datos.gob.mx — MUERTA (re-confirmada)
- URL: `https://datos.gob.mx/api/3/action/package_search?q=acuiferos&rows=1` → 403
  `Access Denied` en 3 de 3. El cementerio decía "a veces"; hoy fue siempre.

### `cenace.pml` — CENACE SW-PML — NO CONCLUYE
- URL: `https://ws01.cenace.gob.mx:8082/SWPML/SIM/SIN/MDA/04PLD-115/{aaaa/mm/dd}/{aaaa/mm/dd}/JSON`
- El proxy de este entorno no atraviesa el puerto 8082. También se probó con
  `portquiz.net:8443`: no es CENACE, es el entorno. El portal `www.cenace.gob.mx`
  sí respondió 200.
- Lo que dice su manual público (`https://www.cenace.gob.mx/DocsMEM/2020-01-14%20Manual%20T%C3%A9cnico%20SW-PML.pdf`,
  PDF descargado y leído):
  - Es REST por GET y el manual no menciona usuario ni token.
  - El periodo va de 1 a 7 Días de Operación.
  - El MDA se publica un día antes del Día de Operación y el MTR siete días después.
  - El PML es **por NodoP, no por punto**.
- Pendiente: medirlo desde un servidor con salida abierta al 8082. Mientras tanto
  sigue fuera del score 0.1 (`docs/02-fuentes.md`).

### `osm.geofabrik`, `cenapred.anr`, `ssn.unam` — NO CONCLUYE
- `https://download.geofabrik.de/north-america/mexico-updates/state.txt`: el proxy cortó
  la conexión (reset).
- `https://www.atlasnacionalderiesgos.gob.mx/`: reset. Las capas de inundación y laderas
  (`cenapred.*`) siguen sin medirse.
- `http://www2.ssn.unam.mx:8080/catalogo/`: tiempo agotado. Es el puerto 8080.

## Lo que sigue

1. Volver a correr `herramientas/medir_fuentes.py` **desde el servidor de producción**
   para las cuatro NO CONCLUYE y para Open-Meteo, que fue CUOTA por la IP compartida.
2. Endurecer el conector de sequía contra el 200 del WAF (firma `PK`, reintento y
   caché buena), con su test.
3. El dueño decide si se paga Open-Meteo o se aloja nosotros. NASA POWER cubre la
   climatología sin clave mientras tanto.
4. Pedir los tokens de Banxico, INEGI BIE y FIRMS si un factor los necesita. Hoy
   ninguno entra al número.
