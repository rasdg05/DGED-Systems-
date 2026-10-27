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

## D-026 — 2026-10-27 — El número vinculado se lee del campo `User`, y se confirma en cada conexión

Finca Emiliano vinculó bien (el dispositivo "ia" quedó activo) y la pantalla dijo "Número equivocado". `on_pair` hacía `str(event.ID)` sobre el objeto JID de neonize y sacaba dígitos de todo el texto (User, Server, Device): los últimos diez ya no eran los del negocio. Efecto caro: `importar` rechazó el historial que WhatsApp manda **una sola vez al vincular**. Ahora `numero_de` lee `.User` (o el texto antes de `:`/`@`), y `on_connected` confirma el número con `client.get_me()` en cada conexión, como Gestor (`_registrar_numero_de_la_sesion`), así que un "numero_ajeno" mal leído no se queda pegado. Test con el caso. El historial perdido se recupera desvinculando y volviendo a vincular.

## D-027 — 2026-10-27 — Desarrollo en local y enjambre de Claude Code para los pendientes, como en Gestor

Dueño: *"para no acabarnos el presupuesto de uso de api quisiera hacer la mayor parte de desarrollo en local y quiero las mismas capacidades de poder desplegar agentes autónomos en swarms para atender cotizaciones pendientes (...) Solo quiero dejar todo listo y medido."* Se copió el modelo de Gestor (`app/services/rondas.py`): el enjambre son subagentes de Claude Code que leen cada plática pendiente y redactan; el orquestador revisa contra la plática; producción solo recibe la ronda. **No llama a la API.** Piezas: `agente/local.py` (copia local con tope 0 y en sombra, lotes, validar, subir con prueba por defecto), `agente/pendientes.py` (una sola vara: `espera`, `solo_medios`, `reclamo`, `no_pide`; el panel la usa), `agente/rondas.py` y rutas del taller (`espejo.json`, `pendientes.json`, `rondas`, `propuestas`), solo con la llave maestra. Más estricto que Gestor en dos cosas: el texto del enjambre no lleva cifras (la pone el cotizador) y **todo** lo de una ronda espera el sí de una persona del negocio. Medido con el historial real de Finca Emiliano: 276 sin responder = 143 esperan, 78 solo medios, 55 no piden, 0 reclamos; 111 de las 143 nunca tuvieron respuesta de una persona. Costo de la vía API para comparar (tokens estimados, no contados): pasada del perfil USD 0.90–1.38 (≈184k tokens de entrada: el material repite la plantilla cientos de veces), clasificación en lote USD 0.15, borradores de los 143 con Haiku USD 0.16. La API no es cara en este cliente; lo local sirve para iterar sin límite y sin depender de la llave. De paso se cerró un hueco: `datos/espacios/` en `.gitignore` solo tapaba la raíz; ahora `**/datos/espacios/` y el test le pregunta a git.

## D-028 — 2026-10-27 — La vara del agente: jugadas del giro, holdout sellado, costos versionados, cero API

Sesión pesada de alineamiento y entrene (`docs/18`), con el rigor de Gestor Morelos (`herramientas/vara.py`, `replay.py`, `backtest.py`, `entrenamiento.py`, `docs/plan_alineamiento_cuantitativo.md`). Se copiaron los métodos, no el giro:

