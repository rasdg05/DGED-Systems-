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

## D-018 — 2026-10-21 — Lector por QR vinculado, solo lectura, para la primera ingesta

Decisión del dueño, con el riesgo a la vista: la coexistencia oficial necesita que DGED sea Tech Provider (días o semanas) y la demo es ya. El historial del negocio se lee vinculando un dispositivo con neonize, como el worker de Gestor Morelos (`services/agente/agente/vinculado.py`). Es el canal no oficial que D-016 prohibió para **enviar**; aquí **solo lee**: el módulo no llama nada que escriba a WhatsApp (ni envío, ni acuse de lectura, ni presencia) y un test lo revisa en el código. Lo que el agente redacte sigue saliendo solo por la Cloud API. Riesgo que queda: WhatsApp puede castigar números con sesiones vinculadas de clientes no oficiales; leyendo sin enviar es bajo, no cero. La sesión vive en el espacio del cliente (volumen `/data`), y si `numero_negocio` está en su config y se vincula otro número, no se importa nada.

Despliegue: el agente es otro servicio de Railway del **mismo repo** (`services/agente/railway.json`, `Dockerfile` propio), no otro repositorio: comparte la vara, las invariantes y el pre-push. Se separa en su repo si un día tiene equipo o ciclo de despliegue propio. Web y lector van en un solo contenedor porque en Railway un volumen se monta en un servicio. Medido el 2026-10-21 desde un contenedor: el lector arranca y WhatsApp entrega el QR (`esperando_qr`), y la página lo dibuja.

## D-019 — 2026-10-27 — Lo que hace útil al agente de Gestor, exportado; el banco antes del encendido

Dirección del dueño: llevar al esqueleto lo que hace útil al agente de Gestor Morelos (main del 2026-10-27, corridas 5 a 9) y entrenarlo con Finca Emiliano. Se exportó lo que no depende del giro (`services/agente/agente/conversacion.py`): la ráfaga se lee junta, lo que nadie oyó no tiene turno, el acuse y el cierre callan, la promesa del cliente deja la pelota de su lado, reclamo/insulto y "quiero una persona" van a una persona, "¿eres un bot?" se contesta con la verdad, en vivo el agente no habla encima de una persona (24 h), y el "ok" que aplaza no es un sí. Todo antes de gastar un token. No se exportó lo de placas (tarifas, padrón, guías), la elección por Thompson ni el refinador: necesitan la sombra de este negocio para tener con qué decidir.

El banco de Gestor (`banco.py`) entra como compuerta: pass^k sobre cinco variantes de escritura y un red team con modelo adversario, en una copia del espacio. Al nacer cazó dos huecos que ahora tienen test: "grax" no era acuse, y una cifra escrita con letra ("seis mil") pasaba el candado. El texto del modelo ya no lleva cantidades de ninguna forma ("mil gracias" sí). Las pantallas del espacio (tablero, alta, WhatsApp, conversaciones con teléfonos enmascarados, perfil, banco) se rehicieron con la paleta de Atlas, pensadas para el celular.

Despliegue: el `railway.json` de la raíz ya no fija `dockerfilePath` (le ganaba a `RAILWAY_DOCKERFILE_PATH` y el servicio del agente construía Atlas); hay test que lo cuida.

## D-020 — 2026-10-27 — Pantallas del agente: iOS nativo hecho a mano, sin Basecoat; la foto y el color del negocio mandan

Encargo del dueño: "el Airbnb de Apple", empezando por lo que ve el negocio (`/v/`). Se decidió **no** usar Basecoat (propuesto en `docs/16`): trae Tailwind (compilado vendido o CDN), y su estética es la de un SaaS web, no la de Apple; una pantalla que abre el negocio desde su celular no debe depender de un CDN. En su lugar, un solo `CSS` propio en `paginas.py`, sin dependencias:

