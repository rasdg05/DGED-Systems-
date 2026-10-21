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

## D-010 — 2026-10-12 — El Oráculo contesta con herramientas del Atlas, no de memoria

`POST /api/oracle` (`services/api/atlas/oracle.py`): ciclo de tool use con el SDK oficial `anthropic` (1.13.0), modelo `claude-opus-5-5` por defecto (`ATLAS_ORACLE_MODEL` lo cambia, con ID completo), esfuerzo `medium` y fallback del servidor (`fallbacks: "default"`) ante un rechazo. Seis herramientas que llaman a las mismas funciones de la API: listar, calificar (la de `POST /api/sites/{id}/score`), ficha/grafo, ontología, fuentes y comparar. Tope de 8 pasos; agotado, el modelo solo puede contestar (`tool_choice: none`). Candados escritos por el sistema, no pedidos al modelo: toda cifra de la respuesta debe aparecer en un resultado de herramienta de esa conversación o se retira y se reporta en `unverified`; una oración que afirme megawatts o capacidad eléctrica se quita (D-003); fuentes (URLs devueltas) y factores ausentes se agregan al final. Dormido por defecto: sin `ANTHROPIC_API_KEY`, 503. Tests sin red ni clave en `services/api/test_oracle.py`.

## D-011 — 2026-10-12 — Atlas Comparativo a USD 15,000

Aprobado por el dueño. Dos o tres predios con fecha de decisión, escenarios y memo. Se acredita completo contra un Atlas Screening firmado dentro de 90 días. Es la puerta de entrada; el Screening (D-006) sigue siendo el destino. No se vende antes de medir las fuentes en vivo. Detalle en `docs/09-portafolio-90-dias.md` (P2).

## D-012 — 2026-10-12 — Tres primeras cuentas y cómo se despliega

Fibra Mty, FIBRA Prologis y Vesta, por evidencia pública de compra en curso (`docs/09-portafolio-90-dias.md` §3). AMPIP es canal después del primer memo. Despliegue en Railway: demo pública de solo lectura, espacio de cliente con llave y trabajo de fondo. El Oráculo no abre sin `ATLAS_ACCESS_TOKEN` (`services/api/atlas/access.py`). Plan en `docs/10-plan-30-dias.md`.

## D-013 — 2026-10-12 — Revisión de adquisiciones: precio por nave con tope por portafolio

Aprobado por el dueño. Producto: memo de banderas rojas antes de la exclusividad (lectura del cuarto de datos con cita a página, rent roll, cruces, riesgo físico de Atlas). No incluye opinión legal, inspección física, ambiental firmado, valuación ni capacidad eléctrica certificada. Se cobra por nave con un tope por portafolio; los montos se fijan con comparables (pendiente del agente de mercado) y se agregan como decisión nueva. Detalle en `docs/11-revision-adquisiciones.md`.

## D-014 — 2026-10-13 — Montos de la revisión de adquisiciones

Aprobado por el dueño, sobre la propuesta de `docs/13-comparables-precio.md` §1. **USD 3,500 por nave**, mínimo 3 naves (USD 10,500), **tope de USD 45,000 por memo hasta 60 naves**; arriba de 60, el mismo tope por cada bloque de 60. Hasta 3 contratos de renta por nave incluidos; cada contrato extra, USD 150. 50% al recibir acceso al cuarto de datos y 50% contra entrega. Se acredita completo contra un Screening firmado en 90 días. Sube 20% si tres propuestas seguidas se firman sin regatear; baja a USD 2,800 por nave si tres seguidas no se firman por precio. Comparables fuertes: inspección física USD 8,000–15,000 por edificio, ambiental fase I USD 1,400–7,500, lectura de contratos con IA USD 10–20 por contrato.

## D-015 — 2026-10-13 — Sin GitHub Actions, las revisiones corren antes de cada push

