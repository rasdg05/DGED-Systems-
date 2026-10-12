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