- **Jugadas, no texto** (`agente/jugadas.py`, clasificador `finca-1`): cifra, disponibilidad, anticipo, pide:fechas/personas/evento/propiedad/otra, espera, visita, info:capacidad/ubicación/incluye, fotos, confirma, saludo, acuse, medio, otra. `otra` = 1.8% en desarrollo (meta < 10%). Validado a mano en una muestra ciega de 40 momentos de desarrollo que no se usó para escribir reglas: **36/40 (90%)**. Las 60 de la primera muestra sí se usaron para corregir; 140 momentos al azar de todo el universo (con holdout) se leyeron una vez para diseñar la taxonomía, antes de existir el sello.
- **Lo automático no es una persona**: plantilla = ≥ 20 usos y ≥ 4 palabras (un "Ok" repetido 26 veces lo teclea Mariana); automática = plantilla a ≤ 20 s del cliente o que abre el intercambio (la bienvenida de WhatsApp Business, que llega tarde con el teléfono apagado: 628 de 628 abren). **Plática de venta** = tuvo una plantilla de Finca o el CTA del anuncio (675 de 701): el teléfono vinculado es también el de la dueña como clienta de otros.
- **La vara** (`agente/vara.py`): momentos (1,003 en 383 pláticas) → holdout 25% out-of-time sellado desde el 2026-10-15 (251), embargo 7 días y purga por plática → desarrollo 498 en 209 pláticas; CPCV 6/2 = 15 caminos; placebo (y oráculo, que sí debe caer: 100% → 13.3%); IC por plática; DSR deflactado por intentos; PBO por CSCV; libro de predicciones sellado con hash; bitácora `services/agente/vara/intentos.jsonl` en git solo con agregados. El agente se simula con **el mismo código del turno** (`agente.antes_del_modelo`, `agente.candados`) y sin reloj de pared; donde iría al modelo, la jugada es `ia` y no se llama a nada.
- **El holdout se abre una vez por candidato** (huella del código que decide + perfil; la vara misma no cuenta) y no se abre si el perfil cita el embargo, el holdout o una plática del holdout. Al simular, el perfil pierde los renglones citados de la misma plática (una guardada citada de ahí es la respuesta del examen; sin esa purga el acierto literal era 1.4%, con ella 0.4%).
- **Costos v2**: callar es caro solo si el cliente pidió algo, con un juez independiente de los detectores del agente (si el agente se calificara con su propio `nada_que_contestar`, nunca fallaría). Cambiarlo fue un intento más en la bitácora.
- **Backtest por despliegue** (`agente/backtest.py`): al arrancar el servicio y en `POST /espacios/<id>/backtest` (maestra), el agente de hoy contra los últimos 14 días del historial, en los mismos momentos que el anterior; regresión con n ≥ 30. Su ventana se encima con el holdout: es alarma de despliegue, **no material para afinar**.
- **Corpus** (`agente/corpus.py`): 675 pláticas con `{{cifra}}` (250 montos tapados) en `datos/espacios/<id>/corpus/`, fuera de git.

## D-029 — 2026-10-27 — Lo que la vara y el banco cazaron en el código de producción, cada uno con su test

1. **La bienvenida automática callaba al agente 24 h** (`agente._lo_lleva_una_persona` contaba cualquier mensaje del negocio): 339 de 1,003 momentos. Ahora `lo_lleva_una_persona` salta lo automático; `fiel` pasó de 28 a 212 momentos de desarrollo.
2. **"persona" de conteo pedía una persona** (`conversacion.PIDE_PERSONA`, exportado de Gestor): *"para 100 persona"*, *"por persona"*. 11 de 11 disparos en el historial eran falsos.
3. **"Estoy pendiente de mi presupuesto" se callaba** (se leía "quedo pendiente"): era un error caro.
4. "Deja le pregunto a mi marido", "…le comento a mi esposo" y "anotado grax" (variante abreviada del banco) ahora son acuse; 4 cambios en 2,507 mensajes, los 4 correctos.
5. **`perfil.numeros`** leía *"12.000"* como 12 y *"$600,00"* como 60000 (las dos formas mexicanas): un renglón real del perfil se tiraba.
6. **El redactor no sabía lo que revisa el candado de voz**: 9 de 60 borradores del enjambre abrían con ¿ y se iban a una persona (Mariana abre así 1 de 598). `voz.reglas_para_redactar` va en el `system` del modelo.
7. `pendientes.hubo_persona`: de las 143 que esperan, **90** (no 111) nunca tuvieron respuesta de una persona.

