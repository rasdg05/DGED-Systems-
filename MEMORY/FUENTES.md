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

---

## Medición del 2026-10-13 — radar, recorte óptico, frontera, compras públicas y FIRMS sin clave

**Cuándo y desde dónde:** 2026-10-13, entre 01:12 y 04:52 UTC, desde el mismo
contenedor con proxy de salida (mismas salvedades de arriba). Peticiones reales
con curl, `urllib` y, para validar el lector stdlib, rasterio 1.4.3. Puntos:
Apodaca, Silao y, para radar sobre la costa, **Coatzacoalcos Ver (18.15, -94.42)**.
Estas fuentes son las que habilitan los productos de `docs/13-comparables-precio.md`
§2–6. Para volver a medirlas:

```bash
python3 herramientas/medir_fuentes.py --solo stac.planetary.s1,stac.earthsearch.s1,stac.earthsearch.s2.recorte,cbp.bwt,compras.comprasmx,compras.ocds_nl,compras.obra_smpu_nl,pnt.transparencia,nasa.firms.csv24h
```

### Tabla

| Clave | Fuente | HTTP | Clave | Veredicto | Valor observado (resumen) |
|---|---|---|---|---|---|
| `stac.planetary.s1` | Sentinel-1 RTC/GRD, Planetary Computer | 200 búsqueda · 409 sin firma · 206 con firma | no (firma SAS anónima) | **VIVA** | Apodaca: RTC del 2026-10-10 (asc.); Coatzacoalcos: RTC del 2026-10-09 (desc.), GRD del 2026-10-12. Recorte de 100×100 px leído |
| `stac.earthsearch.s1` | Sentinel-1 GRD, Earth Search | 200 búsqueda · 206 anónimo | no (el STAC dice *requester pays*) | **VIVA** (acceso al COG: re-medir) | Misma escena GRD del 2026-10-10 (Apodaca) y del 2026-10-12 (Coatzacoalcos); cabecera TIFF leída sin firmar |
| `stac.earthsearch.s2.recorte` | Sentinel-2 L2A, COG B04/B08 | 206 | no | **VIVA** | Escena del 2026-09-15 (0.48 % nubes); 1 km² en Apodaca: B04 0.0874, B08 0.1343, NDVI 0.212; 1.73 MB y ~1.9 s por banda |
| `cbp.bwt` | CBP Border Wait Times `api/bwtnew` | 200 | no | **VIVA** | 85 cruces, 55 de la frontera con México; WTB Laredo: 45 min y 10 de 19 carriles (corte 7:00 pm CDT) |
| `compras.ocds_nl` | OCDS del Gobierno de NL (OCP Data Registry) | 200 | no | **VIVA** | 2026: 4,256 *releases* (del 2026-01-13 al 2026-09-11); 3,588 adjudicaciones directas; 4,052 con proveedor y monto |
| `compras.obra_smpu_nl` | Obra pública por licitación, Movilidad y Planeación Urbana de NL | 200 | no | **VIVA** | 179 contratos de 2021 a 2025, los 179 con coordenadas; MXN 16,459,820,910 en suma |
| `nasa.firms.csv24h` | FIRMS, CSV público de 24 h (Centroamérica) | 200 | no | **VIVA** | NOAA-20: 1,039 focos en la región; 3 a ≤50 km de Apodaca (el más cercano a 12.37 km); 10 de Silao |
| `nasa.firms` | FIRMS API por área | 400 | **sí** | **CON CLAVE** (re-confirmada) | `Invalid MAP_KEY.` con `DEMO_KEY` |
| `compras.comprasmx` | ComprasMX (sucesor de CompraNet), datos abiertos | 403 | — | **MUERTA** (para lectura por máquina) | `{"success":false,"error":"Acceso no permitido."}` |
| `pnt.transparencia` | Plataforma Nacional de Transparencia, consulta (SIPOT) | 403 | — | **MUERTA** (para lectura por máquina) | Página de captcha: *"ayudanos a solucionar el siguiente captcha para verificar que eres humano"* |
| — | `compranet.hacienda.gob.mx`, `contratacionesabiertas.hacienda.gob.mx`, `api.datos.gob.mx` | sin respuesta | — | **NO CONCLUYE** | El proxy rechazó el CONNECT (502) en los dos primeros; el tercero se agotó a los 12 s |
| — | `datos.gob.mx` (portada y `/dataset/compranet`) | 403 | — | MUERTA (ya en el cementerio) | Igual que el 2026-10-12 |

