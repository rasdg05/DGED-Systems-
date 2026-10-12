# CLAUDE.md — DGED Systems

> Se carga en CADA sesión. Por eso es corto: **rutea, no repite**.
> `AGENTS.md` es un enlace a este archivo. El contexto largo vive en `MEMORY/`.

## Qué es esto

DGED Systems es la empresa. Su primer producto cobrable es **Atlas**: cribado
multi-riesgo de sitios industriales en el norte y el Bajío con fuentes públicas
de México (INEGI, SMN/CONAGUA). FastAPI + MapLibre + Postgres/PostGIS opcional.
La meta de largo plazo (espacio) está en `MEMORY/VISION.md` y **no** cambia lo
que se construye hoy.

## Antes de tocar nada

1. `MEMORY/00-INDICE.md` — la puerta (60 s).
2. `MEMORY/CONSTITUCION.md` — lo que no se rompe.
3. `MEMORY/ESTADO.md` — qué corre, qué está trabado, qué sigue.
4. `MEMORY/CEMENTERIO.md` — fuentes e ideas ya medidas y descartadas.
5. `DECISIONS.md` — por qué está así (append-only).

## La regla que manda

**Un hallazgo sin invariante que lo haga cumplir es una nota, no un arreglo.**
Si cierras algo, pregúntate qué test lo impide volver. Si la respuesta es
"acordarse", no está cerrado. (Lección heredada de fq-bot.)

## Verificar antes de push

```bash
python3 -m pytest -q services/api tests
node --test packages/score/score.test.mjs
```

CI corre lo mismo en cada push (`.github/workflows/ci.yml`).

## Reglas de trabajo

- **Ningún dato inventado.** Un factor sin respuesta de la fuente no entra al
  número; se muestra como ausente.
- **Una fuente se mide antes de escribir su código**: ¿responde desde un
  servidor?, ¿cada cuándo publica?, ¿trae dato de verdad? Lo que no pasa va a
  `MEMORY/CEMENTERIO.md`, no a producción.
- **n < 30 no concluye**, ni a favor ni en contra.
- `DECISIONS.md` y el cementerio son append-only: no se reescribe, se agrega.
- Código vendido (`services/api/static/maplibre-gl.*`) no se edita a mano.