El banco crece con 12 casos reales (`banco.CASOS_REALES`), pass^k 1.0 y cero caros.

## D-030 — 2026-10-27 — Resultado: nada pasa la compuerta; lo que falta es estructural

Perfil armado en local por el enjambre (4 agentes, solo desarrollo, 285 renglones citados, 0 descartados; **no se subió**). Contra la línea base (sin perfil, todo a una persona; puntaje 0.30 en dev y holdout):

| intento | dev puntaje | holdout | DSR |
|---|---|---|---|
| perfil del enjambre, sin modelo | 0.115 (A_pol 37.3%, IC 32–44) | 0.097 (A_pol 31.5%, fuera del IC de dev) | 0.0 |
| + el enjambre redacta donde iría al modelo (n = 60, dev) | 0.28 en la submuestra vs 0.30 | no aplica (solo dev) | 0.0 |

Lectura: con perfil, 61% de los momentos irían al modelo y las guardadas casi no aciertan fuera de su plática; las redacciones van a una persona en 41 de 60 (cotizar, disponibilidad, candados). Se dice como fq-bot: **el mejor candidato es indistinguible de pasarlo todo a una persona**. Lo estructural, medido: en **96%** de las cifras de la casa (194 de 202) el cliente no había dicho la propiedad (la casa elige por el tamaño del grupo) y los precios se negocian por grupo (quinta a 6,000/8,000/10,000 la noche; finca con 6 habitaciones a 20/22/25 mil). El cotizador de reglas fijas no puede reproducir eso sin inventar. Siguiente palanca: la lista de precios del dueño como documento (precio por propiedad × personas/habitaciones × temporada) y un cotizador que elija propiedad por grupo; disponibilidad (31 momentos de dev) necesita el calendario. El encendido sigue siendo del dueño con las compuertas de `docs/18`.

## D-031 — 2026-10-27 — La lista de precios se lee de las cotizaciones que el negocio ya dio; el cotizador elige la propiedad por el grupo

Encargo del dueño: armar el cotizador por grupo con la lista de precios reconocida en los mensajes. No hay lista escrita; hay 217 cotizaciones en 177 pláticas de Finca Emiliano. `agente/lista_precios.py` las lee sin modelo (propiedad por la presentación que la casa mandó en la plática, grupo por lo que dijo el cliente con `agente/lectura.py`, unidad, temporada) y arma escalones por propiedad × unidad × temporada con programación dinámica: más cotizaciones coincidentes, un escalón de más cuesta una, montos que no bajan al crecer el grupo. **El precio de un escalón es uno que la casa escribió, nunca un promedio.** Entra con ≥ 60% de acuerdo y ≥ 2 pláticas; si no, queda `a_decidir` sin monto y el cotizador no lo salta. Una regla `grupo` puede probar su tamaño de grupo con la cita del cliente de la misma plática, antes del precio (`origen.grupo`, revisado por `perfil.validar`); `habitaciones` pasa a ser cifra que la cita debe traer. La temporada "fin de año" se propone como la observó la casa (noches 23-dic a 1-ene), `a_confirmar`. `cotizador.cotizar_grupo` y `agente.por_grupo` cotizan sin modelo, cada cifra espera el sí de una persona. Detalle y la lista en `docs/19-lista-de-precios.md`. La propuesta vive fuera de git y **no se subió**: subirla es del dueño.

## D-032 — 2026-10-27 — Lo que cazó la sesión del cotizador, cada uno con su test

1. **`[otro]` no es un medio**: son avisos de protocolo de WhatsApp (reacciones, ediciones, llaves); 710 del cliente en Finca Emiliano, 475 justo tras un texto suyo. El turno los leía como "foto o audio" y mandaba todo a una persona sin leer el texto. Ahora, pegado a texto, se contesta el texto; solo, sigue a una persona (callarlo costó 7 errores caros en grupo-3).
2. **El canal no saca una cifra sin aprobación aunque falte la marca** `requiere_aprobacion` (defensa de fondo de XXXIII; las guardadas aprobadas quedan como estaban).
3. Las fechas *"Del 23 al 25 de. Dic"* no se leían; *"12 adultos y un menor"* contaba 12.

