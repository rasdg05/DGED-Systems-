# Estado — 2026-10-27 (Mariana contestó la hoja)

> Lo único de la memoria que caduca rápido. Al cerrar trabajo, actualízalo.

## Corre

- **Envío por el vinculado** (2026-10-27, D-037, LXIV–LXVI): decisión del dueño, como Gestor. Cola en el
  espacio, al paso de una persona, revisión justo antes; aprobar una ronda completa la encola. 319 tests en
  verde. **Para encenderlo** en Finca Emiliano: `"canal": "vinculado"` y `"encendido": "sin_cifra"` en su
  `config.json`, redesplegar (el lector arranca el enviador) y probar con una ronda chica. **No medido**
  contra WhatsApp. Sigue faltando `AGENTE_URL` + llave maestra en esta sesión para bajar y correr el enjambre.
- **Calendario antes que enjambre** (2026-10-27, D-036, LXIII): una ronda con fechas entra solo si el
  calendario dice libre, y al enviar se revisa otra vez. 309 tests del agente en verde. **Para lanzar el
  enjambre faltan**: `AGENTE_URL` y `TENANT_INTERNAL_TOKEN` en el entorno de la sesión (no hay acceso a
  producción desde aquí) y el iCal secreto de Mariana para cotizar fechas.
- **Calendario de ocupación por iCal** (2026-10-27, D-034, rama `claude/agente-a-la-medida`):
  `agente/calendario.py` lee Airbnb, Booking y Google Calendar; `python -m agente.calendario fuente|bajar|ver`,
  `GET /espacios/<id>/calendario.json` y `POST /espacios/<id>/calendario/fuentes` (llave del cliente); el
  servidor baja cada 30 min. Libre solo con todas las fuentes frescas (LXI); la propiedad ocupada no se
  cotiza (LXII). 14 tests; 307 del agente en verde. **No medido**: faltan los enlaces de Finca Emiliano.
- **Hoja para Mariana** (`docs/20-hoja-para-mariana.md`): el texto para mandarle por WhatsApp en versión corta: la lista en bloque
  para un solo "sí" y 3 preguntas (quinta chica y fin de semana, finca una noche, calendario).
  **Contestó el 2026-10-27** (doc 20, sección "Lo que contestó"): **"Si ándale así" a la lista en bloque**;
  quinta chica "podría" 5,000 para 6 con 3 habitaciones (sin unidad; el fin de semana no lo contestó);
  finca una noche para 25 "12,000 o 15" (rango, no regla); calendario en Google Calendar, a medias.
  **Siguiente**: en la máquina con `datos/`, marcar la lista confirmada en `propuesta.json` y subirla
  para que la apruebe en Asistente → Precios; dos preguntas para cerrar lo a decidir; pedir el iCal.

- **Lista de precios y cotizador por grupo** (2026-10-27, `docs/19-lista-de-precios.md`, D-031 a D-033,
  rama `claude/agente-a-la-medida`). Cero llamadas a la API; nada subido a producción.
  - **La lista**, leída de 217 cotizaciones en 177 pláticas (`python -m agente.lista_precios finca-quinta`):
    finca fin de semana 12k (11–13, 4 hab) · 20k (14–19) · 22k (20, 6 hab) · 25k (23–25) · 30k (30) ·
    35k (35–37) · 38k (39–40); quinta 10k la noche hasta 20 (normal y fin de año), 8k fin de año para
    9–10; las dos casas 45k el fin de semana; alberca finca 2k/día, quinta 900/día; visitas 100 por
    persona; fin de año mínimo 3 noches. **A decidir**: quinta 5–16 personas (5k a 9k), quinta fin de
    semana, finca una noche, finca fin de año. Temporada fin de año observada 23-dic → 1-ene, a confirmar.
    21 reglas + 1 temporada pasan `perfil.validar` (0 descartadas); propuesta en
    `datos/espacios/finca-quinta/lista_precios/propuesta.json` (fuera de git), **no subida**.
  - **Cotizador por grupo** (`cotizador.cotizar_grupo`, `agente.por_grupo`): elige la propiedad por el
    grupo (o la de la plática si tiene precio), fin de semana o por noche, temporada sin caer a la
    normal, mínimo de noches; sin grupo pregunta "Para cuántas personas?"; toda cifra espera aprobación.
  - **Vara**: grupo-5 dev 0.339 · **holdout 0.334 vs 0.300** de la base, cero caros, monto igual a la
    casa 12/18 en holdout (no concluye). **DSR 0.0** (11 intentos): no pasa la compuerta, nada se enciende.
    El holdout del 2026-10-15 ya se abrió para grupo-5; el siguiente, con momentos posteriores al 2026-10-27.
  - **Arreglado con test** (D-032): `[otro]` (aviso de protocolo) ya no esconde el texto del cliente;
    el canal no saca cifra sin aprobación aunque falte la marca; fechas "de. Dic"; "un menor".
  - Pruebas sin red: 293 del agente; `herramientas/verificar.sh` en verde.