- **Apple**: fuente del sistema (SF en iPhone), título grande, listas agrupadas con separadores con sangría, barra superior y **pestañas abajo** con vidrio (`backdrop-filter`), modo oscuro con los grises de iOS, movimiento sutil que respeta `prefers-reduced-motion`. Sin píldoras: el estado es un punto y una palabra.
- **Airbnb**: en `/v/` la **portada es la foto del negocio** (o, sin foto, un degradado de su color con su inicial en vidrio) y una hoja blanca que sube encima. Un solo acento: el color del negocio (`config.marca_color`, `#rrggbb` validado), que pinta botones, pestaña activa y burbujas propias.
- **Celular primero**: el código de vinculación en casillas como las de WhatsApp y con botón de copiar (sin guion); aviso, solo en pantallas táctiles, de que el QR no se puede escanear desde el mismo teléfono; progreso Preparar · Vincular · Copiar; la página se actualiza **en su lugar** (fetch + View Transitions) y, sin JS, con `<meta refresh>` en `<noscript>`.
- **Portada**: se sube desde el alta (el teléfono la achica a 2000 px JPG antes de mandarla), se juzga por sus bytes (JPG/PNG/WebP, ≤ 8 MB), queda una sola en el espacio y `/v/<id>/portada` solo abre con el enlace del negocio.

Invariantes nuevas con test: en **ningún** estado del lector `/v/` enseña menú, conteos, detalle técnico, número vinculado ni enlaces a lo interno; color fuera de `#rrggbb` se rechaza; portada sin llave o que no es imagen se rechaza. Medido con Playwright a 390 px, claro y oscuro: ninguna pantalla con scroll horizontal. Sin fotos reales de Finca Emiliano todavía: su `/v/` sale con degradado e inicial hasta que suban la suya.

## D-021 — 2026-10-27 — Las pantallas del espacio son para administrar; lo de desarrollo no se ve

Dicho por el dueño al ver el despliegue: el alta "ya ni tiene caso", el banco "no se entiende" y "no parece que haya nada útil para el negocio"; la plataforma debe centrarse en la administración y el desarrollo quedar invisible (subcuentas, después). Se reorganizó en cuatro pestañas:

- **Inicio**: saludo, el asistente en palabras del negocio (`sombra` = "Aprendiendo"; `sin_cifra` = "Contesta lo sencillo"), **Pendiente** (solo lo que pide una acción: datos que faltan, conectar WhatsApp, versión por revisar, cotizaciones que esperan su sí, chats sin responder) y sus chats.
- **Chats**: los sin responder marcados; dentro del chat, lo que el asistente habría contestado en burbuja punteada y, si es cotización, el botón **Aprobar** ahí mismo (`/salidas/<id>/aprobar` acepta `?llave=`; en sombra se aprueba y no sale).
- **Asistente** (antes "Perfil"): lo que sabe en palabras del negocio: **Precios** como lista por propiedad, propiedades, temporadas, respuestas, lo que pasa a una persona, cómo habla. Cada dato conserva su origen, plegado en "De dónde salió". Lo descartado, plegado al final.
- **Negocio**: WhatsApp (estado y enlace para conectar), marca (color y foto, que se guardan solos: `POST /marca`) y los datos del alta en lectura, con "Editar".

El **taller** (`/banco`: proponer perfil, banco pass^k, sombra, descargar historial) sigue abriendo por su ruta y no tiene pestaña. Test: en Inicio, Chats, Asistente, Negocio y Alta no aparece ninguna palabra de desarrollo (pass^k, banco, sombra, simbiosis, jsonl, taller, "modelo grande", "Autor:"). Subcuentas por persona (dueño, encargado, DGED) quedan para después; hoy la llave del espacio abre todo lo del negocio y la maestra además el taller por URL.

## D-022 — 2026-10-27 — El taller no existe para el cliente; el panel toma la forma del de Gestor

El dueño: "Eso del banco quítalo. No se ve confiable, un cliente nuevo ve eso y se va a espantar". D-021 ya le había quitado la pestaña; ahora tampoco abre por URL con la llave del cliente: `/banco`, `/historial.jsonl` y `/simbiosis` piden la llave maestra (`TENANT_INTERNAL_TOKEN`, `espacio.llave_maestra`) y con la del cliente responden **404**, no 401, para no anunciar que hay algo detrás. Test por ruta.

