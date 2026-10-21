# MEMORIA — DGED Systems (la puerta)

> Lee esto antes de tocar nada. Los agentes se descarrilan por falta de
> **contexto**, no de inteligencia: olvidan por qué se decidió algo, qué está
> prohibido y qué ya se midió. Esta carpeta cierra ese hueco.

## Qué es DGED (3 líneas)

Empresa mexicana de IA e investigación aplicada. Hoy vende **Atlas** (cribado
de sitios industriales con datos públicos). Mañana, productos de datos
espaciales; después, hardware. El orden no se invierte: cada fase la paga la
anterior.

## Los archivos

| Archivo | Para qué |
|---|---|
| `CONSTITUCION.md` | Invariantes no negociables y el test que hace cumplir cada una |
| `ESTADO.md` | Qué corre, qué está trabado y qué sigue. Lo único que caduca rápido |
| `FUENTES.md` | Catálogo de fuentes medidas con petición real: veredicto y valor observado (`herramientas/medir_fuentes.py`) |
| `CEMENTERIO.md` | Fuentes, componentes e ideas medidos y descartados, con fecha y por qué |
| `VISION.md` | Las tres fases de la empresa y los principios de trabajo |
| `../DECISIONS.md` | Decisiones de arquitectura y producto, append-only |
| `../docs/` | Arquitectura, MVP, fuentes, ontología, precios, riesgos, stack, plan 12 semanas |
| `../docs/15-agente-a-la-medida.md` | Producto 4 (D-016): especificación y orden de trabajo para la siguiente sesión |
| `../services/agente/` | Producto 4 en código (D-017): un espacio por cliente, en sombra de fábrica |
| `../docs/presentacion/` | Presentación del negocio en PDF |

## Tres reglas de oro

1. **Ningún número sin fuente que haya respondido.**
2. **Un hallazgo sin test es una nota.**
3. **Antes de proponer, revisa el cementerio.**

## De dónde viene esta forma

La estructura (`CLAUDE.md` que rutea, `MEMORY/` con constitución, estado y
cementerio, invariantes como tests) se tomó de `rasdg05/fq-bot` y
`rasdg05/Gestor-Morelos`, donde ya probó su valor. Aquí empieza chica a
propósito: crece cuando haya algo que recordar.