## D-033 — 2026-10-27 — Resultado: el cotizador por grupo mejora la vara en el holdout y no pasa la compuerta

Cinco intentos en desarrollo (lista de cada plática armada sin ella, tope 0) y el holdout abierto una vez para grupo-5: puntaje 0.339 en desarrollo y **0.334 en el holdout contra 0.300 de la línea base** (PSR 0.997, cero errores caros); en el holdout el monto del cotizador es uno de los que escribió la casa en 12 de 18 (n < 30, no concluye). **DSR 0.0**: con 11 intentos en la bitácora la deflación exige un Sharpe de 0.99 y este da 0.23; el A_pol del holdout cae fuera del IC de desarrollo. No se enciende nada. Medido y descartado (cementerio): cotizar cuando el cliente da los datos que la casa pidió (grupo-3, 0.289): la casa contesta eso con fotos y presentación. Lo que limita no es el código: la casa negocia por grupo (20 personas recibieron 20, 22 y 25 mil), presenta antes de dar precio, y la disponibilidad necesita el calendario. Siguiente: lista confirmada por Mariana (lo a decidir y la temporada) y el calendario; holdout nuevo con momentos posteriores al 2026-10-27, porque este ya se abrió.

## D-034 — 2026-10-27 — El calendario de ocupación se lee por iCal; "libre" exige que todas las fuentes estén frescas

Encargo del dueño: adelantar el calendario (Google Calendar y Airbnb como mínimo, Booking si se puede). Se buscó en GitHub (2026-10-27): no hay un channel manager abierto que sirva de base; lo que existe son sincronizadores de iCal chicos (`pixelcrash/Sync-Rentals-Calendar`, `gnacho/keynest`) o PMS de hotel pesados (QloApps, Kamra). Las APIs con precio y mensajes (Channex, Beds24, Smoobu, Hospitable) son de paga y piden ser socio; quedan para cuando el iCal no alcance. Se usa **iCal**, que las tres plataformas exportan sin permiso especial: `agente/calendario.py` lo lee sin paquetes (fechas de día completo con salida sin contar, `TZID`, UTC, líneas plegadas, `CANCELLED` no ocupa, una cita del mismo día no ocupa la noche). Las URLs viven en el espacio (`calendario.json`, fuera de git) y no salen en ninguna vista. El servidor baja cada fuente cada 30 min. **Una noche es libre solo si todas las fuentes de la propiedad respondieron con un calendario de verdad en las últimas 12 h** (LXI); un 200 que no es `VCALENDAR` es falla, como en XIX. En el turno, con fechas, la propiedad ocupada no se cotiza y, si todas lo están, va a una persona con el aviso de borrador (LXII); lo que no se sabe viaja en la cotización para quien la aprueba. La vara no pasa calendario (no hay calendario del pasado): sus números no cambian. **No medido** contra los calendarios de Finca Emiliano: faltan sus enlaces (pregunta 25 de `docs/20-hoja-para-mariana.md`). Siguiente, cuando haya enlaces: medir cada cuánto publica cada plataforma y exportar un iCal propio por casa para que Airbnb y Booking se bloqueen entre sí.

## D-035 — 2026-10-27 — Mariana confirma la lista en bloque; un "podría" o un rango no es precio