### `stac.planetary.s1` — Sentinel-1 en Planetary Computer — VIVA
- Búsqueda: `POST https://planetarycomputer.microsoft.com/api/stac/v1/search`, colecciones
  `sentinel-1-rtc` (retrodispersión corregida por terreno, ya proyectada en UTM a 10 m) y
  `sentinel-1-grd`.
- Escena más reciente:
  - **Apodaca**: `S1D_IW_GRDH_1SDV_20261010T004136_…_rtc`, del 2026-10-10 a las 00:41 UTC,
    órbita ascendente, VV+VH, modo IW.
  - **Coatzacoalcos**: RTC `S1D_…_20261009T120916_…`, del 2026-10-09 (descendente). En GRD
    hay una más nueva, `S1D_…_20261012T002256_…`, del 2026-10-12. Frontera (Tabasco,
    18.53, -92.93): RTC `S1C_…_20261010T120034_…`, del 2026-10-10.
- **Lectura del COG:** sin firma, el blob responde **409** `PublicAccessNotPermitted`.
  `GET https://planetarycomputer.microsoft.com/api/sas/v1/sign?href=…` responde 200 sin
  cuenta, con una firma que caduca en ~45 min (`msft:expiry`). Con la firma, la petición
  de rango responde **206**. El RTC VV de Apodaca mide 28,061 × 21,173 px, en EPSG:32614,
  con mosaicos de 512 y vistas reducidas de 2 a 64. Con rasterio, una ventana de
  100×100 px sobre el punto tardó 2.8 s: 10,000 válidos y mediana lineal 0.2358
  (−6.27 dB). En Coatzacoalcos: EPSG:32615, mediana 0.1934 (−7.14 dB), 1.4 s.
- **Revisita medida** (escenas GRD distintas en 60 días, 2026-08-14 → 2026-10-13):
  - **Apodaca**: 10 días con escena. Huecos de 5 y 7 días; **el máximo fue 7**. Solo pasó S1D.
  - **Silao**: 20 días con escena, hueco máximo de 6 días y mediano de 2. Pasaron S1C y S1D.
  - **Coatzacoalcos**: 20 días con escena, **cada 3 días exactos**. Pasaron S1C y S1D.
  - Para `docs/13` §4.2: sobre la costa del Golfo, la primera imagen de radar después de
    un evento puede tardar **hasta 3 días**; en Apodaca, hasta 7. A eso hay que sumar la
    latencia de publicación, que no se midió. **La promesa de "≤ 24 h desde el evento" no
    se puede escribir con Sentinel-1.** Lo que sí se puede escribir es "≤ 24 h desde la
    primera imagen útil".
- La firma SAS no se publica: la salida del script lleva la URL sin su query (test
  `test_s1_planetary_no_publica_la_firma_sas`).
- Licencia: datos Copernicus, libres. El RTC lo produce Microsoft (CC BY 4.0).

### `stac.earthsearch.s1` — Sentinel-1 GRD en Earth Search — VIVA (acceso al COG: re-medir)
- La búsqueda responde con las **mismas escenas** que Planetary Computer.
- Los assets están en `s3://sentinel-s1-l1c/…` (eu-central-1) y el STAC los marca
  `storage:requester_pays: true`. Aun así, aquí un GET **anónimo y sin firmar** respondió
  **206** en 3 de 3 intentos, y el listado del bucket respondió 200. No se concluye que
  siga abierto: si un día da 403, hace falta una cuenta de AWS que pague la salida.
- El GRD viene en **geometría de radar**: no tiene CRS, solo 210 GCP. Leer un punto exige
  GDAL. La ventana central (100×100 px) dio la misma mediana de DN (175) que el mismo
  producto en Planetary Computer.
- Para Atlas conviene el **RTC de Planetary Computer**: ya viene en UTM y corregido por
  terreno.

### `stac.earthsearch.s2.recorte` — recorte real de Sentinel-2 — VIVA
- La escena más reciente con menos de 20 % de nubes sobre Apodaca es
  `S2B_14RLP_20260915_0_L2A` (2026-09-15, 0.48 %). La más reciente sin filtro es la del
  2026-10-10, con 24.3 % de nubes.
- Lectura **solo con stdlib** (`leer_recorte_cog`): peticiones de rango, IFD del TIFF,
  UTM calculado a mano, un mosaico de 1024×1024 descomprimido con deflate y predictor 2,
  y una ventana de 100×100 px (1 km²).
  - **B04**: mediana DN 1874, 1,734,403 bytes leídos, 1.89 s.
  - **B08**: mediana DN 2343, 1,711,296 bytes, 1.83 s.
  - **rasterio leyó la misma ventana con las mismas medianas** (1874 y 2343; 1.2 s y 0.6 s).
