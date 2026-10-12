# Ontología Atlas 0.1

El modelo completo está en [ontology/001_init.sql](../ontology/001_init.sql). Esto es el contrato que el SQL no explica solo.

## Objetos

| Tipo | Identidad | Geometría | Notas |
|---|---|---|---|
| `corridor` | `nl-monterrey` | multipolígono | El recorte comercial. No es un estado |
| `municipality` | `cvegeo` | multipolígono | Del marco. No se dibuja a mano |
| `industrial_park` | uuid | multipolígono nullable | Si no hay polígono, no se finge. Hay un punto y `geom_quality=point` |
| `site` | uuid | punto, o polígono de lote si el cliente lo da | El objeto que se rankea. `status`: `candidate`, `shortlisted`, `rejected`, `operating` |
| `substation` | uuid | punto | `source=osm\|manual`, `voltage_known` |
| `aquifer` | clave CONAGUA | multipolígono | `status`: `deficit`, `equilibrium`, `surplus`, `unknown` |
| `evidence` | uuid | ninguna | Cuelga de cualquier cifra |
| `dataset_snapshot` | texto (`osm.power.2026-10-10`) | ninguna | Inmutable |
| `site_feature_snapshot` | uuid | ninguna | JSON de features de un sitio contra un snapshot |
| `scenario` | uuid | ninguna | `load_mw`, `drought_year`, `corridor_delay` |
| `score_snapshot` | uuid | ninguna | Inmutable. Cambió el modelo → fila nueva, no update |
| `analyst_note` | uuid | ninguna | La corrección humana |
| `portfolio` | uuid | ninguna | El conjunto de sitios de un encargo |
| `link` | uuid | ninguna | Arista tipada |

No hay objeto `Risk`. El riesgo es un factor del score o una capa. Un objeto llamado Riesgo se llena de adjetivos y deja de ser consultable.

No hay objeto `Asset` en v1. Una nave que ya opera entra en fase 2, cuando haya algo que medir dentro del predio.

## Aristas (`link.rel`)

| rel | De | A | Confianza típica |
|---|---|---|---|
| `located_in` | site | municipality | alta, por punto en polígono |
| `within` | site | corridor | alta |
| `contains` | industrial_park | site | alta si el punto cae en el polígono; si no, no se inventa |
| `nearest_substation` | site | substation | baja si el voltaje no viene. Es el mínimo distancia, no la subestación que lo va a alimentar |
| `draws_from` | site | aquifer | media. El acuífero del punto no es la fuente de la toma municipal |
| `referenced_by` | score_snapshot | evidence | alta |

`nearest_substation` se llama así y no `served_by`. `served_by` sería una mentira.

## Features que el score sabe leer

Nombres estables. El pipeline los escribe así y `packages/score` los consume así.

| Campo | Tipo | Null si |
|---|---|---|
| `distSubstationKm` | number | no hay subestación en 40 km |
| `voltageKnown` | boolean | — |
| `voltageKv` | number \| null | la etiqueta OSM no trae voltaje |
| `headroom` | `open\|moderate\|tight\|constrained` | nadie firmó la clase PRODESEN |
| `aquiferStatus` | `surplus\|equilibrium\|deficit\|unknown` | el punto no cae en un acuífero publicado |
| `droughtD2PlusPct` | 0–100 | no hay corte del monitor |
| `minutesToBorder` | number | falló el router |
| `minutesToPort` | number | falló el router |
| `railWithin5Km` | boolean | — |
| `laborMarketPercentile` | 0–100, 100 = más masa | sin IMSS/DENUE |
| `floodClass` | `none\|low\|medium\|high\|very_high` | sin capa |
| `seismicZone` | `A\|B\|C\|D` | sin zona. En este país la zona A es la de **menor** peligro |
| `landslideHigh` | boolean | — |
| `safetyPercentile` | 0–100, 100 = menor incidencia | sin SESNSP |

## Pesos por defecto

Pensados para un fabricante que se instala, no para un último-milla urbano.

| Factor | Peso |
|---|---|
| power | 0.28 |
| logistics | 0.20 |
| water | 0.18 |
| labor | 0.12 |
| climate | 0.12 |
| security | 0.10 |

El cliente puede pedir otros pesos. Se guardan en el `score_snapshot`. El default no se edita “un poco” en producción: o es el default o es un escenario de pesos con nombre.

## Publicable

`publishable = composite != null && coverage >= 0.75 && power.score != null`.

Cobertura = peso de los factores presentes / peso total. Un memo con `publishable=false` puede existir como borrador interno. No sale al cliente.

## Provenance mínima de una cifra en pantalla

Cada factor muestra:

1. El número 0–100.
2. El raw que lo produjo (`4.1 km`, `tight`, `D2+ 38%`).
3. La frase de caveat que ya devuelve el código. No se reescribe en el frontend para que suene más segura.
4. El `dataset_snapshot` y la fecha.

## Versionado

- `MODEL_VERSION` en código. Hoy `atlas-screen-0.1.0`.
- Cambiar una banda o un peso default sube el patch y obliga a un `score_snapshot` nuevo.
- Los snapshots viejos no se recalculan solos. El memo cita la versión.
