# 16 — Plan del ecosistema: qué se toma de cada repo y objetivos

Fecha: 2026-10-30. Revisión de los 18 repos de `rasdg05` y del zip
`rasdg-field-detector` que mandó el dueño. **Es una propuesta**: nada de aquí es
decisión hasta que entre a `DECISIONS.md`, y ningún precio nuevo cambia D-006,
D-011 ni D-014.

Reglas que respeta este documento:

- Se toma **práctica y código probado**, no marcas ni promesas. Lo que no está
  medido se dice "no medido".
- Ninguna proyección de ingresos: con n = 0 clientes no hay tasa de cierre.
- Hardware sigue fuera del presupuesto hasta que la fase 1 tenga clientes que
  paguen (`MEMORY/VISION.md`, constitución).

---

## 1. Inventario

| Repo | Qué es hoy | Qué le sirve a DGED | Veredicto |
|---|---|---|---|
| `fq-bot` | Bot de señales (vivo) + **Marea** (mercados de predicción) | La vara: `tools/validation_gate.py` (DSR/CPCV/PBO), ledger con cadena SHA-256 (`execution.py`), frescura de dato (`tools/fetch_cvd.py`); de Marea, `domain/bitacora.ts` y `domain/sha256.ts`, `settlement.onRead` (frescura L8), el juez con Claude que **no mueve dinero** (R-081) | **Tomar práctica** |
| `Gestor-Morelos` | Gestoría vehicular en producción, 4,137 tests | Núcleo del agente: guardrails de cifra, cotizador separado de la IA, voz citada, banco de casos con *pass^k*, memoria de hechos con fuente, sombra contra la casa, `/internal/tiempos` | **Tomar** (Producto 4, D-016) |
| `gestor-personal` | "El cerebro": asistente/analista en Telegram que lee a los demás | Patrón para que DGED mida su propio embudo (propuestas, cuentas, tiempos) y para el reporte mensual del P1 | **Tomar patrón** |
| `RASMECHANIC` (TALLER-OS) | Paquete de arranque para el sistema de un taller europeo en Cuernavaca; 14 reglas duras, caso real X6, sin código | Segundo perfil de giro para Producto 4: "piezas y mano de obra siempre separadas" es una regla de cotización como dato, justo lo que pide D-016. Diseño de PDF con verificación de recorte (`docs/03`) | **Tomar como vertical** |
| `proyecto-blue-ocean` | Backend FastAPI de rentas cortas (propiedades y embarcaciones, Riviera Maya), con tests | Modelos `listing`, `availability`, `booking`, `addon`, `payment`: son los objetos `Propiedad`, `Tarifa`, `Temporada`, `Reserva` de la demo de finca y quinta (`docs/15`) | **Tomar modelos** |
| `Mrk.5-Blue-Beam` | Marketplace de autos (Next.js), en fusión hacia Gestor-Morelos | Abstracción de pagos `PaymentProvider` (Mercado Pago, webhook verificado): sirve para cobrar la mensualidad del P1 | **Referencia** |
| `regime-lab`, `fib-features-ml`, `numerai-crypto` | Arneses públicos de evaluación honesta; los tres reportan resultados nulos o modestos tal cual | Portafolio citable del P5 (auditoría de modelos): "reportamos el nulo" es la prueba de oficio. `regime-lab` ya trae `railway.json` | **Tomar como muestra pública** |
| `web-hunter` | Firma de ciberseguridad (docs, metodología con autorización firmada) | Método para revisar la seguridad propia de Atlas y del cuarto de datos antes del primer cliente; pieza de seguridad dentro del P3 | **Tomar método** |
| `CRM-Whitelabel` (SaluChain) | Expedientes médicos en cadena + token SALU + "Dr. Salu" que apoya diagnóstico | Nada por ahora. Datos de salud (datos sensibles, LFPDPPP), software que apoya diagnóstico (COFEPRIS) y un token (régimen de activos virtuales): tres frentes regulatorios sin socio | **Fuera de DGED** |
| `PEOPLES_CHOICE` | Marketing de afiliados de suplementos para EE.UU. | Nada: el nicho vive de afirmaciones de salud, contra el principio 3 de la visión | **Fuera de DGED** |
| `proyecto-GM-1.1`, `genius-marketing` | Prototipos de AI Studio (Kanban de tareas y otro) | Ya los superó Gestor-Morelos | **Archivar** |
| `Habita-Inmobiliaria`, `melodic-blessing-`, `fibonacci-quantum` | Vacíos (solo README o sin commits) | — | — |
| `DGED-Systems-` | Este repo | — | — |

---

## 2. El zip: `rasdg-field-detector`

Fusiona geomagnetismo, resonancia Schumann, radón y sismicidad en un score
Ξ (0–10), con la arquitectura de Fibonacci Cuántico v4.1. Está en diseño y
simulación, sin hardware.

### Lo que no aguanta revisión (y por qué no entra como producto)

