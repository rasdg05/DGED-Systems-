# Cementerio — medido y descartado

> Antes de proponer una fuente o componente, búscalo aquí. Append-only: si algo
> revive, se agrega una entrada nueva con la evidencia, no se borra la vieja.

## Fuentes

### CONAGUA ArcGIS REST — 2026-10-10
- `https://sigagis.conagua.gob.mx/ArcGIS/rest/services` entra en redirección y
  no devuelve JSON.
- Reemplazo: `MunicipiosSequia.xlsx` del SMN.
- Revivir solo si responde JSON desde un servidor, dos días seguidos.

### datos.gob.mx (API CKAN) — 2026-10-10
- Responde 403 a veces desde un centro de datos. No hay paquete sustituto.

### DENUE como conteo sin clave — 2026-10-10
- Sin `INEGI_TOKEN` responde `No Autorizado`. La ventana del GeoServer no es
  el universo del radio: se muestra y no puntúa (D-008).

### Open-Meteo archive (clima histórico) — 2026-10-12
- `archive-api.open-meteo.com/v1/archive` (y `historical-forecast-api`, `climate-api`)
  responden 429 `Daily API request limit exceeded` desde el servidor, incluso con
  una consulta de cinco días: la cuota es por IP compartida. `api.open-meteo.com`
  (pronóstico) sí responde, pero no trae cinco años.
- Reemplazo: NASA POWER diario (`PRECTOTCORR`, `T2M_MAX`), sin clave (D-009).
- Revivir solo con plan pagado con clave, o si responde 200 desde un servidor dos días seguidos.

### Overpass `overpass-api.de` y `overpass.kumi.systems` como única instancia — 2026-10-12
- `overpass-api.de`: connection reset en cada intento (también `/api/status`, `lz4.` y `z.`).
- `overpass.kumi.systems`: 504 "server is probably too busy" o se agota a los 50 s.
- `overpass.osm.jp`: certificado vencido. `overpass.private.coffee`: se agota.
- Sigue en la lista de `osm.ENDPOINTS` porque la caída puede ser de esta red; la
  que contestó fue `maps.mail.ru/osm/tools/overpass` (10–50 s, 504 a ratos).

## Componentes

### GeoLibre, Mundi.ai, ontograph-core, OpenFoundry — 2026-10-10
- Pedidos en el brief original. No se incrustan: son productos, no bibliotecas
  (D-007). El mapa es MapLibre; la ontología es JSON + tablas (D-004).
- Revivir uno si resuelve una consulta real que hoy duela, no por el nombre.

## Ideas

### "Plataforma tipo Palantir" como primer entregable — 2026-10-10
- Murió en D-001: el primer sistema es Atlas, un corredor, cobrable.

### Megawatts disponibles por predio — 2026-10-10
- No hay API pública de capacidad por lote. Afirmarlo es inventar (D-003).

## Fuentes — medición del 2026-10-12 (`MEMORY/FUENTES.md`)

### SMN webservices, pronóstico por municipio — 2026-10-12
- `https://smn.conagua.gob.mx/webservices/?method=1`: 0 de 30 intentos seguidos
  (y ~40 sueltos) con dato. Responde **HTTP 200 con la página de error del WAF**
  (730 B, "This page can't be displayed"), con cualquier User-Agent.
- Revivir solo si devuelve el gzip de JSON desde un servidor en 30 de 30 intentos,
  dos días seguidos.

### CONAGUA ArcGIS REST — 2026-10-12 (re-confirmada)
- `sigagis.conagua.gob.mx/ArcGIS/rest/services?f=pjson`: 302 a "Loading" con curl,
  403 con `urllib`. Sigue sin JSON. La entrada del 2026-10-10 sigue en pie.

### datos.gob.mx (API CKAN) — 2026-10-12 (re-confirmada)
- `package_search?q=acuiferos`: 403 `Access Denied` en 3 de 3 desde un centro de
  datos. El "a veces" del 2026-10-10 hoy fue siempre.

### Open-Meteo API gratuita en producción — 2026-10-12
- No está muerta: responde. Se entierra **la idea de usar la API gratuita en Atlas**.
  Sus términos dicen "You may only use the free API services for non-commercial
  purposes", y desde una IP compartida el archivo histórico dio 429 ("Daily API
  request limit exceeded") en todos los intentos.
- Revivir con plan de pago o con una instancia propia (código abierto). Lo decide
  el dueño.

## Fuentes — medición del 2026-10-13 (`MEMORY/FUENTES.md`)

### ComprasMX / CompraNet federal como fuente legible por máquina — 2026-10-13
- `upcp-cnetservicios.buengobierno.gob.mx/amy/comprasmx/portal/documentos` responde
  **403** `"Acceso no permitido."` sin las cabeceras `grc`/`igrc`/`xgrc` que arma el
  navegador. La descarga OCDS del histórico (`historico-compranet.buengobierno.gob.mx`)
  está detrás de lo mismo y de reCAPTCHA v3. No se replica ni se esquiva.
- Reemplazo medido: OCDS de Nuevo León (`data.open-contracting.org/en/publication/149`)
  y el CSV de obra pública de la SMPU de NL, los dos VIVA y estatales.
- Revivir si publica descarga directa (archivo o API sin captcha) que responda desde un
  servidor dos días seguidos.

### Plataforma Nacional de Transparencia (consulta SIPOT) — 2026-10-13
- `consultapublicamx.plataformadetransparencia.org.mx/vut-web/` y el buscador responden
  **403** con captcha ("verificar que eres humano"). La portada responde 200 con un
  User-Agent y 403 de Cloudflare con el de curl. La portada no es dato.
- Revivir si la consulta o una descarga masiva responde sin captcha desde un servidor.

## Agente a la medida — probado y no (2026-10-27, `services/agente/vara/intentos.jsonl`)

### Respuestas guardadas sacadas del historial como capa sin modelo — 2026-10-27
- Perfil del enjambre (285 renglones citados, 48 preguntas frecuentes) sobre Finca Emiliano:
  acierto literal **0.4%** en desarrollo con el perfil purgado por plática (1.4% sin purga:
  la guardada "acertaba" con la respuesta de su propio momento) y 0.4% en el holdout.
  DSR 0.0 contra pasar todo a una persona. n = 498 dev, 251 holdout.
- Revivir con preguntas frecuentes escritas por el dueño (no sacadas de pláticas sueltas)
  y medidas en el holdout siguiente.

### Redacción sin cotizador capaz — 2026-10-27
- El enjambre redactó 60 momentos de desarrollo con el perfil: puntaje 0.28 contra 0.30
  de la línea base (DSR 0.0); 41 de 60 terminan en una persona (cotizar, disponibilidad,
  candados). Sin la lista de precios ni el calendario, redactar mejor no mueve la vara.
- Revivir cuando exista la lista de precios del dueño y el cotizador elija propiedad por grupo.

### Cotizar cuando el cliente da los datos que la casa pidió — 2026-10-27
- grupo-3 en la bitácora: si la bienvenida o "¿Qué fecha?" pidió fechas y personas y el cliente
  las dio, el cotizador daba precio. Puntaje 0.289 contra 0.300 de la línea base en desarrollo
  (n = 498): la casa contesta eso con fotos y presentación (41 momentos de `fotos` recibieron
  una cifra). Se queda solo "pidió precio" (o da el grupo tras pedirlo y no recibirlo).
- Revivir si el dueño decide mandar precio junto con las fotos, y medir en el holdout siguiente.