Respuestas por WhatsApp a la hoja corta (citas y horas en `docs/20-hoja-para-mariana.md`, "Lo que contestó"). Confirma la lista en bloque (*"Si ándale así"*), con la temporada fin de año 23-dic → 1-ene y su mínimo de 3 noches. Para la quinta chica da *"podría dejarles en 5,000 para 6 personas"* sin decir la unidad, y no contesta el fin de semana; para la finca una noche, *"podría variar si 12,000 o 15"*. **Un "podría" sin unidad o un rango no entra como regla**: los escalones siguen `a_decidir` y esas cotizaciones van a una persona, igual que una banda sin acuerdo (D-031); se cierran con una pregunta cada uno. Confirmar por WhatsApp no es aprobar: la lista sale hasta que ella la apruebe en Asistente → Precios. Su calendario vive en Google Calendar; se conecta por su dirección secreta iCal (D-034).

## D-036 — 2026-10-27 — Calendario antes que enjambre: una ronda no vende una fecha a ciegas

Orden del dueño: *"primero lo de google calendar para no vender fechas ya apartadas"*, y después un enjambre que dé seguimiento a los no contestados, cierre cotizaciones y mande recordatorios. El turno ya quitaba la propiedad ocupada (LXII) y dejaba pasar lo que no se sabe con nota, porque una persona lo lee en caliente. Una ronda son decenas de borradores aprobados de golpe: ahí una cotización con fechas entra **solo si el calendario dice libre** (sin calendario conectado, ocupada o sin saber: fuera), y al enviar se vuelve a revisar: si otra plataforma vendió esas noches entre la ronda y el sí, no sale (LXIII). El seguimiento sin fechas ni cifra (*"¿sigue interesado?"*) no depende del calendario. El enjambre sigue sin enviar nada: deja borradores esperando el sí de Mariana, y sin conector oficial nada sale (D-018).

## D-037 — 2026-10-27 — Se envía por el WhatsApp vinculado, como Gestor Morelos

Decisión del dueño: *"quiero hacerlo así directo como en Gestor Morelos. No me importa que no haya conectado oficialmente Meta"*. Revierte para Finca Emiliano la regla de D-016/D-018 (el vinculado solo lee). **Riesgo aceptado por el dueño**: WhatsApp puede suspender un número que lee como envío masivo (P1, `08-mercado.md` §1.5); por eso lo que cambia es el canal, no los candados. Con `"canal": "vinculado"` en el `config.json` y el lector conectado, `canal.enviar` encola y el proceso del lector manda (`enviador.py`, `mandador.py`): uno a la vez, 60–180 s al azar entre envíos, de 9:00 a 20:59, ≤ 60 al día, una ronda por plática cada 24 h (LXIV), y revisa todo otra vez justo antes (LXV). Qué sale sigue igual: en `sombra` nada; en `sin_cifra`, lo que no lleva cifra; una cifra solo con el sí de una persona del alta. Para el enjambre, ese sí se da a la ronda completa (`POST /espacios/<id>/rondas/<nombre>/aprobar`, llave maestra; `python -m agente.local aprobar`), como el orquestador de Gestor. Las respuestas en vivo por el vinculado no se encendieron: solo rondas y aprobaciones. **No medido**: el envío real por neonize (`send_message` + `build_jid`, mismo pin que Gestor).

## D-038 — 2026-10-27 — El ritmo del vinculado: uno cada 40 segundos

Dueño: *"1 cada 40 segundos está bien"*. `enviador.PAUSA_MIN, PAUSA_MAX = 40, 50` (40 s más hasta 10 s al azar, para que no sea un metrónomo). Lo demás de LXIV no cambia: de 9:00 a 20:59, ≤ 60 al día (a este ritmo, ~45 min de envío), una ronda por plática cada 24 h. Un espacio puede ir más lento, nunca más rápido.

## D-039 — 2026-10-27 — La app deja de "aprender": semáforo, cola y calendario a la vista, como Gestor

