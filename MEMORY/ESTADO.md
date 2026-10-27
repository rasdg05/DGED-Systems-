# Estado — 2026-10-27

> Lo único de la memoria que caduca rápido. Al cerrar trabajo, actualízalo.

## Corre

- **Presentación del negocio** (2026-10-21): `docs/presentacion/DGED-presentacion.pdf`,
  14 láminas con lo que ya existe y sus precios aprobados. Versión web privada en
  https://claude.ai/artifact/W415FmFrJxFN4W7X8yuaVQ (se comparte desde su menú).
  No usa las capturas de `docs/demo/` (marca "API KEY REQUIRED" del mapa base).
- **Producto 4 en código, en sombra** (D-016, D-017, `services/agente/`, rama
  `claude/agente-a-la-medida`): espacio por cliente con llave, historial en la forma
  de los webhooks de coexistencia, perfil con origen por renglón y versiones que
  enciende el dueño, cotizador por reglas de datos, candado de cifra, voz, respuestas
  guardadas, tope de gasto, sombra con la vara, MCP de afinación y servidor (webhook
  firmado, pantalla de revisión). 68 tests sin red; las 8 invariantes del doc 15 son
  la XXXII–XXXIX. Muestra **ficticia** de finca y quinta en `services/agente/muestra/`.
  **No medido**: contra Meta (falta la app de DGED como Tech Provider) ni contra la API
  de Anthropic (sin clave). La demo del 2026-10-22 sigue siendo presentación + captura
  de datos; el código enseña el flujo con la muestra, no con datos del familiar.
- **Agente desplegado en Railway** (2026-10-27, environment "WhatsApp", rama `claude/agente-a-la-medida`):
  `/api/health` dice `dged-agente`. Primer negocio: **Finca Emiliano** (espacio `finca-quinta`). Con el
  conocimiento de conversación de Gestor exportado y el banco en pass^k 1.0 sin errores caros (D-019).
  Siguiente: vincular su WhatsApp, juntar historial, proponer perfil, aprobarlo y 30 conversaciones en sombra.
- **Exportado de Gestor Morelos** (D-019, `services/agente/agente/conversacion.py`, `banco.py`):
  ráfaga, acuse, cierre, promesa, reclamo, pedir persona, "¿eres un bot?", no hablar encima de una
  persona, el "ok" que aplaza; banco pass^k con red team. No se trajo la MEMORIA de Gestor: vive en
  `rasdg05/gestor-personal`, que no se agregó. Lo que el banco cazó se corrigió también en Gestor
  (`4f03c48` en su main, desplegado): cifra de la IA revisada por código, también con letra; "grax".
- **UX/UI** (D-020, 2026-10-27): rediseño "Airbnb de Apple" hecho, sin Basecoat. `/v/` con portada
  (foto o degradado del color del negocio), código en casillas, estado en vivo; pantallas internas
  con listas agrupadas y pestañas abajo. D-021: cuatro pestañas para administrar (Inicio, Chats,
  Asistente, Negocio). D-022: el taller (`/banco`, historial crudo, simbiosis) solo con la llave
  maestra; con la del cliente, 404. Barra, barra lateral, íconos de color e instalable, como Gestor.
  Subcuentas: pendiente. Color y foto se ponen en el alta. **Falta**: pedir a Finca
  Emiliano su foto original y el verde exacto de su volante, y subirlos desde su alta.
- **Lector por QR vinculado, solo lectura** (D-018): `services/agente/agente/vinculado.py`, página
  `/espacios/<id>/vincular`. Desplegable en Railway como servicio aparte del mismo repo
  (`services/agente/railway.json`). Medido: WhatsApp entrega el QR al contenedor. **Falta**:
  el escaneo real y medir cuánto historial manda.

- **Atlas** en `main` (`ed7752e`, score 0.1.0). La rama
  `claude/dged-systems-ai-space-f8pm53` lleva lo siguiente, sin pasar a `main`.
- **atlas-live-0.2.0** (D-009): USGS sismos y OSM vía férrea **puntúan si
  responden** (0.08 y 0.10); NASA POWER (lluvia, días > 35 °C) y la subestación
  OSM (nombre, voltaje del tag, km) **se muestran y no puntúan**.