1. **El ruido puro ya llega al umbral.** Su propio `docs/04_decisiones.md`: con
   ruido puro Ξ₀ ronda 6–8, y la alerta es Ξ ≥ 7. Un detector que dispara con
   ruido no ha medido nada todavía.
2. **La validación no tiene tasa base ni placebo.** Precisión = alertas seguidas
   de un evento en 72 h. En el eje neovolcánico hay sismos chicos casi a diario:
   cualquier alerta, puesta al azar, "acierta". Sin comparar contra alertas al
   azar con la misma frecuencia, la precisión no dice nada (la misma trampa que
   el 16/16 de shorts de fq-bot).
3. **Los factores vienen del bot, no de la física.** φ = 1.618 para el CHoCH, el
   umbral 7/10 y la tabla de W_session son constantes de trading; el bot que las
   usa no tiene edge demostrado (motor paper n = 90, E[R] −0.51, IC95% bajo cero).
4. **|Ψ_field|² es una coherencia clásica.** Con c = z + i·ż, la fórmula es la
   longitud resultante de fasores, útil, pero llamarla función de onda no agrega
   nada: el mismo veredicto que el cementerio de fq-bot dio a Baaquie y
   Khrennikov. Además `core/fusion.py` aplica la coherencia dos veces
   (`1 + α|Ψ|²` y luego `0.5 + 0.5|Ψ|²`).
5. **Predecir sismos a corto plazo no tiene método validado**, y los precursores
   electromagnéticos siguen en disputa. Una empresa que vende "aguanta revisión
   externa" no puede ofrecerlo.
6. **La capa experimental** (portales, conciencia, sonido) está bien separada
   por el propio repo y se queda fuera de DGED.

Va al cementerio como idea, con condición para revivir (ver `MEMORY/CEMENTERIO.md`).

### Lo que sí se rescata

| Pieza | A dónde va | Condición |
|---|---|---|
| Índice Kp de NOAA SWPC y el observatorio de Teoloyucan (INTERMAGNET) | Capa de **clima espacial** (§4, P6) | Medir antes de escribir código. Desde esta sesión el proxy dio 403 a SWPC, INTERMAGNET y hasta USGS: **NO CONCLUYE** (invariante XIX), no "muerta" |
| "La coherencia filtra el glitch de un solo sensor" | Ojo satelital: un cambio cuenta solo si **Sentinel-2 y Sentinel-1 coinciden** (A3) | Medir con placebo antes de cambiar el umbral |
| Θ D₁: un sensor aporta más del 70% → falla probable | Regla de calidad para cualquier producto con sensores o varias fuentes | Test que la fije cuando haya producto |
| Red de estaciones propias (magnetómetro, radón) | Fase 3, con un socio académico (por ejemplo, el servicio de clima espacial de la UNAM; **por verificar**) | No entra al presupuesto antes de clientes de fase 1 |

---

## 3. Mejoras para Atlas

En orden de valor. Cada una nombra de dónde sale y qué test la cierra.

| # | Mejora | Se toma de | Invariante que la cierra |
|---|---|---|---|
| A1 | **Instantáneas inmutables** (pendiente de la semana 2): cada calificación se sella en una cadena SHA-256 y el memo cita su hash | `fq-bot/execution.py` (ledger), `marea/src/domain/bitacora.ts` | Recalcular con otra versión del score da otro hash; editar una fila rompe la cadena |
| A2 | **Frescura por factor**: cada fuente con edad máxima; el libro del SMN (corte 2026-09-30) se muestra con su edad y pasado el límite el sitio no es publicable | `marea` `settlement.onRead` (L8), `fq-bot` frescura de CVD | Un dato más viejo que su límite nunca deja publicable el número |
| A3 | **Confirmación S1 + S2** en el ojo satelital: el radar no ve nubes, el óptico no se confunde con la humedad | El zip (coherencia entre fuentes) | Un cambio que solo ve una fuente sale como "no concluye", no como obra |
| A4 | **Vara para el ojo satelital**: las 55 naves de Colliers como positivos y sitios sin obra como placebo; precisión con IC | `fq-bot/tools/validation_gate.py`, `regime-lab` | n < 30 no publica precisión; los umbrales de v0.2 puestos después de ver las obras se re-validan fuera de muestra |
| A5 | **Memo PDF** con verificación de recorte | Diseño de `RASMECHANIC/docs/03` | Ninguna tabla cortada en el PDF (test de render) |
| A6 | **Banco de preguntas del Oráculo** con variantes y red team | `Gestor-Morelos` `services/banco.py` (*pass^k*) | 0 cifras sin herramienta en el banco completo, k corridas |
| A7 | **Seguridad propia** antes de abrir el cuarto de datos a un cliente | Metodología de `web-hunter` | Lista de hallazgos cerrados con test; llave y tope por IP ya existen (XI, XII) |
| A8 | **Alertas por sitio** para Atlas Operate (USD 96k/año, D-006): FIRMS, cambio S1, sismos USGS | Medidos en `MEMORY/FUENTES.md` | La alerta dice la revisita real (S1 3–7 días); nunca "≤ 24 h" |
| A9 | Capa de **clima espacial** mostrada, sin puntuar | El zip | Igual que XIV: una capa nueva no mueve el número sin decisión con nombre |

