# Decisiones

Registro corto. Si una decisión de aquí cambia, no se borra: se añade otra línea.

## D-001 — 2026-10-10 — Primer sistema es Atlas, no “la plataforma”

DGED Systems es la empresa. El primer producto cobrable es Atlas: cribado multi-riesgo de sitios industriales. La visión de hardware queda detrás de un cliente que ya use el objeto `Site`.

## D-002 — 2026-10-10 — Un corredor

Se construye `nl-monterrey` como producto que se vende. El mapa de demostración también enseña puntos del Bajío, marcados como segundo corredor, para no fingir que la ingesta nacional ya existe.

## D-003 — 2026-10-10 — El modelo no afirma megawatts

La holgura eléctrica del cribado de escritorio es una clase regional firmada por un analista a partir del PRODESEN. El MVP en vivo no tiene esa clase todavía: `SubestacionAprox` viaja vacío. La frase “MW disponibles en el predio” queda prohibida.

## D-004 — 2026-10-10 — Postgres, no un grafo

La ontología es un contrato JSON más tablas. Un grafo dedicado se reconsidera solo si una consulta real de traversía duele. Hoy las consultas son espaciales, contra el WMS.

## D-005 — 2026-10-10 — El score es código

`packages/score`, versión `atlas-screen-0.1.0`, para features firmados. `services/api/atlas/score.py`, versión `atlas-live-0.1.0`, para lo que las APIs públicas devuelven hoy.

## D-006 — 2026-10-10 — Precio de entrada

Atlas Screening a USD 55,000 (USD 70,000 si DGED construye el universo de predios). Anualidad Operate a USD 96,000. Ver `docs/04-entrega-precios.md`.

## D-007 — 2026-10-10 — El MVP en código es atlas-live, no el score de escritorio

GeoLibre, Mundi, ontograph-core y OpenFoundry no se incrustan: son otros productos, no bibliotecas. El mapa es MapLibre. La ontología mínima vive en `ontology/atlas.ontology.json` y se materializa en cada calificación. DENUE solo entra con `INEGI_TOKEN`.

## D-008 — 2026-10-10 — Municipio por polígono; DENUE y SAKBÉ no rellenan el número

El municipio sale del Catálogo Único (`wscatgeo/v2`), con población del Censo 2020. La ventana DENUE del GeoServer se muestra y no puntúa. Los minutos de SAKBÉ puntúan solo si `SAKBE_TOKEN` devuelve `tiempo_min`.

## D-009 — 2026-10-12 — Cuatro capas sin clave; sismicidad y vía férrea puntúan (atlas-live-0.2.0)

Medidas desde un servidor antes de escribir código. USGS FDSN responde (GeoJSON, <1 s). Open-Meteo archive responde 429 "Daily API request limit exceeded": va al cementerio y el clima sale de NASA POWER, que sí responde. Overpass: `overpass-api.de` corta la conexión, `kumi` da 504, `maps.mail.ru` entrega JSON; el conector prueba los tres en orden.

Entran al número solo si su fuente respondió: sismicidad (magnitud máxima M4+ en 100 km y 50 años) con peso 0.08 y distancia a vía férrea mapeada con 0.10. Los pesos de 0.1.0 se escalan por `1 − suma`; sin esas respuestas el número es idéntico al de 0.1.0. No son compuertas de publicación. Clima y subestación se muestran y no puntúan: el clima de reanálisis repite lo que ya dice la sequía, y una distancia a subestación sin holgura firmada empujaría a leer capacidad donde no la hay (D-003). `SubestacionAprox` se llena con nombre, voltaje del tag y distancia de OSM, y nunca con capacidad.

De paso: el SMN respondió 200 con una página HTML de error en vez de `MunicipiosSequia.xlsx`, se guardaba como libro y tumbaba el arranque. Ahora se rechaza lo que no empieza con `PK`, el API arranca y califica con la sequía ausente: el número existe pero no es publicable (invariante I).
