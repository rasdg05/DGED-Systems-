# 19 — Lista de precios de Finca Emiliano y cotizador por grupo

Fecha: 2026-10-27. Encargo del dueño: *"Arma el cotizador por grupo con la lista
de precios. La idea es que tú reconozcas la data de los mensajes y hagas la
lista de cotización basado en cotizaciones que el negocio ya da actualmente."*
Rama `claude/agente-a-la-medida`. Cero llamadas a la API; nada subido a producción.

## De dónde sale la lista

No hay lista escrita: vive en la cabeza de Mariana y en imágenes. Lo que sí hay
son **217 cotizaciones escritas a 177 pláticas** (2026-07-29 → 2026-10-27).
`agente/lista_precios.py` las lee sin modelo:

- **Propiedad**: la que nombra el precio o la última que la casa *presentó* en esa
  plática (*"Somos Finca Emiliano. Capacidad para 37"*, *"Quinta Emiliano es
  nuestra opción"*, *"Solo tengo la quinta"*). La bienvenida lleva el nombre del
  negocio y no presenta nada.
- **Grupo**: el que dice el precio (*"para 37 personas"*) o lo último que el
  cliente dijo de cuántos son (`agente/lectura.py`: *"8 adultos y 4 niños"* = 12;
  *"20"* a secas solo si la casa acababa de preguntar).
- **Unidad**: la noche o el fin de semana (viernes a domingo), escrita o por las
  fechas del cliente. **Temporada**: por las fechas del cliente.
- **Escalones**: por propiedad × unidad × temporada, programación dinámica sobre
  los tamaños de grupo: se eligen los cortes con los que más cotizaciones de la
  casa coinciden, pagando un escalón de más, con montos que no bajan al crecer el
  grupo. **Ningún precio se promedia**: el de la lista es uno que la casa escribió.
- **Entra** un escalón si su monto ganó en ≥ 60% de las veces y en ≥ 2 pláticas.
  Si no, queda **"a decidir"**: el cotizador no lo salta (no le cobra a 12 lo de 20).

Cada renglón trae la cita literal del negocio con el monto y, si el grupo lo dijo
el cliente, la cita del cliente que lo prueba (`origen.grupo`, revisada por
`perfil.validar`). Validada contra el historial: **21 reglas y 1 temporada, 0 descartadas**.

## La lista leída (para que Mariana la confirme)

**Finca** (9 habitaciones, hasta 37–40 personas), temporada normal, **el fin de semana**:

| Grupo | Habitaciones | Precio | n | Acuerdo | Otros montos que dio |
|---|---|---|---|---|---|
| 11 a 13 | 4 | $12,000 | 2 | 100% | |
| 14 a 19 | | $20,000 | 5 | 100% | |
| 20 | 6 | $22,000 | 7 | 71% | 25,000 · 28,000 |
| 23 a 25 | 6 | $25,000 | 7 | 86% | 30,000 |
| hasta 30 | | $30,000 | 8 | 100% | |
| 35 a 37 | | $35,000 | 22 | 100% | |
| 39 a 40 | | $38,000 | 5 | 60% | 20,000 · 35,000 |

**Quinta** (5 habitaciones, hasta 20 personas), **la noche**:

| Temporada | Grupo | Precio | n | Acuerdo |
|---|---|---|---|---|
| normal | 17 a 20 | $10,000 | 17 | 94% |
| fin de año | 9 a 10 | $8,000 | 2 | 100% |
| fin de año | 13 a 20 | $10,000 | 50 | 96% |

**Las dos casas**, 37 a 50 personas: $45,000 el fin de semana (n = 3, 67%).

**Extras**: alberca climatizada de la finca $2,000 el día (n = 4); de la quinta
$900 el día (n = 4, una vez 1,000); visitas $100 por persona (n = 3).
**Anticipo**: no entra solo (la casa escribe "50%" pocas veces como número).
**Estancia mínima en fin de año**: 3 noches (27 veces, 96%; una vez dijo 4).

**Temporada "fin de año" observada: noches del 23-dic al 1-ene — a confirmar.**
Es el rango de las estancias a las que la casa les escribió *"mínimo 3 noches"* o
*"temporada alta"*; la casa nunca escribió dónde empieza ni dónde acaba.

### A decidir por el dueño (sin acuerdo en lo que ya cotizó)

| Qué | Lo que la casa ha dado |
|---|---|
| Quinta, temporada normal, 5 a 16 personas, la noche | 5,000 (7 de 14) · 7,000 · 6,000 · 5,500 · 4,500 · 9,000 · 3,000. Mariana (2026-10-27, doc 20): "podría" 5,000 para 6 con 3 habitaciones, sin unidad |
| Quinta, el fin de semana (5 a 20) | 12,000 (3 de 8) · 6,000 · 8,000 · 9,000 · 10,000 · 15,000. Se le preguntó el 2026-10-27 y no contestó esta parte. **2026-10-28: 12,000** (doc 20, segunda vuelta) |
| Finca, una noche (15 a 40) | 15,000 (2 de 4) · 16,000 · 20,000. Mariana (2026-10-27, doc 20): para 25 "podría variar si 12,000 o 15". **2026-10-28: 15,000** (doc 20) |
| Finca, fin de año, la noche | 17,000 (n = 1) |
| Las dos casas, una noche (50) | 22,000 (n = 1) |
| Semana Santa, puentes, Navidad antes del 23 | sin cotizaciones con fechas |

## El cotizador por grupo (`cotizador.cotizar_grupo`)

El cliente no dice la propiedad (96% de las cifras de la casa, D-030): la elige el
grupo. Con fechas, total de la estancia (viernes a domingo al precio de fin de
semana; si no, por noche); sin fechas, el precio de lista del grupo. Cotiza la
propiedad de la que se habla si tiene precio para ese grupo; si no, las que sí.
"Las dos casas" solo si el grupo no cabe en una. Una temporada con tabla no cae a
la normal; una estancia que cruza dos temporadas, o por debajo del mínimo, va a
una persona. En el turno (`agente.por_grupo`, sin modelo): entra si el cliente
pide precio (o da su grupo después de haberlo pedido); sin grupo pregunta
*"Para cuántas personas?"* (como la casa); apartado, eventos, mesas y horas no se
cotizan como hospedaje; la alberca se contesta con el precio de su casa. **Toda
cifra espera el sí de una persona** (XXXIII) y el canal no saca una cifra sin
aprobación aunque falte la marca.

## Medido en la vara (`vara/intentos.jsonl`, D-033)

| intento | dev puntaje | holdout | monto igual a la casa | DSR |
|---|---|---|---|---|
| base (todo a una persona) | 0.300 | 0.300 | — | — |
| grupo-1: entra con grupo o fechas | 0.333 | — | 29% (n = 48) | 0.98 |
| grupo-2: propiedad de la plática, unidad, extras fuera | 0.334 | — | 35% (n = 26) | 0.0 |
| grupo-3: + dar datos que la casa pidió dispara | **0.289** | — | 40% (n = 48) | 0.0 |
| grupo-4: sin eso, + `[otro]` no esconde el texto | 0.333 | — | 41% (n = 29) | 0.0 |
| **grupo-5** (candidato) | **0.339** | **0.334** | dev 34% (n = 35) · holdout **67% (n = 18)** | 0.0 |

La lista de cada plática se arma **sin esa plática** y solo con desarrollo; con
`--tope-cero`, lo que iría al modelo va a una persona (lo que hace un espacio con
tope 0). Lectura: el cotizador mejora a la línea base en desarrollo y en el
holdout (+0.034, PSR 0.997, cero errores caros), pero **no pasa la compuerta**:
con 11 intentos la deflación pide un Sharpe de 0.99 y da 0.23. El A_pol del
holdout (90.0) queda fuera del IC de desarrollo. **Nada se enciende.** Lo que
limita: la casa negocia (un grupo de 20 recibió 20, 22 y 25 mil), presenta con
fotos antes de dar precio, y 31 momentos de desarrollo son de disponibilidad
(el calendario, siguiente sesión).

## Cómo se repite

```bash
cd services/agente
python -m agente.lista_precios finca-quinta        # lista.json y propuesta.json en datos/ (fuera de git)
python -m agente.vara medir finca-quinta --variante <x> --lista-de-precios --tope-cero --contra base
python -m agente.local proponer finca-quinta datos/espacios/finca-quinta/lista_precios/propuesta.json   # prueba local
# --de-verdad solo con el sí del dueño: queda como versión por aprobar en Asistente → Precios
```

## Lo que es del dueño

- Confirmar o corregir la lista con Mariana, sobre todo lo **a decidir** y el
  rango de **fin de año**. Con eso, subir la propuesta (`--de-verdad`) y que ella
  la apruebe en Asistente.
- El calendario de ocupación (siguiente sesión).