El dueño no tiene gasto de GitHub por ahora: cada corrida de CI muere en ~2 s sin ejecutar pasos (desde el 2026-10-12). `.github/workflows/ci.yml` se queda tal cual para cuando vuelva. Mientras tanto, `herramientas/verificar.sh` corre lo mismo que el CI y `.githooks/pre-push` lo exige antes de cada push (`git config core.hooksPath .githooks`). Un push sin verificar se hace solo con `--no-verify` y se dice en el commit.

## D-016 — 2026-10-21 — Producto 4: el agente se construye con los datos de cada negocio

Dirección del dueño. El agente de WhatsApp (P1) se empaqueta como plataforma que se arma alrededor de cada cliente: datos básicos, conexión por QR y, desde el historial del propio negocio, perfil (contrato JSON por cliente, como la ontología de Atlas), voz citada y reglas de cotización como datos, todo aprobado por el dueño del negocio antes de encenderse. Hereda el núcleo de Gestor Morelos y la vara de fq-bot. Desde la primera instalación hay llave interna y un MCP para afinar con un agente de código, con cada cambio como versión nueva aprobada. El QR es el de la **coexistencia oficial de Meta** (Embedded Signup sobre la app de WhatsApp Business), no el de WhatsApp Web: el worker no oficial pone en riesgo el número del cliente (P1, `08-mercado.md` §1.5). Se mide antes de escribir el conector. El costo de API se diseña con tope por cliente, modelo chico para rutina y lote, una pasada grande por perfil y caché. Precio el de P1. Detalle y orden de trabajo en `docs/15-agente-a-la-medida.md`.

## D-017 — 2026-10-21 — Producto 4 en código: un espacio por cliente, cifra solo del cotizador, sombra de fábrica

Primera sesión de código de D-016 (`services/agente/`). Se reescribió el núcleo de Gestor Morelos para un cliente por espacio en vez de extraerlo tal cual: el código de Gestor es de gestoría vehicular (tarifas de Morelos en Python, SQLModel, su worker) y no se separa sin arrastrar el giro. Lo que se tomó es el patrón: cifra que solo pone el código, voz revisada antes de salir, META para escalar, sombra y la vara. Decisiones con efecto:

- **El texto del modelo no lleva ningún número**, ni horas ni fechas: se revisa por código y, si trae, va a la persona con el borrador. Más estricto que Gestor (que bloquea montos); se afloja solo con datos de la sombra.
- **Cotizador por reglas de datos con origen**; si dos reglas igual de específicas chocan (p. ej. temporada alta contra fin de semana) **no se elige**: la cotización sale incompleta y va a la persona. El dueño lo arregla con una regla explícita.
- **El perfil tira lo que no prueba su origen**: cita literal en un mensaje del negocio de ese mismo espacio (o en el alta o un documento suyo) y, si el renglón trae cifra, la cifra dentro de la cita.
- **Nace en sombra**: `encendido` de fábrica es `sombra` (nada sale). `sin_cifra` deja salir guardadas y respuestas sin cifra; la cotización siempre con aprobación.
- **Sin tope configurado, el tope es 0**: no se gasta hasta que alguien diga cuánto.
- **Costo** con precios de la skill `claude-api` (2026-10-06): con supuestos explícitos (`gasto.estimar_mes`), un cliente de 300 conversaciones al mes cuesta ~USD 3.2 de API (USD 1.1 de ellos la pasada única del perfil). La escalada a Opus es la mitad del costo recurrente. No es medición.
- `httpx` entra a `requirements-dev.txt` (el TestClient de FastAPI lo pide); el servicio no lo usa.

Lo que no se pudo: medir la coexistencia contra Meta (necesita la cuenta de DGED como Tech Provider; `MEMORY/FUENTES.md`) y llamar a la API real (sin clave en esta sesión). Gestor no trae `MEMORY/` propia: su memoria vive en `rasdg05/gestor-personal`, que no se agregó.