- Reflectancia: DN × 0.0001 − 0.1 (de `raster:bands`; la baseline 05.12 trae
  `earthsearch:boa_offset_applied: true`). B04 = 0.0874, B08 = 0.1343, **NDVI de las
  medianas = 0.212**. El TCI (`visual`, RGB uint8) también se leyó con rasterio
  (mediana 191, 0.65 s).
- Costo práctico: **~1.7 MB por banda por km²**, porque se baja el mosaico entero
  (10 × 10 km). Un corredor de muchas obras conviene leerlo por mosaico, no por punto.
- Que 10 m distinga etapas de una nave (`docs/13` §2.2) **sigue sin medirse**: esto
  prueba que el píxel llega, no que sirva para eso.

### `cbp.bwt` — CBP Border Wait Times — VIVA
- `GET https://bwt.cbp.gov/api/bwtnew` responde JSON de 134 KB en 0.4–0.8 s, sin clave.
  También están `https://bwt.cbp.gov/xml/bwt.xml`, `api/waittimes` y RSS por puerto
  (`api/bwtRss/rssbyportnum/HTML/POV/230502`).
- El feed trae 85 cruces, 55 de ellos de la frontera con México. **Carril comercial**
  (`commercial_vehicle_lanes`, estándar y FAST) en los cruces pedidos (01:12 UTC):
  - **Laredo – World Trade Bridge** (`230404`): demora 45 min, 10 de 19 carriles
    abiertos, FAST 15 min. Corte "At 7:00 pm CDT".
  - **Laredo – Colombia Solidarity** (`230403`): 20 min, 3 de 8 carriles, FAST 10 min.
  - **Pharr** (`230502`): 5 min, 4 de 7 carriles, FAST 2 min.
  - **Otay Mesa – Commercial** (`250602`): *Lanes Closed*, de 10 carriles.
  - **El Paso – Ysleta** (`240203`, enfrente de Zaragoza): *Lanes Closed*, de 8 carriles.
  - De noche, *Lanes Closed* es un estado del carril, no un hueco del feed.
- **Cada cuándo:** el campo `update_time` es por hora y por cruce. A las 04:52 UTC, WTB y
  Colombia decían "At 11:00 pm CDT" (30 min y 5 min) y Pharr seguía en "At 9:00 pm
  CDT": un cruce puede saltarse horas. El feed se regenera varias veces por hora (el
  XML decía 21:10:38 y el JSON 21:12:20). Son dos lecturas: n < 30, no concluye sobre
  la regularidad.
- **Histórico:** `GET https://bwt.cbp.gov/api/historicalwaittimes/{bwtId}/COV/GEN/{mes}/{día}`.
  El `bwtId` sale de `api/bwtmodern/crossingslist` (WTB = `07230404`) y el día 7 es
  "todos". **No es una serie**: es un promedio por mes × día de la semana × hora, **sin
  año** (`cv_time_avg`, `xcv_time_avg`). En septiembre, WTB tiene 104 filas, con un
  máximo de 59 min (martes a las 19 h). Colombia: 101 filas, máximo 41. Pharr: 94,
  máximo 46. Otay Mesa Commercial: 91, máximo 58. Ysleta: 98, máximo 51.
- Para `docs/13` §5: el pronóstico necesita **una serie propia**, juntada leyendo el feed
  cada hora. El promedio sin año de CBP sirve de base ingenua, no de holdout. Hoy no
  hay serie guardada. Lo que sigue es empezar a juntarla (n ≥ 30 días antes de medir
  nada).

### `compras.ocds_nl` — contrataciones abiertas de Nuevo León (OCDS) — VIVA
- `https://data.open-contracting.org/en/publication/149/download?name=2026.jsonl.gz`
  responde con una redirección a Fastly: 1,684,726 bytes en 2.0 s, sin clave. También hay
  `full`, 2024 y 2025, en jsonl.gz, xlsx y csv.tar.gz. El registro dice "Weekly", con
  descarga mensual del registro.
- **2026**: 4,256 *releases*, con fecha del 2026-01-13 al **2026-09-11** (un mes de
  rezago al medir). Por método: 3,588 adjudicaciones directas, 358 restringidas, 119
  abiertas y 191 sin método. 4,052 traen proveedor y monto adjudicado; 3,024 traen
  `contracts`.
- Campos: `buyer` (dependencia), `tender` (método, título, `numberOfTenderers`,
  `tenderers`, `items`), `awards` (fecha, monto MXN y proveedor con **RFC**) y
  `contracts`. En el ejemplo leído, el contrato venía sin `dateSigned` ni monto.
  **Sin ubicación de la obra**: 0 de 4,256.
