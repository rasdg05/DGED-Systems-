# Riesgos y mitigación

## Técnicos

| Riesgo | Cómo se ve | Mitigación |
|---|---|---|
| Falsa precisión eléctrica | Alguien lee 73 y cree que hay capacidad | El caveat va en el código, no en un tooltip opcional. `publishable` exige el factor. La UI dice `nearest_substation`, nunca “alimentado por” |
| OSM incompleto o mal etiquetado | Una subestación de distribución parece de transmisión | Sin voltaje ≥115 kV confirmado, el factor eléctrico se capa en 70. El analista puede suprimir un punto |
| Capas que no casan | El punto cae en el municipio vecino por el datum | Todo se guarda en EPSG:4326, el snap usa el marco, y el memo muestra municipio y `cvegeo` |
| Sequía o incidencia atrasadas | El score habla de un año que ya pasó | Cada cifra muestra el corte. Un snapshot de más de 120 días en sequía o incidencia bloquea `publishable` hasta que el analista lo renueve o lo acepte con nota |
| Router de rutas optimista | Minutos de domingo a las 5 am | Se documenta como tiempo libre. No se vende como tiempo de cruce. El escenario `corridor_delay` existe para eso |
| El score se “afina” para que gane el predio que el cliente ya quiere | Deja de ser un instrumento | Los snapshots son inmutables. Un cambio de peso es otra corrida con nombre. Queda el base al lado |

## De negocio

| Riesgo | Mitigación |
|---|---|
| Ciclo de venta largo y el campeón es energía o real estate, no sistemas | Se vende el memo. El software es como se produce el siguiente trimestre |
| Scope de “Palantir” | [01-mvp.md](01-mvp.md) es la lista de no. Una petición fuera de esa lista se cotiza como fase 2 o se rechaza |
| Colliers/AMPIP ya venden el mapa industrial | No vendemos inventario ni absorción. Vendemos la decisión bajo supuestos. Si el prospecto quiere metros disponibles, se le manda con ellos |
| Un error público en un predio conocido | Los primeros diez sitios los revisa alguien que haya trabajado parque en NL antes de usarlos como demo |
| Datos personales o republicación de DENUE | Solo agregados municipales en el producto. El crudo se queda en el bucket de ingesta, sin URL pública |
| Lenguaje de seguridad | Revisión de las frases del memo antes del primer cliente. “Contexto municipal” es el techo |
| Depender de un solo corredor | Es el plan, no un accidente. El segundo corredor se abre cuando un cliente lo pague, no cuando el mapa se vea vacío |
| Hardware demasiado pronto | Prohibido en el presupuesto de las primeras 12 semanas. Un render de dron no entra al deck de ventas del piloto |

## Legal y de palabra

Atlas es apoyo a la decisión. El contrato del piloto lo dice en una cláusula: no sustituye el estudio de interconexión, la concesión de agua, la manifestación de impacto ambiental ni un dictamen de seguridad. El memo repite esa frase en castellano llano, no solo en el contrato.

No se toma posición política sobre incidencia delictiva. El percentil se muestra o no se muestra. No se escribe “zona controlada por”.

## Riesgo de ejecución

Un solo equipo no ingiere siete fuentes y diseña una marca al mismo tiempo. El orden del [plan de 12 semanas](07-plan-12-semanas.md) es el mitigante: primero el score y la energía, después el mapa. Un mapa bonito sin holgura PRODESEN firmada no se enseña.