- **Alineamiento y entrene del agente con el rigor de Gestor** (2026-10-27, `docs/18`, D-028 a D-030,
  rama `claude/agente-a-la-medida`). Cero llamadas a la API; nada subido a producción.
  - **La vara** (`python -m agente.vara medir finca-quinta --variante <x>`): 1,003 momentos reales,
    holdout sellado desde el 2026-10-15 (251), desarrollo purgado 498 en 209 pláticas, CPCV, placebo y
    oráculo, DSR, PBO, libro sellado, bitácora `services/agente/vara/intentos.jsonl` (11 intentos).
    Clasificador `finca-1`: 90% contra etiqueta a mano ciega (36/40). Holdout abierto una vez para la
    base y una para el perfil del enjambre; un tercer intento se rechazó.
  - **Resultado**: nada pasa la compuerta. Base (todo a una persona) 0.30 en dev y holdout; perfil del
    enjambre 0.115 dev / 0.097 holdout; enjambre redactando 60 momentos de dev 0.28. DSR 0.0 en todos.
  - **Lo estructural** (medido): en 96% de las cifras de la casa el cliente no dijo la propiedad (la
    casa la elige por grupo) y los precios se negocian por grupo. Hace falta la **lista de precios del
    dueño** y un cotizador que elija propiedad por grupo; disponibilidad necesita el calendario.
  - **Arreglado en el turno, con test** (D-029): la bienvenida automática ya no calla al agente 24 h
    (339 de 1,003 momentos); "persona" de conteo ya no pide una persona (11 de 11 falsos); "pendiente de
    mi presupuesto" ya no se calla; montos "12.000" y "$600,00"; el redactor recibe las reglas de voz
    del candado. Pendientes: 143 esperan, **90** nunca tuvieron persona (antes decía 111).
  - **Perfil en local** (enjambre, solo desarrollo): 285 renglones citados, 0 descartados, en
    `datos/espacios/finca-quinta/enjambre/perfil/perfil.json` (fuera de git). **No se subió**: subirlo
    con `--de-verdad` y aprobarlo es del dueño, y la vara dice que hoy no mejora nada.
  - **Backtest por despliegue** (`agente/backtest.py`, `GET/POST /espacios/<id>/backtest[.json]` con la
    maestra, sección en `/banco`) y **corpus** con `{{cifra}}` (`python -m agente.corpus finca-quinta`).

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
  Subcuentas: pendiente. D-023: `/negocios` da de alta un negocio nuevo sin código (runbook
  `docs/17-plug-and-play.md`); reglas de Safari en iPhone con test. **Cuello para revender**: un
  lector vinculado por servicio de Railway (`AGENTE_ESPACIO_VINCULADO`).
- **Finca Emiliano vinculado (2026-10-27, noche)** tras D-024 a D-026: el código de 8 se pedía en
  cada arranque (429 de WhatsApp por los redespliegues), el respaldo no enseñaba el QR, y el número
  propio salía "equivocado" (`str()` del JID). Hoy: QR siempre, código a pedido, botón "Generar QR
  nuevo", número por `.User` y confirmado con `get_me()`. **Regla**: no redesplegar el agente
  mientras un negocio vincula. **Siguiente sesión**: confirmar en el panel que el historial entró
  (si son 0, cerrar "ia" en el teléfono y volver a vincular), luego el taller
  (`/espacios/finca-quinta/banco` con la llave maestra): proponer perfil, que Mariana lo apruebe en
  Asistente, banco y 30 conversaciones en sombra. Color y foto se ponen en el alta. **Falta**: pedir a Finca
  Emiliano su foto original y el verde exacto de su volante, y subirlos desde su alta.
