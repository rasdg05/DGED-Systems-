# Estado — 2026-10-12

> Lo único de la memoria que caduca rápido. Al cerrar trabajo, actualízalo.

## Corre

- **Atlas live** en `main` (`ed7752e`): FastAPI, mapa MapLibre 5.6.1, diez
  sitios demo (5 norte, 5 Bajío), score `atlas-live-0.1.0`.
- Pruebas sin red: `test_score.py` (8) y `score.test.mjs` (6) en verde.

## No medido todavía

- **No se ha levantado con `docker compose up`** desde este repo. El criterio
  de "menos de 40 minutos" está escrito, no comprobado.
- **No se ha probado contra las fuentes en vivo** desde esta copia (INEGI WMS,
  Catálogo Único, MunicipiosSequia.xlsx).
- Sin `INEGI_TOKEN` ni `SAKBE_TOKEN`: DENUE conteo y rutas no entran al número.

"No medido" no es "medido y no funcionó".

## Sigue

1. Levantar con Docker y anotar el tiempo real aquí.
2. Una calificación en vivo por corredor; guardar las URLs de `/api/examples`.
3. Pedir las claves INEGI (DENUE) y SAKBÉ.
4. Holgura eléctrica por corredor firmada contra PRODESEN (`DECISIONS.md` D-003).
5. Mercado y portafolio a 90 días (`docs/08-mercado.md`, `docs/09-portafolio-90-dias.md`): primero agente WhatsApp, Atlas Comparativo (USD 15k, requiere D-009) y evaluación técnica; P4 solo tras medir CENAPRED/CFE/acuíferos.

## Lo que es del dueño

- Claves INEGI y SAKBÉ (se piden con nombre y correo).
- Quién revisa los primeros diez sitios (alguien que haya trabajado parque en NL).
- Primer prospecto para el piloto de Atlas Screening.