- **Califica en vivo, medido 2026-10-12** (`docs/verificacion-2026-10-12.md`,
  con 0.1.0): 10 de 10 sitios contra INEGI (Catálogo Único, WMS uso de suelo e
  inundación) y el libro del SMN (corte 2026-09-30); los diez publicables, 0
  errores, ~2 s por sitio, scores de 70.8 a 83.0. Con 0.2.0 se calificaron 2
  sitios (El Marqués, Apodaca); n = 2 no concluye nada del modelo.
- **Docker, medido 2026-10-12**: `/api/health` a los 39 s de
  `docker compose up --build` (más ~20 s de imágenes), PostGIS sano y 10 filas
  en `atlas_score`. Medido con un ajuste del sandbox (CA del proxy, red del
  host) que no está en el repo; ver bloqueos.
- **Oráculo** (D-010): contesta solo con herramientas de Atlas; cerrado sin
  `ATLAS_ACCESS_TOKEN` y sin `ANTHROPIC_API_KEY`. **No medido contra la API
  real.**
- **Semana 1 del plan** (`docs/10-plan-30-dias.md`): llave del Oráculo, tope por
  IP, compose sin fugas, `/api/health` con commit, CI con ruff, cobertura y
  Dependabot.
- Arreglado en la verificación: la página de error del SMN no tumba el
  arranque; celda vacía del SMN = "sin sequía" del último corte (4 de 10 sitios
  cambiaron); calificar reintenta el SMN y, si falla, califica con la sequía
  ausente (no publicable); una respuesta rara del WMS ya no cuenta como "no
  inundable".
- **Fuentes medidas** (`MEMORY/FUENTES.md`, `herramientas/medir_fuentes.py`): 23
  fuentes el 2026-10-12. Vivas sin clave: USGS, NASA POWER, Sentinel-2 (Earth
  Search y Planetary Computer), Copernicus DEM, World Bank, Catálogo Único, GHSL.
  Con clave gratuita: Banxico SIE, INEGI BIE, NASA FIRMS. Open-Meteo gratis es
  **solo no comercial**. No concluyen desde aquí (puertos que el proxy no deja):
  CENACE PML, Atlas Nacional de Riesgos, SSN.
- **Fuentes para productos nuevos, medidas 2026-10-13** (`MEMORY/FUENTES.md`):
  Sentinel-1 VIVA (firma SAS anónima; revisita 3 días en la costa, hasta 7 en
  Apodaca: no se promete "≤24 h" en alertas); recorte Sentinel-2 en stdlib VIVO;
  CBP tiempos de cruce VIVO (sin serie histórica: hay que guardarla); compras de
  Nuevo León VIVAS (OCDS 2026 y 179 obras con coordenadas); FIRMS CSV 24 h sin
  clave VIVO. ComprasMX federal y la PNT: MUERTAS para lectura automática
  (captcha), al cementerio.
- **Ojo satelital, prototipo** (`services/satelite/`, `docs/12-ojo-satelital.md`):
  Sentinel-2 sin clave, nubes medidas con SCL sobre el recorte, NDVI/NDBI/BSI,
  "no concluye" con nubes. Corrido en vivo sobre 10 sitios y 2 obras (seca
  2024 vs 2026): BMW SLP muestra 20.9 ha suelo→construido dentro del polígono
  OSM de la planta (plausible, no verificado); LEGO no se pudo atribuir. **n = 2:
  no concluye precisión.** Dos umbrales de v0.2 se pusieron después de ver las
  obras: no validados. Siguiente: las 55 naves en construcción de Monterrey que
  reporta Colliers.
- **Lector del cuarto de datos** (`services/dataroom/`, `docs/14-lector-dataroom.md`,
  D-013): cita literal por página o se descarta; rent roll, cruces deterministas
  y memo de banderas rojas. En la muestra ficticia encuentra exactamente los 5
  errores plantados. **No medido contra la API real**: falta probar que
  `fallbacks` y la salida estructurada van juntos en la primera llamada.
- **Precio de la revisión de adquisiciones aprobado** (D-014): USD 3,500 por nave,
  mínimo 3, tope USD 45,000 por cada 60 naves.
- **Sin GitHub Actions** (D-015): el dueño no tiene gasto de GitHub; el CI muere
  sin correr. `herramientas/verificar.sh` corre lo mismo y `.githooks/pre-push`
  lo exige (`git config core.hooksPath .githooks` en cada clon).