- **Historial de Finca Emiliano entró (2026-10-27)**: 11,463 mensajes, 701 chats (4,835 de texto,
  5,421 imágenes, casi todas del negocio: las tarifas viven en imágenes, la pasada de texto no las lee).
  Línea base al estilo de la vara de Gestor (n = 699 chats donde escribió el cliente): 410 (59%) solo
  recibieron plantillas; primera respuesta humana mediana 45 min, p90 ~25 h (n = 289); precio escrito
  en 68 chats, mediana 36 min. **La pasada del perfil no corre**: la llave de Anthropic de Railway no es
  de un workspace (400, pide `anthropic-workspace-id`). Arreglo en código: `ANTHROPIC_WORKSPACE_ID`.
  **Del dueño**: poner esa variable en Railway o cambiar a una llave de workspace; luego
  `POST /espacios/finca-quinta/simbiosis` con la llave maestra. "Entrenar" aquí es perfil citado +
  sombra + vara, no reentrenar pesos: una tarifa en los pesos es una cifra inventada mañana.
- **Desarrollo en local y enjambre listos, sin lanzar** (D-027, 2026-10-27): `python -m agente.local`
  baja la copia (tope 0, en sombra: cero API), saca la vara de pendientes y los lotes; el enjambre de
  Claude Code (`.claude/skills/enjambre/SKILL.md`) redacta la ronda; `subir` prueba contra producción y
  solo con `--de-verdad` (y el sí del dueño) quedan salidas **esperando aprobación**. Medido sobre el
  historial real: 276 sin responder = **143 esperan**, 78 solo medios, 55 no piden, 0 reclamos; 111 de
  las 143 nunca tuvieron respuesta de una persona. El panel ya cuenta con esa vara (221, sin los 55).
  Panel local con los datos reales: 0.1 s por página. Vía API, para comparar (tokens estimados): perfil
  USD 0.90–1.38, clasificación USD 0.15, 143 borradores USD 0.16. **Antes de la primera ronda con
  cifra**: perfil aprobado (en local con el enjambre o con la pasada de Opus). **Para que algo salga**:
  conector oficial; el lector vinculado no envía (D-018).
- **La vinculación sobrevive a los redespliegues** (medido 2026-10-27, dos redespliegues): la sesión vive
  en el volumen (`/data/espacios/<id>/vinculado/session.sqlite3`), igual que Gestor
  (`/data/whatsapp/session.sqlite3`); tras los dos, el historial seguía en 11,463 mensajes y el panel en
  "Conectado". Lo que sí desvincula: el botón "Generar QR nuevo" (borra la sesión a propósito) y pedir
  códigos de 8 en serie (429, D-024).
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
- Pruebas sin red: 374 de Python y 6 de `score.test.mjs`, en verde; cobertura de atlas + dataroom + satelite + agente 81.5% (piso 70).

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
- **Agente (sesión del calendario)**: mandar a Mariana `docs/20-hoja-para-mariana.md`; con sus enlaces
  iCal, darlos de alta y medir (`python -m agente.calendario bajar finca-quinta`).
- **Agente (sesión del cotizador)**: que Mariana confirme `docs/19-lista-de-precios.md` (lo a decidir y el
  rango de fin de año) y, con su sí, subir la propuesta (`python -m agente.local proponer finca-quinta
  datos/espacios/finca-quinta/lista_precios/propuesta.json --de-verdad`) para aprobarla en Asistente →
  Precios; el calendario de ocupación (siguiente sesión); rotar `TENANT_INTERNAL_TOKEN` (volvió a pasar
  por el chat el 2026-10-27, en el encargo de esta sesión).
- **Agente (sesión anterior)**: su calendario de ocupación; si quiere, subir el perfil del enjambre
  como propuesta (`python -m agente.local proponer finca-quinta <perfil.json> --de-verdad`); rotar
  `TENANT_INTERNAL_TOKEN` (volvió a pasar por un chat el 2026-10-27).

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