Aprendizaje que aplica a todo: en Gestor-Morelos el juez de IA midió **kappa
0.011 (n = 49)** contra la casa, es decir, azar. Ningún juicio de un modelo entra
a Atlas sin medir su acuerdo contra una persona.

---

## 4. Productos

Los de `docs/09-portafolio-90-dias.md` siguen igual. Aquí se dice qué repo
alimenta a cada uno, y se proponen dos nuevos.

| Producto | Alimentado por | Siguiente paso |
|---|---|---|
| P1 / **Producto 4** — agente a la medida (D-016) | Gestor-Morelos (núcleo), blue-ocean (modelos de renta corta para la demo de finca y quinta), RASMECHANIC (perfil taller), Mrk.5 (cobro) | Medir la coexistencia de Meta para números de México (`docs/15`) |
| P2 — Atlas Comparativo (D-011) | Este repo + A1, A2, A5 | Demo en Railway y primera corrida en vivo desde ahí |
| P3 — Evaluación técnica | Este repo como muestra; método de seguridad de web-hunter | Dos dictámenes con descuento declarado a cambio de citarlos |
| P4 — Cribado de cartera (NIIF S2) | Atlas + A8 | Medir CENAPRED, CFE sismo y acuíferos antes de ofrecerlo |
| P5 — Auditoría de modelos | fq-bot (gate), regime-lab, fib-features-ml, numerai-crypto | Una página pública con los tres nulos como muestra |
| **P6 (propuesta) — Clima espacial para operaciones** | El zip (capa medible) | Fase 2. Para quien depende de GNSS (agricultura de precisión del Bajío, topografía, drones) y de líneas largas. Medir SWPC e INTERMAGNET desde Railway; entrevistar a 5 usuarios antes de escribir código |
| **P7 (propuesta) — Taller-OS como vertical** | RASMECHANIC + Producto 4 | Es un perfil de P4, no un SaaS aparte: talleres y refaccionarias ya son cliente objetivo de P1 |

---

## 5. Objetivos

Cada objetivo dice cuándo está **terminado**. Los que dependen de un cliente se
dicen como meta, no como promesa.

### Noviembre–diciembre 2026

| # | Objetivo | Terminado cuando |
|---|---|---|
| O1 | Demo de Atlas en Railway | URL pública, `/api/health` con commit, 10 sitios calificados desde Railway, SMN medido 30 intentos desde esa red |
| O2 | Demo sin pena | Mapa base sin clave, ficha legible, fuentes cortas en el Oráculo |
| O3 | A1 + A2 + A5 | Instantánea con hash, frescura por factor y memo PDF, cada uno con su test en la constitución |
| O4 | Producto 4 medido | Coexistencia de Meta medida y escrita en `FUENTES.md`; perfil de la demo sobre los modelos de blue-ocean |
| O5 | Primera propuesta enviada | Un Atlas Comparativo propuesto a Fibra Mty, FIBRA Prologis o Vesta (D-012) |
| O6 | Seguridad propia (A7) | Revisión hecha y hallazgos cerrados antes de subir un documento real de cliente |

### Enero–marzo 2027

| # | Objetivo | Terminado cuando |
|---|---|---|
| O7 | Ojo satelital validado (A3, A4) | n ≥ 30 obras con placebo, precisión con IC95% publicada, S1 + S2 |
| O8 | Producto 4 en sombra | Un cliente con 30 días en sombra y n ≥ 30 conversaciones medidas |
| O9 | Primer cobro | Meta: un Comparativo, una revisión de adquisiciones o un P5 firmado |
| O10 | Claves | INEGI (DENUE), SAKBÉ y Anthropic pedidas y medidas; CENACE, ANR y SSN medidos desde Railway |

### Abril–septiembre 2027

| # | Objetivo | Terminado cuando |
|---|---|---|
| O11 | Atlas Operate con alertas (A8) | Un sitio en monitoreo con alertas que citan escena y fecha |
| O12 | Clima espacial (P6) | Fuentes medidas, capa mostrada sin puntuar, 5 entrevistas; se decide si es producto o va al cementerio |
| O13 | Holgura eléctrica por corredor | Clase firmada contra PRODESEN (D-003) |

### 2028 en adelante

- Fase 2 completa: observación de la Tierra para agua, agricultura e
  infraestructura sobre la misma ontología.
- Fase 3: estaciones y cargas útiles con socio, **solo** con clientes de fase 1
  pagando.

---

## 6. Lo que es del dueño

- Aprobar P6 y P7 como líneas (o mandarlas al cementerio).
- Si `web-hunter` es socio, proveedor o parte de DGED.
- Archivar `proyecto-GM-1.1`, `genius-marketing` y los repos vacíos.
- Si SaluChain y PEOPLES_CHOICE siguen como proyectos personales, fuera de la marca DGED.
- Si el detector de campo sigue como investigación personal; si sí, con hipótesis
  pre-registrada y placebo antes de comprar sensores.
