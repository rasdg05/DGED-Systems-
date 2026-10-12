# Stack

Elegido para que una persona pueda operarlo y para que dentro de dos años el `Site` siga siendo el mismo objeto. No para parecer una plataforma de defensa.

## Ahora

| Capa | Elección | Por qué | No |
|---|---|---|---|
| Sistema de registro | Postgres 16 + PostGIS 3 | Los objetos son filas con geometría y evidencia. Las consultas del MVP son puntos en polígonos y distancias | Neo4j, un triple store, “ontology server” |
| Motor de score | TypeScript plano en `packages/score` | Misma librería en el job y en un test. Cero framework | Notebook como producción |
| Ingesta | Python 3.12, GeoPandas, un script por fuente | Los shapefiles de INEGI y CENAPRED viven aquí | Spark, Airflow, un “data OS” |
| Archivos crudos | Bucket S3-compatible (R2 o S3), un prefijo por snapshot | Inmutables | Disco de una laptop |
| API | La misma app, server functions o un módulo pequeño. No hay segundo servicio hasta que el job de ingesta estorbe | Menos deploy | Microservicios |
| Mapa | MapLibre GL + una fuente vectorial del corredor (Martin o PMTiles) | No se paga un mapa de negocio por tile | Google Maps como base de la decisión |
| App | TypeScript, React | El producto es una ficha y una lista; el mapa es el tercer panel | Un visor GIS de escritorio como entrega |
| Auth | Nada en el piloto interno. Cuando haya cliente: un proveedor aburrido (correo mágico o SSO del cliente) sobre la app | El segundo cliente concurrente | Construir auth propio |
| Host | Una app y un Postgres administrado (Neon, RDS o equivalente) | Alcanza para 12 sitios y también para 400 | Kubernetes |
| CI | `node --test` del score en cada push | Es el único módulo que no tiene derecho a romperse en silencio | — |
| PDF | HTML imprimible | Una plantilla | LaTeX, un generador de marcas |

## Contratos que no se negocian al cambiar de framework

- Los nombres de features de [03-ontologia.md](03-ontologia.md).
- `scoreSite(features, { weights, scenario })` devuelve `composite`, `coverage`, `publishable`, `factors[]` con `caveats`.
- Los `score_snapshot` no se actualizan. Se insertan.
- La geometría de intercambio es GeoJSON WGS84.

## Qué se añade en fase 2, y solo entonces

- Cola de jobs (pg-boss alcanza) cuando el refresco trimestral deje de ser un comando.
- Objetos `Asset` e `InterconnectionCase`.
- Lectura de un PDF de interconexión como evidencia ligada, no como texto suelto en un chat.
- Segundo corredor como datos, no como fork del código.

## Qué no se añade aunque sobre tiempo

Kafka, un feature store genérico, un LLM en el camino del número, una app móvil, un visor 3D del teseracto, tiles satelitales como capa default.

El símbolo de la empresa puede vivir en el memo y en la portada. No es una capa del mapa.
