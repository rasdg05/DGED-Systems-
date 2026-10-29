# 21 — Corrida GM del agente a la medida (bitácora)

> Del dueño (2026-10-29): *"Quiero que hagas una corrida pesada como las de GM GM
> del repo gestor Morelos aplicadas al mejoramiento del sistema: entrenamiento
> especializado a fondo, corrección de errores y alineamiento pesado (...) y no
> pares de construir varias horas."*
>
> Método: `rasdg05/gestor-morelos` → `docs/gm_gm.md` (runbook) y
> `docs/bitacora_gm.md`. Se copian las reglas de la corrida larga, no el giro.

## Reglas de la corrida (de Gestor, ajustadas)

1. No se detiene al terminar un bloque: pasa al siguiente. Lo del dueño se junta al final.
2. La llave maestra vive solo en la sesión (`export` en el mismo comando). Nunca en
   archivo, commit, test, log ni documento. Al cerrar: rotarla.
3. Cada bloque se cierra entero: corpus (casos reales) **antes** de arreglar → test →
   suite completa → `herramientas/verificar.sh` → push a la rama (Railway despliega)
   → `/health` con el commit → backtest de producción del commit → línea aquí.
4. Una línea al empezar y al cerrar cada bloque: hora, bloque, commit, métrica antes →
   después y n. Si el contexto se compacta, se continúa desde el último bloque cerrado.
5. **La vara no se afloja**: holdout out-of-time una vez por candidato, DSR, placebo,
   cobertura junto a la alineación. **Máximo 4 intentos por universo**, cada uno
   registrado antes de medir (hipótesis, segmento, efecto esperado).
6. Dos puertas: un **arreglo de lectura** (un caso real que el sistema no leía) pasa con
   *sin regresión*; un **cambio de política** necesita la vara completa o un
   experimento en vivo. No se mezclan en un candidato.
7. Nada sale a clientes desde la sesión: lo que el enjambre redacte queda en local y
   subirlo (`--de-verdad`) es del dueño.
8. Teléfonos solo enmascarados (`…1234`); ningún texto de cliente con nombre en git.

## Foto de partida (B0, 2026-10-29 00:30 UTC)

- Producción `0fffaad` (según el backtest; `/api/health` decía `"commit": ""`).
- Historial: **11,975 mensajes** (11,463 el 27-oct), último 2026-10-28 18:09 (CDMX).
- Perfil **v3 activo** (lista de precios v2 de Mariana). Backtest de producción
  (14 días, n = 344): puntaje **0.106**, A_pol 17.2%, a la IA 71.5%, caros 0. Era
  0.30 hasta `3877f8c`; cayó a 0.122 en `8af42e5` con `regresion: true` y el siguiente
  despliegue (`a3c763b`, el mismo agente) dijo `false`.
- Pendientes (`/pendientes.json`): 268 sin responder = 123 esperan (67 nunca tuvieron
  persona), 82 solo medios, 63 no piden, 0 reclamos.
- Semáforo (clientas sin administradoras): 194 rojos, 121 ámbar, 119 para seguimiento.
- **Rondas enviadas**: 138 (128 del 27 + 10 del 28), las 138 en el historial.
  **Contestaron 26 (18.8%)**; de esas, **8 recibieron respuesta de una persona**
  (mediana 0.8 h, p90 3.0 h) y **18 siguen sin respuesta** a ~26 h. En el semáforo
  quedan en los lugares 170–192 de 194 rojos: el rojo se ordena por horas de espera y
  arriba están pláticas de hasta 21 días. El reporte de las 9 y 19 enseña los 5 de
  arriba: **nunca** las respuestas frescas a la ronda.

## Bloques

| Bloque | Qué | Sale con |
|---|---|---|
| B0 | arranque: producción, backtest, pendientes, rondas | esta foto |
| B1 · instrumentación honesta | commit en `/health`; el backtest compara contra una referencia que no se mueve con una regresión; lo que pasa al modelo se cuenta como *sin medir* | tests y backtest re-medido |
| B2 · la respuesta a la ronda | lo que contesta un cliente a nuestro seguimiento va primero en semáforo y reporte; lecturas de cierre y aplazamiento que faltaban (corpus de la ronda) | rojos frescos arriba; casos al corpus |
| B3 · el clasificador de pendientes | doble etiquetado ciego (agentes) de los 268 pendientes; kappa; desacuerdos al dueño | precisión de `espera` y `no_pide` con n |
| B4 · política contra la vara | por pérdida esperada por jugada, intentos registrados (≤ 4) | DSR / holdout o "probado y no" |
| B5 · banco | casos reales nuevos (ronda y mesa) | pass^k 1.0, 0 caros |
| B6 · cierre | ESTADO, DECISIONS, CONSTITUCIÓN, verificar, push, lo del dueño | reporte |

## Bitácora

- **2026-10-29 00:30 · B0 abierto y cerrado** · foto arriba.
- **B1 · abierto** · lo encontrado: (1) `/health` leía `GIT_COMMIT`, que Railway no pone;
  (2) la caída 0.30 → 0.106 **no es un agente peor**: de los 349 momentos, 251 pasaron
  de "a una persona" a "iría al modelo" (sin medir, 0.0); en los 98 que los dos deciden
  sin modelo el puntaje **sube** 0.30 → 0.374 (A_pol 100 → 60: la base "alinea"
  pasándolo todo); (3) la alarma se borraba en el despliegue siguiente.
