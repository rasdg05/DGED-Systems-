# DGED Atlas

Cribado multi-riesgo de sitios industriales en el norte y el Bajío. No es un gemelo de Palantir ni un dictamen de interconexión: es un mapa, una ontología chica y un número que solo existe si INEGI y CONAGUA respondieron.

## Qué hace

1. Diez puntos candidatos (cinco en el norte, cinco en el Bajío).
2. En cada punto ubica el municipio con el polígono del Catálogo Único de INEGI (marco de diciembre de 2025, población del Censo 2020). Si el polígono no carga, cae al pixel del WMS.
3. Pregunta al WMS de INEGI el uso de suelo serie VII y si el punto cae en una capa de inundación.
4. Cruza la clave geoestadística con el [Monitor de Sequía](https://smn.conagua.gob.mx/es/climatologia/monitor-de-sequia/monitor-de-sequia-en-mexico).
5. Muestra manufactura de la ventana DENUE en el GeoServer. Eso es evidencia, no un conteo, y no entra al número. El conteo de 1.5 km entra solo con `INEGI_TOKEN`.
6. La ruta a Puente Colombia (norte) o al puerto de Altamira (Bajío) entra solo con `SAKBE_TOKEN`. Sin clave el factor se ve y no mueve el número.
7. Sin clave (D-009): sismos M4+ en 100 km y 50 años (USGS FDSN), lluvia anual y días arriba de 35 °C de los últimos cinco años (NASA POWER), la subestación pública mapeada más cercana con su voltaje y la distancia a la vía férrea mapeada (OSM Overpass). Sismicidad y vía férrea puntúan solo si respondieron; clima y subestación se muestran y no puntúan.
8. Devuelve una viabilidad 0–100, el riesgo complementario y los objetos ligados.
9. El mapa enciende las capas del WMS como tiles, por un proxy de este servicio.

## Arranque con Docker

Hace falta Docker con Compose v2. La primera vez baja PostGIS, el libro de sequía (~2 MB) y los polígonos de cinco estados (~8 MB). En una red normal queda abajo de 40 minutos; el cuello es la imagen de PostGIS, no el código.

```bash
cp .env.example .env
# opcional: INEGI_TOKEN y SAKBE_TOKEN
docker compose up --build
```

Abre `http://localhost:8080`.

Postgres queda en el puerto 5432 (`atlas` / `atlas`, base `atlas`) con PostGIS y la tabla `atlas_score`. Cada calificación se guarda ahí. Si Postgres no está, el API sigue en memoria.

## Arranque sin Docker

```bash
cd services/api
python3 -m pip install -r requirements.txt
export INEGI_TOKEN=
export SAKBE_TOKEN=
python3 -m uvicorn atlas.main:app --host 0.0.0.0 --port 8080
```

Prueba del modelo, sin red:

```bash
python3 services/api/test_score.py
```

## Arquitectura

```text
mapa (MapLibre GL 5.6.1)
    │  tiles /api/wms/{capa}/{z}/{x}/{y}.png
    ▼
FastAPI  ── polígono ──► Catálogo Único INEGI  wscatgeo/v2
         ── GetFeatureInfo ──► WMS INEGI (suelo, inundación)
         ── xlsx oficial    ──► SMN / CONAGUA  MunicipiosSequia.xlsx
         ── ventana         ──► GeoServer DENUE industrias manufactureras
         ── REST            ──► DENUE conteo, solo con INEGI_TOKEN
         ── POST            ──► SAKBÉ optima, solo con SAKBE_TOKEN
         ── FDSN            ──► USGS sismos M4+, sin clave
         ── diario          ──► NASA POWER lluvia y Tmax, sin clave
         ── Overpass        ──► OSM subestación y vía férrea, sin clave
         └─ score atlas-live-0.2.0
```

La ontología está en [ontology/atlas.ontology.json](ontology/atlas.ontology.json). El esquema espacial de largo plazo sigue en [ontology/001_init.sql](ontology/001_init.sql). Lo que Compose crea al nacer la base es [ontology/010_runtime.sql](ontology/010_runtime.sql).

El mapa es MapLibre. La ontología es un contrato JSON de object types, link types y una acción, materializado en cada calificación.

## API

| Método | Ruta | |
|---|---|---|
| GET | `/api/health` | filas de sequía y corte |
| GET | `/api/sources` | estado de cada fuente en el arranque |
| GET | `/api/ontology` | contrato |
| GET | `/api/sites?corridor=norte` | candidatos |
| POST | `/api/sites/{id}/score?drought_year=true` | consulta real y score |
| GET | `/api/sites/{id}` | ficha y grafo si ya se calificó |
| GET | `/api/examples` | URLs que el proceso acaba de consultar |
| GET | `/api/wms/uso_suelo/{z}/{x}/{y}.png` | tile INEGI |

`drought_year=true` no cambia el dato observado. Si el municipio está en NONE, D0 o D1, el escenario usa D2 y lo dice en `raw.used`.

## Cómo se calcula

Solo entran factores con respuesta. Sin claves: sequía 0.40, inundación 0.30, uso de suelo 0.30. Con conteo DENUE: 0.34 / 0.24 / 0.18 / 0.24. Con ruta SAKBÉ: 0.32 / 0.24 / 0.22 / 0.22. Con ambos: 0.28 / 0.20 / 0.16 / 0.18 / 0.18.

Versión `atlas-live-0.2.0` (D-009). Sobre esa tabla, si USGS respondió entra sismicidad con **0.08** y si Overpass respondió entra vía férrea con **0.10**; los demás pesos se multiplican por `1 − (suma de los que entraron)` (0.92, 0.90 o 0.82). Ejemplo sin claves y con las dos capas: sequía 0.328, inundación 0.246, uso de suelo 0.246, sismicidad 0.08, vía férrea 0.10. Sin respuesta de USGS ni de Overpass los pesos y el número son exactamente los de 0.1.0. Los pesos suman 1 en las 16 combinaciones (`test_capas.py`). Las capas nuevas no deciden si se publica: eso sigue siendo sequía, inundación y uso de suelo.

| Factor | Dato | Puntaje |
|---|---|---|
| Sequía | categoría del último corte municipal con dato | NONE 92, D0 78, D1 62, D2 46, D3 28, D4 12 |
| Inundación | el punto cae en `c463` o, si no, en `c424` | sin polígono 84, con polígono 22 |
| Uso de suelo | serie VII, `c783` | industrial 88, asentamiento 70, agro 52, bosque o agua 34, otra clase 48 |
| DENUE conteo | `manufactura` a 1.5 km, solo con `INEGI_TOKEN` | 0 → 30, 1–5 → 55, 6–20 → 75, más de 20 → 90 |
| DENUE ventana | GetFeatureInfo de manufactureras | no puntúa; se muestra |
| Ruta | minutos SAKBÉ en automóvil, solo con `SAKBE_TOKEN` | ≤45 → 88, ≤90 → 72, ≤150 → 54, ≤240 → 36, más → 20 |
| Sismicidad | magnitud máxima USGS M4+ en 100 km, 50 años | ninguno 90, <4.5 → 82, <5.0 → 76, <5.5 → 62, <6.0 → 46, <6.5 → 30, más → 16 |
| Vía férrea | km en línea recta a `railway=rail` en OSM | ≤2 → 88, ≤5 → 74, ≤10 → 56, nada mapeado en 10 km → 36 |
| Clima | lluvia media anual y días > 35 °C, NASA POWER 5 años | no puntúa; se muestra |
| Subestación | la pública mapeada más cercana en OSM en 25 km, voltaje del tag | no puntúa; se muestra |

Es publicable solo si sequía, inundación y uso de suelo respondieron. Un 78 no significa agua disponible ni un predio a salvo.

`SubestacionAprox` se llena desde OpenStreetMap: nombre, voltaje del tag (null si no lo trae), distancia en línea recta y `source: osm`. Se omiten las de planta (`substation=industrial`). OSM puede estar incompleto. Nunca dice cuánta carga se puede conectar: no hay API pública de eso por lote (D-003).

## Fuentes y límites

- **Catálogo Único** `https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/{entidad}`. Atlas carga Coahuila, Guanajuato, Nuevo León, Querétaro y San Luis Potosí.
- **INEGI WMS** `https://gaia.inegi.org.mx/NLB/tunnel/wms/wms61`. Capas `c783` serie VII, `c463` y `c424` inundación. El municipio por pixel queda solo como respaldo.
- **DENUE conteo** exige clave. Sin ella responde `No Autorizado`.
- **DENUE ventana** GeoServer `denue:industrias_manufactureras`. Nombre, actividad y rango de personal. No se guardan teléfono ni correo. No es el universo del radio.
- **SAKBÉ** `POST https://gaia.inegi.org.mx/sakbe_v3.1/optima`. La clave se pide en [genera_token.jsp](https://gaia.inegi.org.mx/sakbe_v3.1/genera_token.jsp). Referencias: Puente Colombia y Puerto de Altamira. La ruta une líneas de la red, no el portón.
- **SMN/CONAGUA** `MunicipiosSequia.xlsx`. Si la última quincena viene vacía, se usa la anterior que sí trae categoría y la ficha muestra esa fecha.
- **ArcGIS** `https://sigagis.conagua.gob.mx/ArcGIS/rest/services` hoy entra en redirección y no suelta JSON.
- **datos.gob.mx** el API CKAN a veces responde 403 desde un centro de datos. No hay paquete sustituto.
- **USGS FDSN** `https://earthquake.usgs.gov/fdsnws/event/1/query`. GeoJSON, sin clave. Catálogo registrado, no la regionalización sísmica de CFE; el M4 de antes de los noventa está incompleto en México.
- **NASA POWER** `https://power.larc.nasa.gov/api/temporal/daily/point` (`PRECTOTCORR`, `T2M_MAX`). Celda MERRA-2 de ~0.5°, no una estación. Reemplaza a Open-Meteo, que desde un servidor responde 429 por cuota diaria (cementerio).
- **OSM Overpass** se prueban en orden `overpass-api.de`, `maps.mail.ru/osm/tools/overpass` y `overpass.kumi.systems`; la ficha dice cuál contestó. Tarda de 10 a 50 s y a veces da 504.
- Los diez puntos son candidatos para la demo, no polígonos oficiales de parque ni una recomendación de inversión.

## Qué sigue

Clase de holgura eléctrica firmada contra el PRODESEN, por corredor. Después, el oficio de interconexión del cliente como objeto que pisa esa clase.
