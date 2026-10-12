# Fuentes de datos

Principio: si no se puede citar la extracción, no entra al score. La resolución se guarda siempre (`site`, `park`, `municipality`, `aquifer`, `region`). Mezclarlas sin decirlo es el defecto que el producto existe para evitar.

## MVP — se integran en las 12 semanas

| Clave | Fuente | Qué se saca | Resolución | Licencia / cuidado |
|---|---|---|---|---|
| `inegi.marco` | Marco Geoestadístico INEGI | Municipios del corredor, claves `cvegeo` | municipio | Uso público INEGI. Guardar la edición (2020/2024) |
| `inegi.denue` | DENUE | Unidades económicas manufactureras por municipio, como masa relativa | municipio | No republicar el microdato. Solo agregados |
| `inegi.rnc` | Red Nacional de Caminos | Grafo para tiempo de manejo si no hay router externo | tramo | Citar edición |
| `inegi.usv` | Uso de suelo y vegetación, serie vigente | Máscara industrial / urbana en el punto | sitio (clase de polígono) | Citar serie |
| `inegi.cem` | Continuo de Elevaciones | Pendiente media en 300 m | sitio | No es un estudio geotécnico |
| `osm.power` | OpenStreetMap vía Geofabrik, `power=substation` y `power=line` | Candidatos a subestación y línea, voltaje si viene etiquetado | sitio (distancia) | ODbL. El dato está incompleto. `voltage_known=false` es el caso normal |
| `osm.rail` | OSM `railway` | ¿Hay vía a ≤5 km? | sitio | Misma salvedad |
| `conagua.acuiferos` | Disponibilidad de acuíferos publicada por CONAGUA (DOF / SIG) | `deficit` / `equilibrium` / `surplus` | acuífero | Citar el acuerdo de disponibilidad, no “CONAGUA” a secas |
| `conagua.sequia` | Monitor de Sequía de México (SMN/CONAGUA) | % del municipio en D2–D4 en el corte más reciente | municipio | Mensual. Guardar el corte |
| `cenapred.inundacion` | Atlas Nacional de Riesgos, peligro por inundación | Clase máxima que toca un buffer de 500 m | sitio | Descargar la capa, no scrapear el visor cada request |
| `cfe.sismico` | Regionalización sísmica CFE | Zona A/B/C/D del punto | sitio | NL cae casi todo en zona baja. El factor no debe dominar |
| `cenapred.laderas` | Susceptibilidad de laderas | Bandera alta sí/no | sitio | Binaria a propósito |
| `sener.prodesen` | PRODESEN vigente (edición 2025-2039 y la que la sustituya) | Clase manual de holgura de la región de transmisión Noreste: `open`, `moderate`, `tight`, `constrained` | región | No es un dato geográfico fino. Lo asigna el analista leyendo el capítulo de transmisión y lo firma en `evidence` |
| `ampip.parques` | Directorio y comunicados AMPIP + ficha pública del desarrollador | Nombre, desarrollador, municipio, hectáreas si están publicadas | parque | Muchas geometrías habrá que digitalizarlas a mano. No comprar el mapa Colliers para revenderlo |
| `sesnsp.incidencia` | Incidencia delictiva del fuero común, municipal | Percentil de robo de vehículo y, donde exista corte útil, delitos contra el transporte. 100 = menor incidencia | municipio | Lenguaje de producto: “contexto municipal”. Prohibido “sitio peligroso” |
| `imss.asegurados` | Datos abiertos IMSS, asegurados por municipio | Percentil de masa laboral, idealmente sector transformación | municipio | Agregado |
| `ruta.ors` | Router sobre la RNC o un servicio OSRM propio | Minutos a Puente Colombia y al puerto de Altamira | sitio | Altamira es el puerto de referencia del corredor. Manzanillo se reporta como nota, no como score, porque castiga a todo NL por igual y no rankea |

### Reglas de la holgura eléctrica

PRODESEN no trae “MW libres en este lote”. El MVP usa cuatro clases regionales, escritas por un humano:

- `open` — la región tiene obra de transmisión relevante ya en marcha y no es el cuello que el propio plan destaca.
- `moderate` — cabe carga media con obra local probable.
- `tight` — el plan o la prensa técnica de CFE describe saturación o obras que no entran en el horizonte de una nave (24 meses).
- `constrained` — apagones, diferimiento o negativa documentada en la zona.

La clase es una sola para todo el corredor en v1 si no hay base para partirla. Partirla por municipio sin evidencia es falsa precisión. El analista puede sobreescribir **un sitio** con una nota y una cita (oficio, minuta, nota de inversionistas de CFE); eso baja a resolución `site` y `confidence=verified`.

OSM no se “corrige” en silencio. Una subestación falsa se marca `suppressed` con nota. Sigue en la base.

## Después del MVP — solo con presupuesto de un piloto

| Fuente | Para qué | Bloqueo |
|---|---|---|
| Estudio de interconexión del cliente | Objeto `InterconnectionCase`, pisa la holgura regional en ese sitio | Lo tiene que entregar el cliente. No se promete conseguirlo |
| Concesión o constancia de CONAGUA del parque | Igual, pisa el acuífero en ese sitio | Documento del cliente |
| Cola y precios nodales CENACE | Módulo energético de verdad | Licencia y otro modelo. No se mete al score 0.1 |
| Sentinel-2 (Planetary Computer) | Figura de cambio de suelo en el memo | No entra al número |
| ENOE / DataMéxico | Salarios y empleo exportador como contexto del memo | Agregado estatal, no rankea lotes |
| Robo a transportista por tramo (fiscalías, aseguradoras) | Seguridad de ruta, que es lo que el logístico compra | No hay capa nacional abierta y estable |
| SCADA, medidores, sensores del parque | Fase 3, evidencia `verified` | Sin cliente operando no hay señal |

## Corredor 2, cuando exista

El Bajío (Querétaro–Guanajuato) repite el mismo esquema: otros minutos (León no compite por Colombia; compite por puerto y por ferrocarril), otra clase PRODESEN, otros acuíferos. No se reescriben los factores. Se cambian los parámetros de referencia de ruta.

Juárez y Tijuana son otro producto de seguridad y de cruce. No se venden con este score sin recalibrar `security` y `logistics`.
