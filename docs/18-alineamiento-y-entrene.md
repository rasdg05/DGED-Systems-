# 18 — Alineamiento y entrene del agente con el rigor de Gestor (sesión pesada)

Fecha: 2026-10-27. Dirección del dueño: *"En gestor Morelos hice backtesting y
miles de pruebas. Quiero el mismo rigor aplicado aquí para alineamiento y
entrene del modelo en una sesión pesada de trabajo con opus en uso alto."*
Rama: **`claude/agente-a-la-medida`**. Primer negocio: Finca Emiliano
(`finca-quinta`).

## Qué significa "entrenar" aquí (no se reabre)

No se reentrenan pesos. Una tarifa aprendida en los pesos es una cifra
inventada el día que cambie (invariante XXXII; Gestor, `entrenamiento.py`: *"los
precios no se enseñan, se consultan"*). Entrenar es: **perfil citado + política
determinista + vara que mide contra la casa + banco adversario + backtest en
cada despliegue**. La sesión de Claude Code ES el modelo grande que lee y
propone (enjambre, D-027): **no se gasta API** salvo lo que se mida a
propósito y con tope.

## Lo que Gestor tiene y aquí falta (la lista de trabajo)

| Gestor (archivo) | Qué hace | Aquí hoy | Por hacer |
|---|---|---|---|
| `herramientas/vara.py` | universo; holdout sellado out-of-time 25% con embargo 7 d y purga por persona; CPCV 6/2 = 15 caminos; placebo barajado; puntaje con `COSTOS`; DSR por persona deflactado por intentos; PBO por CSCV; libro sellado con hash; bitácora `datos/vara/intentos.jsonl` | `sombra.medir`: holdout 25% sin embargo, sin purga, sin placebo, sin DSR | `agente/vara.py` + `python -m agente.vara` con TODO eso |
| `app/services/replay.py` | compara **jugadas**, no textos (cifra, pregunta:<dato>, persona, espera, acuse, saludo, explica, ubicación, opciones…); auditar `otra` | se compara parecido de texto (0.8) | taxonomía de jugadas del giro (abajo) y su clasificador, con `otra` medido |
| `app/services/backtest.py` | el código de hoy contra 14 días, en cada despliegue; regresión > 5 pts con n ≥ 30 avisa | no existe | `agente/backtest.py` y ruta del taller |
| `entrenamiento.py`, `corpus_entrenamiento.py` | exporta pláticas limpias a JSONL con `{{cifra}}`; mide `faltaba_al_cotizar` | no existe | exportar el corpus de Finca Emiliano (fuera de git) |
| `tests/` | 2,922 tests; cada error real entra como test antes de arreglarse | 165 del agente | cada hallazgo de la sesión, su test |
| `banco` (pass^k) | — | `agente/banco.py` con red team | crecer el banco con casos sacados de las pláticas reales |

## Datos medidos (2026-10-27, copia local)

- 11,463 mensajes, 701 pláticas, 2026-07-29 → 2026-10-27; 4,835 de texto, 5,421
  imágenes (las tarifas viven en imágenes: el texto no las ve).
- **691 momentos** (una persona del negocio contesta a un mensaje del cliente,
  sin contar las 9 plantillas de ≥ 20 usos) en **255 pláticas**. Holdout 25% =
  **173 momentos desde el 2026-10-15**. Con purga por persona y embargo, el
  desarrollo queda en ~450: alcanza para CPCV; por jugada, varias tendrán n < 30
  y **no concluyen**.
- Pendientes: 276 sin responder = 143 esperan, 78 solo medios, 55 no piden.
- Primera respuesta humana: mediana 45 min, p90 ~25 h (n = 289).

## Jugadas del giro (punto de partida, se corrige con datos)

`cifra` (dio precio) · `pide:fechas` · `pide:personas` · `pide:propiedad` ·
`pide:evento` · `disponibilidad` (sí/no hay fecha) · `info:capacidad` ·
`info:ubicacion` · `info:incluye` (alberca, mascotas, reglas) · `fotos` ·
`anticipo` (cómo apartar, cuenta) · `persona` · `espera` ("le confirmo") ·
`acuse` · `saludo` · `medio` (no se mide) · `otra`. Meta: `otra` < 10% en
desarrollo antes de confiar en el acierto (Gestor arrancó en 62 de 89 `otra` y
su 7% medía el clasificador, no al bot).

## Orden de trabajo de la sesión

1. **Arranque**: leer esta hoja, `MEMORY/` y `.claude/skills/enjambre/SKILL.md`.
   `add_repo rasdg05/gestor-morelos` y leer `herramientas/vara.py`,
   `app/services/replay.py`, `backtest.py`, `entrenamiento.py`,
   `docs/plan_alineamiento_cuantitativo.md`. **Se copian los métodos, no el
   código del giro** (placas no son fincas).
2. **Copia local**: `cd services/agente && python -m agente.local bajar finca-quinta`
   (necesita `AGENTE_URL` y `TENANT_INTERNAL_TOKEN`).
3. **Jugadas y clasificador** determinista, con tests por jugada sacados de
   mensajes reales (sin teléfonos en el repo).
4. **La vara** (`agente/vara.py`), con la bitácora de intentos en git solo con
   agregados (hash, n, métricas; test de que no lleva teléfonos ni textos).
   Línea base: la política de hoy (sin perfil → todo `persona`). Placebo
   primero: si no cae al azar, la vara no mide nada.
5. **Perfil en local con el enjambre** (sin Opus por API): cada renglón con cita
   literal; `python -m agente.local proponer finca-quinta perfil.json` hasta que
   los descartados se expliquen. Subirlo con `--de-verdad` es del dueño.
6. **Política y voz contra la vara**, solo en desarrollo. Cada variante es un
   intento en la bitácora. El holdout se abre **una vez por candidato** y queda
   escrito.
7. **Donde el bot iría al modelo, la jugada es `ia`** (como Gestor). Si se quiere
   medir la redacción, el enjambre redacta sobre una muestra de desarrollo
   (n ≥ 30) y se califica por jugada; el holdout no se toca para eso.
8. **Banco**: subir casos reales al banco (pass^k, cero errores caros).
9. **Backtest por despliegue** y ruta del taller para verlo.
10. **Corpus** con `{{cifra}}` en `datos/espacios/finca-quinta/corpus/` (fuera de git).
11. Cerrar: ESTADO, DECISIONS (D-028…), invariantes nuevas con su test,
    `herramientas/verificar.sh` en verde, push a la rama.

## Compuertas para encender algo (no se negocian)

- `sin_cifra` solo si en el holdout: puntaje con costo por encima de la línea
  base con DSR ≥ 0.95, placebo en el azar, cobertura reportada junto al
  acierto, cero errores `grave`, banco pass^k = 1 y n ≥ 30 por jugada que se
  enciende. Lo enciende el dueño, no la sesión.
- La cotización siempre espera el sí de una persona (XXXIII).
- Nada sale sin conector oficial; el lector vinculado solo lee (XL).

## Reglas de la sesión

- **Cero llamadas a la API** salvo medición explícita con `tope_usd_mes`; la copia
  local trae tope 0.
- **No redesplegar mientras un negocio vincula**; la sesión vive en el volumen y
  sobrevive a los redespliegues (medido tres veces el 2026-10-27).
- Ningún dato de cliente final en git (`**/datos/espacios/`, XXXIX/XLVII).
- n < 30 no concluye. Un hallazgo sin test es una nota.

## Lo que es del dueño

- `ANTHROPIC_WORKSPACE_ID` en Railway (o llave de workspace) si se quiere la vía API.
- Rotar `TENANT_INTERNAL_TOKEN` (pasó por un chat).
- La lista de precios de Finca Emiliano como documento (hoy está en imágenes).
- Que Mariana apruebe el perfil en Asistente; la orden escrita para la primera ronda.

## Hecho en la sesión (2026-10-27) — D-028 a D-030

```bash
cd services/agente
python -m agente.local bajar finca-quinta                      # copia local (tope 0, en sombra)
python -m agente.vara medir finca-quinta --variante base       # desarrollo; el holdout no se abre
python -m agente.vara medir finca-quinta --variante p --perfil perfil.json --contra base
python -m agente.vara medir finca-quinta --variante p --perfil perfil.json --redacciones r.json --contra base
python -m agente.vara medir finca-quinta --variante p --perfil perfil.json --contra base --abrir-holdout   # UNA vez
python -m agente.corpus finca-quinta                           # corpus {{cifra}} y faltaba_al_cotizar
```

| Paso | Dónde | Medido |
|---|---|---|
| Jugadas y clasificador | `agente/jugadas.py` (`finca-1`) | `otra` 1.8% en dev; 36/40 contra etiqueta a mano ciega |
| La vara | `agente/vara.py`, `vara/intentos.jsonl` | 1,003 momentos · holdout 251 desde 2026-10-15 · dev 498 (209 pláticas) · oráculo 100 → 13.3% con placebo |
| Perfil en local | enjambre de 4 agentes, solo desarrollo | 285 renglones citados, 0 descartados; **no se subió** |
| Redacción | enjambre de 3 agentes, 60 momentos de dev | candados del turno: 12 de 60 detenidos (9 por ¿, 3 por "dos") |
| Banco | `banco.CASOS_REALES` (12) | pass^k 1.0, cero caros (cazó "anotado grax") |
| Backtest | `agente/backtest.py`, al arrancar y en el taller | 349 momentos (12–26 oct), sin regresión |
| Corpus | `agente/corpus.py` (fuera de git) | 675 pláticas, 250 montos tapados |

**Resultado**: base 0.30 (dev y holdout); perfil del enjambre 0.115 dev / 0.097 holdout; con
redacción 0.28 en su submuestra. DSR 0.0: **nada se enciende**. Lo que mueve la vara no es redactar
mejor sino lo estructural: la lista de precios (precio por propiedad y tamaño de grupo) y el
calendario (31 momentos de disponibilidad en dev). `faltaba_al_cotizar`: propiedad 96%, personas
15%, fechas 8% (n = 202).

**Lecturas de la vara que no se deben olvidar**
- A_pol de la base es 100% porque la política acepta pasarlo todo: la alineación se compra con
  silencio. Por eso se reporta junto a la cobertura y el puntaje con costos, y el placebo no cae con
  un agente constante (y sí con el oráculo).
- El backtest mira los últimos 14 días, que se enciman con el holdout: es alarma de despliegue, no
  material para afinar.
- La huella del candidato es el código que decide + el perfil; editar la vara no reabre el holdout.

**Siguiente sesión**: con la lista de precios del dueño, un cotizador que elija propiedad por grupo
(y la regla con su origen en el documento), medido como intento nuevo; holdout nuevo cuando entren
momentos de producción posteriores al 2026-10-27 (el viejo pasa a desarrollo).