- **Calificado en vivo con 0.2.0, 2026-10-13**: 10 de 10 publicables, de 71.2 a
  83.4 (Apodaca 78.3, Pesquería 72.3, Salinas 71.2, García 76.9, Ramos Arizpe
  82.9, Puerto Interior 72.8, El Marqués 76.0, Celaya 81.3, SLP 83.4, León
  77.8). El SMN volvió a dar su página de WAF: la sequía salió del libro real
  guardado (corte 2026-09-30). Vía férrea faltó en 5 (Overpass). DENUE y ruta
  ausentes en todos (sin claves). Capturas en `docs/demo/`.
- **Demo vista por el dueño (2026-10-13)**. Lo que da pena antes de una junta:
  mapa base de CARTO con "API KEY REQUIRED", la ficha muestra JSON crudo y el
  Oráculo pega URLs largas. Faltan también las instantáneas inmutables y el memo
  PDF (semana 2). Un intento con agentes se detuvo sin dejar nada: está por hacer.
- Pruebas sin red: 270 de Python y 6 de `score.test.mjs`, en verde; cobertura de atlas + dataroom + satelite + agente 78.95% (piso 70).

## Bloqueos (con causa)

- **SMN intermitente desde un centro de datos**: 3 de 12 (verificación) y 4 de
  30 (fuentes) descargas trajeron el libro; las demás, una página de WAF con
  HTTP 200. Sin libro, ningún sitio es publicable. Falta medir desde otra red.
- **Overpass**: solo `maps.mail.ru` contesta, con 504 a ratos y 10–50 s. Una
  caída deja vía y subestación ausentes (`evidence.osmAttempts`).
- **`docker compose up --build` tal cual** no corrió desde el sandbox: Docker
  Hub 429 y `pip` con `CERTIFICATE_VERIFY_FAILED` por el proxy. Causas de la
  red, no del proyecto.
- Sin `INEGI_TOKEN` ni `SAKBE_TOKEN`: DENUE conteo y rutas no entran al número.

"No medido" no es "medido y no funcionó".

## Sigue

0. **UX/UI en sesión nueva** (`docs/16-arranque-ux-ui.md`), en paralelo con: Finca Emiliano vincula
   su WhatsApp con el enlace del tablero → historial → proponer perfil → aprobar → banco → 30 en sombra.

0b. **Producto 4**: con los datos de la demo (con permiso), cargar el alta y 20–50
   conversaciones reales a un espacio, correr la simbiosis con clave y medir la primera
   llamada real (salida estructurada + `fallbacks` en Opus; lote en Haiku). Del dueño:
   Meta Business de DGED, verificación y App Review para medir la coexistencia
   (`MEMORY/FUENTES.md`). Después: 30 días de sombra; n < 30 no concluye.

1. Desplegar la demo en Railway: mide Docker y el SMN desde una red normal.
2. Arreglar la demo (mapa base sin clave, ficha legible, fuentes cortas) y la semana 2 (instantáneas y memo PDF).
3. Pedir las claves INEGI (DENUE), SAKBÉ y Anthropic; después Banxico, INEGI BIE y FIRMS.
   Volver a medir CENACE PML, ANR y SSN desde el servidor de producción.
4. Holgura eléctrica por corredor firmada contra PRODESEN (`DECISIONS.md` D-003).
5. Mercado y portafolio a 90 días (`docs/08-mercado.md`,
   `docs/09-portafolio-90-dias.md`): agente WhatsApp, Atlas Comparativo (USD 15k,
   D-011) y evaluación técnica; P4 solo tras medir CENAPRED/CFE/acuíferos.
6. Primeras cuentas (D-012): Fibra Mty, FIBRA Prologis, Vesta.

## Lo que es del dueño

- Producto 4: cuenta de Meta Business de DGED y su app para el Embedded Signup; tope
  de gasto por cliente; si el familiar de la demo es cliente que paga o caso citado.

- Claves INEGI (DENUE), SAKBÉ y Anthropic, y `ATLAS_ACCESS_TOKEN`.
- Acceso a Railway y un dominio para la demo pública.
- El contacto con nombre en Fibra Mty, FIBRA Prologis y Vesta.
- ¿Compras públicas con nombre de DGED o por un socio?
- Confirmar en BMV la fecha de la compra de USD 32.7 M de FIBRA Prologis (¿2023 o 2026?).
- ¿Producto de auditoría catastral (ley catastral aprobada en Diputados el 07/10, falta Senado)? Ofrecido, sin respuesta.
- Quién revisa los primeros diez sitios (alguien que haya trabajado parque en NL).
- El punto de `salinas-hofusan` cae en el polígono de General Zuazua, no de
  Salinas Victoria: ¿se mueve el punto o se renombra?
