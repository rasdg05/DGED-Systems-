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
