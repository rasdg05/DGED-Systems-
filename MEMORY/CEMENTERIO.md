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
