# Estado — 2026-10-12

> Lo único de la memoria que caduca rápido. Al cerrar trabajo, actualízalo.

## Corre

- **atlas-live-0.2.0** (integrado en `claude/dged-systems-ai-space-f8pm53`, D-009): cuatro capas sin clave.
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
- **Oráculo** (`POST /api/oracle`, D-010): preguntas en lenguaje natural
  contestadas solo con herramientas del Atlas; dormido sin `ANTHROPIC_API_KEY`
  (503). Probado con cliente simulado (`test_oracle.py`, 16); **no medido
  contra la API real** todavía.
- **Semana 1 del plan de 30 días** (`docs/10-plan-30-dias.md`): Oráculo con
  llave (`ATLAS_ACCESS_TOKEN`) y tope por IP, compose sin fugas, `/api/health`
  con commit, CI con ruff, cobertura (piso 59, medido 60.01%) y Dependabot.
- Pruebas sin red: 60 de Python y 6 de `score.test.mjs`, en verde.

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
5. Mercado y portafolio a 90 días (`docs/08-mercado.md`, `docs/09-portafolio-90-dias.md`): primero agente WhatsApp, Atlas Comparativo (USD 15k, aprobado en D-011) y evaluación técnica; P4 solo tras medir CENAPRED/CFE/acuíferos.
6. Primeras cuentas (D-012): Fibra Mty, FIBRA Prologis, Vesta.

## Lo que es del dueño

- Claves INEGI y SAKBÉ (se piden con nombre y correo).
- Quién revisa los primeros diez sitios (alguien que haya trabajado parque en NL).
- El contacto con nombre en Fibra Mty, FIBRA Prologis y Vesta.
- Acceso a Railway y un dominio para la demo pública.
- Clave de Anthropic y `ATLAS_ACCESS_TOKEN` para prender el Oráculo.