- El proveedor puede ser una persona física con su RFC. Eso es dato personal: no se
  publica por persona, igual que con DENUE.
- Origen: `catalogodatos.nl.gob.mx` (CKAN, respondió 200) y `api-ocds.nl.gob.mx`
  (respondió 200, 649 KB por *release* agrupado).
- El Data Registry lista **18 publicaciones de México**. Ninguna es federal y vigente:
  la del INAI va de 2020 a feb-2025 y "ya no se actualiza"; la de QuiénEsQuién.Wiki
  (republica CompraNet), de mar-2022, tampoco.

### `compras.obra_smpu_nl` — obra pública de Movilidad y Planeación Urbana de NL — VIVA
- `catalogodatos.nl.gob.mx/…/contratos_licitacion.csv`: 60,961 bytes en latin-1, con
  columnas `Periodo, Licitacion, Contrato, Obra, Empresa, Ubicacion, Coordenadas, Monto`.
  Viene con su diccionario aparte.
- 179 contratos (2021: 1, 2022: 65, 2023: 53, 2024: 30 y 2025: 30). **Los 179 traen
  coordenadas**: un par o un tramo inicio-fin, por ejemplo `27.423890 -100.000880
  27.689460 -99.779819`. 151 traen ubicación en texto. La suma de montos es MXN
  16,459,820,910. El recurso se modificó por última vez el 2026-06-29.
- Es la única fuente medida con **ubicación de la obra**. Junto con Sentinel-2 permite
  cruzar el contrato con el píxel (`docs/13` §2 y §6). n = 179 de un solo ente: no
  generaliza al país.

### `compras.comprasmx` — ComprasMX / CompraNet federal — MUERTA (para lectura por máquina)
- El portal (`comprasmx.buengobierno.gob.mx/datos-abiertos`) es una SPA de Angular. Los
  documentos se piden a `https://upcp-cnetservicios.buengobierno.gob.mx/amy/comprasmx/portal/documentos`
  con tres cabeceras (`grc`, `igrc`, `xgrc`) que **arma el navegador** (`encryptRequest`).
  Sin ellas responde **403** `{"success":false,"error":"Acceso no permitido."}`.
- El histórico de CompraNet (`historico-compranet.buengobierno.gob.mx`) tiene una descarga
  OCDS (`DOWNLOAD_OCDS_CNET5`) detrás de las mismas cabeceras y de **reCAPTCHA v3**.
  `…/whitney/sitiopublico/` responde 403 igual.
- **No se replicó el mecanismo del navegador ni se esquivó el captcha.** Una descarga
  manual en navegador quizá funcione (no medida). Si el producto §6 la necesita,
  decide el dueño si alguien la baja a mano cada mes.
- `compranet.hacienda.gob.mx` y `contratacionesabiertas.hacienda.gob.mx`: **NO
  CONCLUYE**, porque el proxy rechazó la conexión.

### `pnt.transparencia` — Plataforma Nacional de Transparencia — MUERTA (para lectura por máquina)
- La portada responde 200 (10 de 10) con el User-Agent del script y **403 de Cloudflare**
  (10 de 10) con el de curl. La portada no es dato.
- La consulta pública (`consultapublicamx…/vut-web/`, SIPOT) y el buscador responden
  **403** con una página de captcha (*"verificar que eres humano"*), con cualquier
  User-Agent probado.

### `nasa.firms.csv24h` y `nasa.firms` — FIRMS — VIVA sin clave (CSV) / CON CLAVE (API)
- **Sin clave**: `https://firms.modaps.eosdis.nasa.gov/data/active_fire/{sensor}/csv/{archivo}_Central_America_24h.csv`
  respondió 200 en ~0.3 s. También hay versiones de 48 h y 7 días; la región va de 7.0°
  a 33.5° de latitud y de −115.5° a −58.5° de longitud, y cubre México.
  - **VIIRS S-NPP**: 1,012 focos (83 KB).
  - **VIIRS NOAA-20**: 1,039 focos (87 KB).
  - **VIIRS NOAA-21**: 1,154 focos (97 KB).
  - **MODIS**: 144 focos.
  - **Global de 24 h (S-NPP)**: 6.3 MB.
- Frescura: el archivo NOAA-20 tenía `last-modified` 00:41 UTC y su última adquisición
  era del 2026-10-12 a las 17:11 UTC (unas 8 h antes de medir).
- Valor en NOAA-20: 3 focos a ≤ 50 km de Apodaca (el más cercano a 12.37 km) y 10 de
  Silao (el más cercano a 48.18 km).
