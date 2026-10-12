# Plan de 30 días — calidad, despliegue y primeras ventas

Aprobado por el dueño el 2026-10-12. Lo que cambia se agrega abajo con fecha;
no se reescribe.

## La idea de despliegue

**Se vende el memo firmado; el software es cómo se produce.** Nadie le compra
USD 55,000 a un SaaS desconocido, pero sí a un equipo que entrega un análisis
defendible con fuente y fecha de corte (`04-entrega-precios.md`).

Tres capas, en este orden:

| Capa | Qué es | Quién la ve | Se cobra en |
|---|---|---|---|
| **Demo pública** | Los 10 sitios, mapa y fichas. Solo lectura, sin Oráculo, con tope por IP | Cualquier prospecto, ligada en cada correo | Nada: es la carta de presentación |
| **Espacio del cliente** | Sus sitios y escenarios, instantáneas congeladas, memo PDF, Oráculo con llave y tope | El cliente, con su llave | Comparativo, Screening, Operate |
| **Trabajo de fondo** | Refresca sequía cada quincena, recalifica, alerta si un sitio publicado se mueve más de 8 puntos | Nadie: avisa | Operate (USD 96,000/año) |

**Dónde:** Railway, igual que Gestor Morelos y fq-bot. Servicio web
(`Dockerfile`), Postgres con PostGIS y un volumen para la caché. No se pasa a
AWS o GCP hasta que un contrato lo exija.

## Semana 1 — seguridad y calidad (empezada el 2026-10-12)

- [x] `SAKBE_TOKEN` llega al contenedor; toda variable de `.env.example` pasa por
      `docker-compose.yml` (invariante IX con test).
- [x] Postgres solo en `127.0.0.1` y contraseña por variable (invariante X).
- [x] Oráculo detrás de `ATLAS_ACCESS_TOKEN` + `X-Atlas-Key`; sin llave, 503
      aunque haya clave de Anthropic (`atlas/access.py`, `test_access.py`).
- [x] Tope por IP: 30 calificaciones / 10 min y 20 preguntas / hora,
      configurables.
- [x] `/api/health` dice el commit que corre (`RAILWAY_GIT_COMMIT_SHA` o
      `GIT_COMMIT`) y si el Oráculo tiene clave y puerta.
- [x] CI: ruff, cobertura con piso (49.62% medido), `docker compose config`.
- [x] Dependabot (pip, Actions, Docker) y dependencias de desarrollo fijadas.
- [ ] Integrar lo de los agentes de fuentes, conectores y verificación.
- [ ] Desplegar la demo pública en Railway — **necesita acceso del dueño**.
- [ ] Prueba diaria contra las fuentes reales en CI (avisa el día que INEGI o
      CONAGUA cambian).

## Semana 2 — lo que va en un memo

- Instantáneas inmutables: cada calificación publicada queda con su fecha,
  versión del score y URLs; no se recalcula encima (`05-riesgos.md`).
- Memo PDF generado desde una instantánea, con la cláusula de "apoyo a la
  decisión" en castellano llano.
- Atlas Comparativo (D-011) como flujo: 2–3 predios, escenarios, memo.

## Semana 3 — el espacio del cliente

- Llave por cliente (no una sola llave global) y sus sitios aparte.
- Oráculo con tope por cliente.
- Alerta de cambio > 8 puntos, sin correo si no hay delta.

## Semana 4 — el piloto de demostración

- 12 sitios reales de Monterrey calificados en vivo, con su memo.
- Es lo que se enseña en las juntas con las tres primeras cuentas.

## Primeras ventas

Orden de `09-portafolio-90-dias.md`: agente de WhatsApp para PyMEs, Atlas
Comparativo (USD 15,000, D-011) y evaluación técnica independiente.

**Tres primeras cuentas (D-012):**

1. **Fibra Mty** — integra 343 naves de Fibra Macquarie y es emisora con
   reporte climático obligatorio: Comparativo y cribado de cartera.
2. **FIBRA Prologis** — compra en Monterrey, Toluca y Juárez: due diligence
   técnico de cada adquisición.
3. **Vesta** — desarrolla en el norte y el Bajío, los dos corredores de Atlas:
   Comparativo y Screening.

AMPIP es canal, y entra **después** del primer memo real.

## Lo que es del dueño

- Acceso a Railway (o conectar el repo él mismo) y un dominio.
- Claves INEGI (DENUE), SAKBÉ y Anthropic.
- El contacto con nombre en cada una de las tres cuentas.
- Si Gestor Morelos se usa con su nombre como caso del agente de WhatsApp.
