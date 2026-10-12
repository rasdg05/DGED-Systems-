# Estado — 2026-10-12

> Lo único de la memoria que caduca rápido. Al cerrar trabajo, actualízalo.

## Corre

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
- Pruebas sin red: 69 de Python y 6 de `score.test.mjs`, en verde.

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

1. Desplegar la demo en Railway: mide Docker y el SMN desde una red normal.
2. Calificar los 10 sitios con 0.2.0 y actualizar la tabla de verificación.
3. Pedir las claves INEGI (DENUE), SAKBÉ y Anthropic.
4. Holgura eléctrica por corredor firmada contra PRODESEN (`DECISIONS.md` D-003).
5. Mercado y portafolio a 90 días (`docs/08-mercado.md`,
   `docs/09-portafolio-90-dias.md`): agente WhatsApp, Atlas Comparativo (USD 15k,
   D-011) y evaluación técnica; P4 solo tras medir CENAPRED/CFE/acuíferos.
6. Primeras cuentas (D-012): Fibra Mty, FIBRA Prologis, Vesta.

## Lo que es del dueño

- Claves INEGI (DENUE), SAKBÉ y Anthropic, y `ATLAS_ACCESS_TOKEN`.
- Acceso a Railway y un dominio para la demo pública.
- El contacto con nombre en Fibra Mty, FIBRA Prologis y Vesta.
- Quién revisa los primeros diez sitios (alguien que haya trabajado parque en NL).
- El punto de `salinas-hofusan` cae en el polígono de General Zuazua, no de
  Salinas Victoria: ¿se mueve el punto o se renombra?
