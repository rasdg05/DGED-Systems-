# Estado — 2026-10-12

> Lo único de la memoria que caduca rápido. Al cerrar trabajo, actualízalo.

## Corre

- **Atlas live** en `main` (`ed7752e`): FastAPI, mapa MapLibre 5.6.1, diez
  sitios demo (5 norte, 5 Bajío), score `atlas-live-0.1.0`.
- **Califica en vivo, medido 2026-10-12**: 10 de 10 sitios contra INEGI
  (Catálogo Único, WMS uso de suelo e inundación) y el libro del SMN (corte
  2026-09-30), los diez publicables, 0 errores, ~2 s por sitio. Scores de
  70.8 a 83.0. Detalle y tabla: `docs/verificacion-2026-10-12.md`.
- **Docker, medido 2026-10-12**: `/api/health` en 8080 a los 39 s de
  `docker compose up --build` (más ~20 s de imágenes), Postgres/PostGIS sano y
  10 filas en `atlas_score` tras calificar. Medido con un override del sandbox
  (CA del proxy, red del host); ver bloqueos.
- Pruebas sin red: `test_score.py` (8), `test_conagua.py` (4),
  `test_inegi_flood.py` (3), `test_reintento_sequia.py` (2), invariantes y
  `score.test.mjs` (6) en verde.
- Arreglado en la verificación: la página de error del SMN ya no tumba el
  arranque; la celda vacía del SMN es "sin sequía" del último corte (antes se
  reportaba la última categoría vieja: 4 de 10 sitios cambiaron de número);
  calificar reintenta el SMN; una respuesta rara del WMS ya no cuenta como "no
  inundable".

## Bloqueos (con causa)

- **`docker compose up --build` tal cual no se pudo correr desde el sandbox**:
  Docker Hub 429 (límite anónimo) y `pip` con `CERTIFICATE_VERIFY_FAILED` por
  el proxy que intercepta TLS. Causas de la red, no del proyecto. Falta
  medirlo tal cual desde una red normal.
- **El SMN es intermitente desde un centro de datos**: 3 de 12 descargas
  entregaron el libro; las otras, una página de WAF con HTTP 200 (n=12, no
  concluye tasa). Con el arreglo el API levanta igual y reintenta al calificar.
- Sin `INEGI_TOKEN` ni `SAKBE_TOKEN`: DENUE conteo y rutas no entran al número.

"No medido" no es "medido y no funcionó".

## Sigue

1. Correr `docker compose up --build` tal cual en una máquina sin proxy y
   anotar el tiempo.
2. Medir el SMN desde otra red (¿el WAF es por IP de centro de datos?).
3. Pedir las claves INEGI (DENUE) y SAKBÉ.
4. Holgura eléctrica por corredor firmada contra PRODESEN (`DECISIONS.md` D-003).

## Lo que es del dueño

- Claves INEGI y SAKBÉ (se piden con nombre y correo).
- Quién revisa los primeros diez sitios (alguien que haya trabajado parque en NL).
- El punto de `salinas-hofusan` cae en el polígono de General Zuazua, no de
  Salinas Victoria: ¿se mueve el punto o se renombra?
- Primer prospecto para el piloto de Atlas Screening.
