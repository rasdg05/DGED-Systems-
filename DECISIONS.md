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

## D-010 — 2026-10-12 — El Oráculo contesta con herramientas del Atlas, no de memoria

`POST /api/oracle` (`services/api/atlas/oracle.py`): ciclo de tool use con el SDK oficial `anthropic` (1.13.0), modelo `claude-opus-5-5` por defecto (`ATLAS_ORACLE_MODEL` lo cambia, con ID completo), esfuerzo `medium` y fallback del servidor (`fallbacks: "default"`) ante un rechazo. Seis herramientas que llaman a las mismas funciones de la API: listar, calificar (la de `POST /api/sites/{id}/score`), ficha/grafo, ontología, fuentes y comparar. Tope de 8 pasos; agotado, el modelo solo puede contestar (`tool_choice: none`). Candados escritos por el sistema, no pedidos al modelo: toda cifra de la respuesta debe aparecer en un resultado de herramienta de esa conversación o se retira y se reporta en `unverified`; una oración que afirme megawatts o capacidad eléctrica se quita (D-003); fuentes (URLs devueltas) y factores ausentes se agregan al final. Dormido por defecto: sin `ANTHROPIC_API_KEY`, 503. Tests sin red ni clave en `services/api/test_oracle.py`.

## D-011 — 2026-10-12 — Atlas Comparativo a USD 15,000

Aprobado por el dueño. Dos o tres predios con fecha de decisión, escenarios y memo. Se acredita completo contra un Atlas Screening firmado dentro de 90 días. Es la puerta de entrada; el Screening (D-006) sigue siendo el destino. No se vende antes de medir las fuentes en vivo. Detalle en `docs/09-portafolio-90-dias.md` (P2).

## D-012 — 2026-10-12 — Tres primeras cuentas y cómo se despliega

Fibra Mty, FIBRA Prologis y Vesta, por evidencia pública de compra en curso (`docs/09-portafolio-90-dias.md` §3). AMPIP es canal después del primer memo. Despliegue en Railway: demo pública de solo lectura, espacio de cliente con llave y trabajo de fondo. El Oráculo no abre sin `ATLAS_ACCESS_TOKEN` (`services/api/atlas/access.py`). Plan en `docs/10-plan-30-dias.md`.