Dueño: *"la página se siente muy vacía, ya no debería decir aprendiendo, ya debería estar lista para conectarme al google y el semáforo de pendientes para enviar mensajes, la cola"*. Se trajo de Gestor Morelos (`expediente_cotizacion.semaforo`, `QUE_HACER`) **el semáforo**: un estado por plática, el más urgente, ordenado por cuánto lleva esperando (`agente/semaforo.py`): sin atender, le toca contestar, reclamo, foto o audio, quedamos de mandar, cotizado, esperando al cliente, cerrada; rojo / ámbar / verde / gris por estado y horas, y `seguimiento` para lo cotizado o preguntado que lleva de 24 h a 21 días sin respuesta (lo que el enjambre persigue). Pantallas nuevas (`agente/operacion.py`, llave del cliente): **Pendientes** (el semáforo completo), **Cola de envío** (esperan su sí con botón de aprobar, en cola, enviados y lo que no salió con su porqué en palabras del negocio) y **Calendario** (conectar Google Calendar, Airbnb o Booking pegando el iCal; estado de cada fuente y 6 semanas de noches libres, ocupadas y sin saber; la URL nunca se vuelve a mostrar). Inicio enseña el semáforo, el envío y el calendario y se refresca solo; el modo `sombra` se lee "Listo · envío en pausa" y `sin_cifra` "Listo · enviando". De paso: *"ya rentamos / encontramos / apartamos"* (plural) no se leía como cierre; ahora sí, con test (el test viejo lo fijaba como `False` sin razón escrita).

## D-040 — 2026-10-27 — Tope del vinculado: 100 mensajes al día

Dueño: *"Cámbialo de 60 a 100 mensajes al día"*. `enviador.TOPE_DIA = 100`. A uno cada 40–50 s son ~75 min de envío; lo demás de LXIV no cambia (9:00 a 20:59, una ronda por plática cada 24 h, un espacio puede ir más lento y nunca más rápido).

## D-041 — 2026-10-27 — Las rondas también dan seguimiento; lo de más de 3 semanas se enfría

Para que el enjambre persiga *"los no contestados y cierre cotizaciones"*, una ronda acepta, además de `espera`, el **seguimiento** que marca el semáforo: lo último es del negocio (cotizó o preguntó) y el cliente no contesta hace 24 h a 21 días. Lo recién cotizado (< 24 h) o frío (> 21 días) no. `python -m agente.local pendientes` arma los lotes en el orden del semáforo, con `tipo` contestar o seguimiento y `--dias`. Medido en Finca Emiliano el 2026-10-27 (706 pláticas): 349 rojos, de los cuales 126 llevaban más de 21 días sin que nadie los atendiera; ahora salen en gris ("se enfrió") y el rojo es lo de hoy.

## D-042 — 2026-10-27 — La mesa de la dueña por WhatsApp, como `dueno.py` de Gestor

Dueño: *"el agente asistente debe tener las mismas o más capacidades que el de Gestor Morelos. El número de la otra administradora (...) con ella le puedes enviar los reportes de los agentes autónomos, seguimientos y todo eso"*. `agente/mesa.py`: las administradoras (el teléfono de quien aprueba según el alta, más `config.administradores`) escriben al WhatsApp del negocio y el asistente les contesta por el vinculado: *estado*, *pendientes*, *cola*, *ayuda*; y solo quien aprueba: *aprueba la ronda* (cada salida a su nombre, mismos candados), *enciende el envío* y *pausa el envío* (lo aprobado en pausa entra a la cola al encender). Reportes a las 9:00 y 19:00. Una administradora no es clienta (LXVIII): en Finca Emiliano su plática (20 mensajes) estaba en el semáforo y un agente del enjambre la apartó por criterio, no por regla; ahora es regla. La mesa solo escribe a administradoras (LXVII). El enviador corre siempre en el proceso del lector: encender el envío ya no pide redesplegar. El Asistente enseña lo que hace y las órdenes de WhatsApp, y la lista de precios leída de las cotizaciones quedó subida como versión 1 por aprobar (Mariana la confirmó por WhatsApp, D-035; la aprobación en pantalla es suya). **No medido** contra WhatsApp: el primer reporte sale al redesplegar (ya pasaron las 9:00).
