# Estado — 2026-10-12

> Lo único de la memoria que caduca rápido. Al cerrar trabajo, actualízalo.

## Corre

- **atlas-live-0.2.0** (rama `agent/conectores`, D-009): cuatro capas sin clave.
  USGS (sismos M4+ 100 km / 50 años) y OSM vía férrea **puntúan si responden**
  (0.08 y 0.10); NASA POWER (lluvia, días > 35 °C) y la subestación OSM (nombre,
  voltaje del tag, km) **se muestran y no puntúan**. Pruebas: `test_capas.py` (18).
- Calificado en vivo el 2026-10-12 con uvicorn: El Marqués 68.2 (sismo 62, M5.3
  de 1979; vía Ferromex Línea B a 2.51 km; subestación Conín 230 kV a 2.92 km;
  575 mm/año, 2 días > 35 °C). Apodaca: primer intento Overpass falló en las tres
  instancias y el número salió sin vía (76.9, cobertura 0.6); el segundo contestó
  `maps.mail.ru` → 78.5 (vía a 0.93 km, subestación 115 kV a 2.38 km). n = 2: no concluye nada del modelo.

- **Atlas live** en `main` (`ed7752e`): FastAPI, mapa MapLibre 5.6.1, diez
  sitios demo (5 norte, 5 Bajío), score `atlas-live-0.1.0`.
- Pruebas sin red: `test_score.py` (8) y `score.test.mjs` (6) en verde.

## Bloqueos vivos

- **SMN `MunicipiosSequia.xlsx` desde este servidor (2026-10-12)**: responde 200
  con una página HTML "This page can't be displayed". Ya no tumba el arranque, pero
  **sin sequía ningún sitio es publicable**. Medir desde otra red antes de concluir.
- **Overpass**: solo `maps.mail.ru` contesta, con 504 a ratos y 10–50 s por consulta.
  Una caída deja vía y subestación ausentes (se ve en `evidence.osmAttempts`).

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

## Lo que es del dueño

- Claves INEGI y SAKBÉ (se piden con nombre y correo).
- Quién revisa los primeros diez sitios (alguien que haya trabajado parque en NL).
- Primer prospecto para el piloto de Atlas Screening.