Del rediseño iOS de Gestor Morelos (`a727d51`, "que parezca un software iOS native") se trajo lo que encaja: barra de arriba transparente que se vuelve vidrio con el título chico cuando el grande se va (IntersectionObserver); ícono de la app con la inicial y el color del negocio; barra lateral en iPad grande y Mac (≥ 1024 px); listas tipo Ajustes con íconos de color (Inicio y Negocio); transición entre pantallas (`@view-transition`); instalable desde Safari y Chrome (`app.webmanifest` e `icono.svg` por espacio, con su llave). No se trajo la hoja «Más»: con cuatro pestañas no hace falta. Sin PNG para el ícono de iPhone (no hay Pillow en la imagen): iOS usa una captura hasta que se agregue.

## D-023 — 2026-10-27 — El esqueleto del agente se vende como plug and play; Safari en iPhone es la vara

Dirección del dueño: "este esqueleto nos va a servir para ir copiando a otros negocios y revender el software como un plug and play", y que todo esté optimizado para iPhone en Safari.

- **Alta sin código**: `/negocios` (solo llave maestra; 404 con otra) lista los negocios con su estado y crea uno nuevo con nombre y color; nace en sombra. Entrega dos enlaces: el panel del dueño (llave derivada) y el de conectar WhatsApp. Textos del alta sin giro (nada de "huéspedes"). Runbook en `docs/17-plug-and-play.md`. Test de punta a punta.
- **Safari en iPhone**: ícono PNG de 180 px con la inicial y el color (Pillow entra a `requirements.txt`), `format-detection` apagado (el código y los teléfonos no se vuelven enlaces), áreas seguras laterales, `svh` en la portada, teclado de teléfono y mayúsculas donde toca, zonas de toque de 44 px, respaldo sin `color-mix` para iOS 15, y refresco al volver a la app instalada. Test `test_pag_reglas_de_safari_en_iphone`. Auditado con el perfil iPhone 15 en Chromium; **no medido en Safari real** (sin WebKit en el entorno).
- **Lo que todavía no es plug and play**: un lector vinculado por servicio (`AGENTE_ESPACIO_VINCULADO`), el cotizador con reglas de renta, y sin subcuentas.

## D-024 — 2026-10-27 — Si WhatsApp niega el código de vinculación, el negocio ve el QR

Finca Emiliano abrió su enlace y vio "Preparando" sin fin. Causa medida en la pantalla interna: `PairPhoneError(... 429: rate-overlimit)`; WhatsApp limita los códigos de 8 por número, y cada redespliegue del servicio (cuatro ese día) reinicia el lector y pide uno nuevo. El respaldo estaba roto: al fallar, se anunciaba `esperando_qr` **sin el QR** y los QR siguientes se ignoraban. `vinculado.Emparejar` publica el último QR en cuanto el código falla, sigue publicando los nuevos y reintenta el código pasada una hora; el detalle técnico ya no llega a la pantalla. Test con el caso. Lección: **no redesplegar el agente mientras un negocio está vinculando**.

## D-025 — 2026-10-27 — Vincular como en Gestor: QR siempre, código de 8 solo a pedido, botón de QR nuevo

El código de 8 que Finca Emiliano tecleó a los seis minutos dio "No se pudo vincular" (ya había caducado), y pedir uno en cada arranque fue lo que gastó el límite de WhatsApp (429). Se copió el modelo del panel de Gestor (`whatsapp_worker._reset_sesion`, `_pair_por_numero`): el lector publica **siempre el QR** y pide el código de 8 **solo cuando alguien toca el botón** (uno por minuto a lo más; vale ~150 s y luego vuelve el QR). **"Generar QR nuevo"** deja una orden (`vinculado/orden.json`) que el lector toma cada 2 s: borra la sesión a medias y sale; `arrancar.sh` lo levanta en 5 s con un QR nuevo, sin tocar la web. Los botones están en el enlace del negocio y en el panel, funcionan sin JS y no tocan una sesión ya conectada (409). Tests.