- **Con clave**: la API por área sigue en 400 `Invalid MAP_KEY.` con `DEMO_KEY`. **Cómo
  se pide**: en `https://firms.modaps.eosdis.nasa.gov/api/map_key/`, gratis con un
  correo (*"The key will be sent to your email"*). El límite publicado es de **5,000
  transacciones cada 10 minutos**. El script la lee de `FIRMS_MAP_KEY`. Para "incendios
  a ≤ 50 km en 24 h–7 días", el CSV público alcanza sin clave. La API sirve para cajas
  y fechas arbitrarias (histórico).

### Lo que sigue (de esta medición)
1. CBP: juntar la serie propia (lectura horaria del feed) antes de prometer un
   pronóstico. El holdout pide n ≥ 30 días.
2. Medir la **latencia de publicación** de Sentinel-1: cuántas horas pasan entre la
   adquisición y que la escena aparece en el STAC. La revisita ya está medida.
3. Compras federales: el dueño decide si se baja a mano (ComprasMX) o si el producto §6
   arranca con lo estatal que sí se lee (NL).
4. Re-medir desde producción `compranet.hacienda.gob.mx`, `contratacionesabiertas.hacienda.gob.mx`
   y el acceso anónimo al bucket `sentinel-s1-l1c`.

## Medición del 2026-10-21 — WhatsApp coexistencia (Producto 4, D-016)

Paso 2 de `docs/15-agente-a-la-medida.md`, antes de escribir el conector. Lo que se
pudo medir desde aquí es **la documentación oficial y que la Graph API responde**; el
alta de verdad necesita la cuenta de Meta Business de DGED, que es del dueño.

### `meta.whatsapp.coexistencia` — Embedded Signup con la app de WhatsApp Business — NO CONCLUYE (documentación favorable)

- **Desde un servidor**: `graph.facebook.com/v23.0/me` sin token responde **400**
  (responde; pide token). La documentación en markdown
  (`developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users.md`)
  responde 200, 65 KB.
- **Qué exige a DGED**: ser **Tech Provider** (o Solution Partner): verificación del
  negocio en Meta, luego App Review con video de envío de mensajes y manejo de
  plantillas, para tener *Advanced access* a `whatsapp_business_messaging` y
  `whatsapp_business_management`. Embedded Signup con *session logging* y un webhook
  que reciba y procese bien.
- **Qué exige al cliente**: app de WhatsApp Business **2.24.17 o mayor**; escanea el QR
  desde su app, toca "Connect", acepta compartir el historial. Hay **24 horas** para
  sincronizar el historial después del alta, o hay que darlo de baja y repetir.
- **Historial que llega**: webhooks `history` con lo enviado y recibido en los **180
  días** previos al alta, por fases (0: día 0–1; 1: día 1–90; 2: día 90–180) y porciones
  (`chunk_order`, `progress` hasta 100). **Sin grupos.** Los medios llegan como
  `media_placeholder` sin contenido; su id solo si son de los últimos **14 días**. Si el
  negocio no acepta compartir, llega un aviso con el error 2593109.
- **Mensajes nuevos**: `messages` (del cliente final) y `smb_message_echoes` (lo que el
  negocio manda desde su app). Contactos por `smb_app_state_sync`.
- **Límites**: 20 mensajes por segundo fijos; en la app se apagan mensajes temporales,
  "ver una vez", ubicación en vivo y listas de difusión (quedan de solo lectura); los
  dispositivos vinculados se desvinculan (no hay WhatsApp para Windows).
- **Precio**: lo que el negocio manda desde su app sigue gratis; lo que sale por la
  Cloud API paga la tarifa de la Cloud API. La ventana de 24 h solo se abre con
  mensajes que llegan **después** del alta.
- **México**: la página de Meta no publica lista de países. Ninguna de las listas de
  "no soportados" que circulan (UE/RU, Nigeria, Sudáfrica, Australia, Japón, Corea,
  Filipinas, Rusia, Turquía) incluye a México, y un proveedor (Chakra, 2026) lo lista
  con soporte completo. **Fuente de tercero, no de Meta**: no concluye.
- **Veredicto**: NO CONCLUYE hasta que el alta corra con un número mexicano real. El
  conector se escribió contra la forma documentada (`services/agente/agente/historial.py`,
  `canal.py`) y queda **no medido contra Meta**.
- **Para que concluya** (del dueño): verificación de negocio de DGED en Meta, app con
  Embedded Signup y App Review; luego un alta de prueba con el número de la demo y
  contar cuántos mensajes y de qué fechas llegan.
