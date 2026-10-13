# Comparables de precio y modelo de cobro

Fecha de consulta de todas las fuentes: **2026-10-13**, salvo que se diga otra.
Solo información pública. Reglas de lectura, las mismas de `08-mercado.md`:

- Lo que no está publicado se escribe **"no encontrado"** o **"no publicado"**;
  no se rellena con un estimado propio.
- Una cifra que solo aparece en un tercero (blog de proveedor, comparador,
  guía de costos) se marca **"de tercero"**. Sirve para dimensionar, no para
  meterla a un modelo.
- Lo que es razonamiento de DGED y no dato se marca **(inferencia)**.
- n de comparables por producto: 3–6. **n < 30 no concluye**: esto fija un
  precio de arranque que se corrige con propuestas firmadas o rechazadas, no un
  precio "de mercado" demostrado.

Moneda: USD para lo que compra un fondo, FIBRA, aseguradora o banco
(`04-entrega-precios.md`); MXN cuando el comprador es gobierno o PyME mexicana.

---

## 1. Revisión técnica de adquisiciones industriales (D-013) — va primero

### 1.1 Qué se compara

El producto de `11-revision-adquisiciones.md` es un **memo de banderas rojas de
escritorio**: lectura del cuarto de datos con cita a página, rent roll, cruces y
riesgo físico de Atlas. **No** firma un PCA (ASTM E2018), ni una fase I
(ASTM E1527-21), ni una valuación, ni opinión legal. Por eso los comparables
directos son de dos clases y ninguno es idéntico:

1. **Los reportes de terceros que el comprador ya paga** (PCA, fase I,
   valuación): son el techo. Llevan ingeniero, visita al sitio y seguro de
   responsabilidad; nosotros no.
2. **La lectura de contratos (lease abstraction)**, manual o con IA: es el
   piso. Es la parte de nuestro trabajo que más se automatiza.

### 1.2 Comparables

| # | Comparable | Precio público | Modelo de cobro | Comprador típico | Fuente (consulta 2026-10-13) |
|---|---|---|---|---|---|
| A | **Property Condition Assessment (ASTM E2018)**, EE. UU. | **De tercero**: USD 4,000–15,000 por inmueble; < 100,000 ft²: 4,000–8,000; 100,000–500,000 ft²: **8,000–15,000**; campus o portafolio: 15,000–30,000+. Entrega 3–4 semanas después de la visita | Por inmueble, escalado por superficie | Comprador y su banco (el banco lo exige) | [APERS, "Third-party reports", sep 2026](https://apers.app/learn/transaction-lifecycle/due-diligence/third-party-reports-appraisal-pca-esa-zoning) |
| B | **Fase I ambiental (ASTM E1527-21)**, EE. UU. | USD **1,400 a más de 7,500**; el autor recomienda no contratar abajo de USD 3,000. Dato atribuido al *LightBox EDR 2023 Benchmark Survey* (el informe original no es público) | Por sitio | Comprador, banco | [SCS Engineers, 2024-01-15](https://www.scsengineers.com/balancing-costs-and-liabilities-for-consulting-firms-in-phase-i-environmental-site-assessments/) · **De tercero**: USD 3,000–6,000, 2–4 semanas ([APERS](https://apers.app/learn/transaction-lifecycle/due-diligence/third-party-reports-appraisal-pca-esa-zoning)) |
| C | **Paquete de reportes de terceros** por adquisición | **De tercero**: fase I 2,000–5,000; levantamiento ALTA 3,000–8,000; PCA 1,500–10,000; avalúo MAI 4,000–10,000; **12,000–30,000 en total por inmueble** antes de una fase II | Por inmueble y por reporte | Comprador | [Peony, calculadora de due diligence](https://www.peony.ink/tools/due-diligence-cost-calculator) (proveedor de cuartos de datos; indicativo) |
| D | **Lease abstraction manual** (resumen de contrato de renta) | **De tercero**: USD 75–400 por contrato según complejidad y plazo; la revisión interna del comprador agrega 30% o más al costo real | Por contrato | Fondos, administradores, FIBRAs | [Unframe, 2026-08-04](https://www.unframe.ai/blog/evaluating-ai-lease-abstraction-services) |
| E | **Lease abstraction con IA** | **De tercero**: Lextract USD 10 por contrato según SFAI Labs (2026-07-26), USD 15 (12 en paquete de 10) según rets.ai — dos cifras distintas del mismo proveedor, y su página de precios dio 404 el 2026-10-13; Prophia "desde ~USD 20 por documento". Mismo artículo: servicio humano en EE. UU. USD 150–300, *offshore* 50–100, completo con enmiendas 250–400 | Por documento, autoservicio; los grandes (MRI) por contrato anual de USD 10,000–100,000+ | Administradores, corredores, fondos | [SFAI Labs, act. 2026-07-26](https://www.sfailabs.com/guides/how-much-does-automated-lease-abstraction-cost-2026) · [rets.ai, glosario](https://rets.ai/glossary/lease-abstract) |
| F | **México: dictamen estructural** de un inmueble | **De tercero**: MXN 8,000–20,000 por dictamen (otra página del mismo sitio: 10,000–30,000, promedio 20,000). No distingue nave industrial | Por dictamen | Dueño, municipio | [Cronoshare, dictamen estructural](https://www.cronoshare.com.mx/cuanto-cuesta/dictamen-estructural) |

**No encontrado** (y no se inventa):

- Precio público de un **red-flag report** legal o técnico de una adquisición
  industrial en México. Los despachos (legales y de ingeniería) no publican
  honorarios.
- Precio de una **fase I o PCA hecha en México** por firma internacional. El
  único texto público de una firma de EE. UU. sobre fase I en México
  ([Partner ESI, 2016-11-10](https://www.partneresi.com/resources/articles/making-your-own-rules-environmental-due-diligence-in-mexico/))
  describe el método (registros históricos escasos, más peso a la visita) y no
  da costo ni plazo.
- El costo de due diligence **como porcentaje del precio** en adquisiciones de
  FIBRAs: no aparece desglosado en los avisos que se revisaron.
- Precio de lista de **lease abstraction en español** o de contratos mexicanos.

### 1.3 Contra qué se mide el tamaño de la operación

| Operación | Monto | Naves | Monto por nave (inferencia) | Fuente |
|---|---|---|---|---|
| FIBRA Prologis, parque en Monterrey | USD 32.7 M | **3 edificios** + reserva de 40,800 m², rentados al 100% en USD | ≈ USD 10.9 M | [The Logistics World, fechada 2026-08-04](https://thelogisticsworld.com/actualidad-logistica/fibra-prologis-adquiere-parque-industrial-en-monterrey) · [Bloomberg Línea](https://www.bloomberglinea.com/latinoamerica/mexico/fibra-prologis-acelera-ritmo-de-compras-de-parques-industriales-en-la-carrera-por-el-nearshoring/) |
| FIBRA Prologis, Monterrey/Toluca/Juárez | USD 67.1 M (dic 2025) | no encontrado en la nota | — | citado en `08-mercado.md` §2.2 |
| Fibra Mty → Fibra Macquarie | toma de control > 80% | 343 naves | — | citado en `08-mercado.md` §2.2 |

**Ojo con la fecha del parque de USD 32.7 M**: la nota de The Logistics World
lleva fecha 2026-08-04, pero la de Bloomberg Línea que cuenta la misma compra
habla de las adquisiciones de los primeros nueve meses de **2023**. Antes de
citarlo como compra de 2026 en una propuesta, confirmarlo en el aviso de la BMV.
`08-mercado.md` y `09-portafolio-90-dias.md` lo dan como "ago 2026": queda
señalado aquí, no se reescribe allá.

### 1.4 Lectura de los comparables (inferencia)

- Una nave industrial típica de Monterrey (10,000–30,000 m² ≈ 108,000–323,000
  ft²) cae en el tramo de PCA de **USD 8,000–15,000** (A). Sumando fase I
  (B, 3,000–6,000), el comprador ya gasta **USD 11,000–21,000 por nave** en
  reportes firmados, sin contar avalúo ni legal (C: 12,000–30,000 por inmueble).
- La lectura pura de contratos con IA vale **USD 10–20 por contrato** (E); con
  humano, 75–400 (D). Una nave suele tener uno a tres contratos: la lectura
  sola no sostiene un precio de miles.
- Lo que sí sostiene miles es lo que ni A ni E entregan: **cruces entre
  documentos con cita a página** (escritura vs contrato vs catastro, vencimientos
  contra horizonte, oficio CFE contra uso) + **riesgo físico con fuente
  oficial mexicana** + **72 horas antes de la exclusividad**, cuando todavía se
  puede negociar o retirarse. Ese es el valor, y es el mismo trabajo de analista
  que ya se cobra en Atlas: Screening ≈ USD 4,600 por sitio (D-006), Comparativo
  ≈ USD 5,000 por sitio (D-011).
- Por lo tanto el precio por nave va **arriba de la fase I más barata y abajo
  del PCA**: llegamos antes que esas firmas, no en su lugar.

### 1.5 Propuesta para D-013 (a decidir por el dueño; no es decisión todavía)

| Concepto | Propuesta | Lógica |
|---|---|---|
| **Precio por nave** | **USD 3,500** | Abajo del Screening por sitio (USD 4,600) porque reusa Atlas y el lector; arriba del piso de fase I (USD 1,400–3,000) y de la lectura con IA (USD 10–20 por contrato); **un cuarto a la mitad** del PCA de una nave de 100,000–500,000 ft² (USD 8,000–15,000). Sobre una nave de ≈ USD 10.9 M es ≈ **0.03%** del precio (inferencia) |
| **Mínimo por memo** | **3 naves = USD 10,500** | Debajo del Comparativo (USD 15,000), para que un gerente de adquisiciones lo apruebe sin comité; coincide con el tamaño del parque de 3 edificios de FIBRA Prologis |
| **Tope por portafolio** | **USD 45,000 por memo, hasta 60 naves** | 45,000 / 3,500 ≈ 13: de la nave 14 a la 60 no se cobra más. El portafolio pesa por consolidación (343 naves de Fibra Macquarie), y el costo marginal del lector baja por nave; el del analista no baja a cero, de ahí el límite de 60. Queda **debajo** del Atlas Screening (USD 55,000) para no canibalizarlo |
| **Arriba de 60 naves** | Un segundo tramo con el mismo tope (USD 45,000 por cada 60 naves o fracción), o Atlas Portfolio (USD 210,000/año, D-006) si además quiere monitoreo | Un memo de 343 naves no se entrega en 72 h; partirlo en tramos de 60 conserva el plazo |
| **Plazo** | 72 h hábiles hasta 10 naves; 10 días hábiles hasta 60 | La promesa de venta de `11-revision-adquisiciones.md` |
| **Contratos por nave incluidos** | Hasta 3 contratos de renta; cada contrato extra USD 150 | Precio de lectura manual de tercero (D: 75–400) sin bajar al de autoservicio con IA: incluye cruce y cita |
| **Cobro** | 50% al recibir acceso al cuarto de datos, 50% contra memo | La misma regla de `04-entrega-precios.md`: sin el primer pago no se enciende |
| **Crédito** | 100% acreditable contra un Atlas Screening o Portfolio firmado en 90 días | Misma lógica que D-011: esta es puerta, el Screening sigue siendo destino |

**Cuándo subir** (inferencia, cada caso con su n):

- Si **tres propuestas seguidas firman sin regateo**, subir el precio por nave
  20% (USD 4,200) y el tope en proporción.
- Cuarto de datos con **más de 150 documentos por nave** o en papel escaneado
  sin OCR: +USD 1,000 por nave (el costo es del analista, no del modelo).
- Naves **fuera de los corredores medidos** (hoy solo `nl-monterrey` y puntos
  del Bajío marcados, D-002): +25% por cada corredor nuevo, o no se vende hasta
  medir las fuentes (`CLAUDE.md`: una fuente se mide antes de su código).
- **Urgencia de menos de 72 h**: +25%.

**Cuándo bajar** (inferencia):

- Si **tres propuestas seguidas no firman por precio** (no por alcance ni por
  tiempo), bajar a USD 2,800 por nave antes de recortar alcance; nunca quitar la
  sección de "lo no revisado".
- **Segundo memo del mismo cliente** en 12 meses: −15%, porque el lector y las
  plantillas del cliente ya existen.
- **Socio de ingeniería** que revende el memo dentro de su PCA: precio mayorista
  USD 2,500 por nave, con nuestro nombre en el memo.

**Los tres comparables más fuertes** para defender el número ante el cliente:
(A) PCA USD 8,000–15,000 por nave de 100–500 mil ft² — APERS; (B) fase I
USD 1,400–7,500+, con piso recomendado de USD 3,000 — SCS Engineers citando a
LightBox; (E) lectura de contrato con IA USD 10–20 — SFAI Labs / rets.ai. El
primero pone el techo, el segundo dice dónde empieza un reporte técnico serio,
el tercero dice cuánto vale la lectura sin cruce ni criterio.

---

## 2. Monitoreo satelital de avance de obra

Para bancos (crédito puente o de construcción), desarrolladores con varias obras
y gobierno (obra pública).

### 2.1 Comparables

| # | Comparable | Precio público | Modelo de cobro | Comprador típico | Fuente (consulta 2026-10-13) |
|---|---|---|---|---|---|
| A | **Inspección de avance para liberar un pago** (*draw inspection*), EE. UU. | **De tercero**: USD 100–300 por visita (alto: 400+). Citizens Bank, según el extracto del buscador: USD 155 por inspección de avance en créditos solicitados antes del 2026-01-22 y ninguno después; inspección final USD 200–1,000. El PDF del banco devolvió 403 y no se pudo leer completo | Por visita, una por cada disposición | Banco; lo paga el acreditado | [Citizens Bank, tarifas de servicio](https://www.citizensbank.com/dam/6a53971d-329f-486d-911e-b42100cd8a1a/common-servicing-fees-original-file.pdf) · [Lenderly](https://lenderly.co/navigating-construction-loan-draws/) |
| B | **DroneDeploy** (captura con dron y análisis de avance) | **Público**: Flight & Analysis USD 4,188/año (≈ 349/mes) por piloto; planes Enterprise, Aerial y Ground "cotización" | Suscripción anual por licencia; el vuelo lo pone el cliente | Constructoras, desarrolladores | [DroneDeploy, precios](https://dronedeploy.com/pricing) |
| C | **Imagen satelital de 50 cm** bajo pedido (SkySat vía SkyWatch) | **De tercero**: archivo USD 10–12/km², mínimo 25 km² (catálogo SkyWatch, jun 2026); tareo nuevo desde USD 12/km² con mínimo ≈ 25 km² en un listado agregador que pide re-verificar | Por km² por imagen | Cualquier analista | [SkyWatch, área y costo mínimo](https://intercom.help/skywatch-ab92e82e1a0a/en/articles/9917241-aoi-size-and-cost-requirements-hub) · [apis.io, planes SkyWatch](https://apis.io/plans/skywatch/skywatch-plans-pricing/) |
| D | **SpaceKnow Guardian** (avance satelital contra el calendario de obra) · **Vantor** (señales de construcción) · **BlackSky** (contrato con gobierno de EE. UU. para monitoreo de construcción) | **No publicado** en ninguno de los tres | Contrato a la medida | Gobierno, bancos, infraestructura | [SpaceKnow](https://spaceknow.com/blog/spaceknow-guardian-for-construction-monitoring/) · [Vantor](https://go.vantor.com/monitoring-construction-signals) · [FedScoop](https://fedscoop.com/?p=32026) |
| E | **ESA ConsTrack / Buildspot** (proyectos piloto con bancos y vigilancia semanal de miles de obras) | **No publicado**: la ESA describe usuarios (bancos) y alcance, no precio | Piloto financiado | Bancos europeos | [ESA ConsTrack](https://business.esa.int/projects/constrack) · [ESA Buildspot](https://business.esa.int/projects/buildspot) |
| F | **Supervisión de obra pública en México** | **No encontrado** como porcentaje público. Un trámite estatal de Coahuila (ICIFED, supervisión de obra educativa) aparece en el buscador con un cobro de **3% del monto de la obra**; la página dio 503 el 2026-10-13 y no se verificó. La ASF exige licitar la supervisión aparte de la constructora | Porcentaje de obra o precio unitario por tiempo | Dependencias, estados | [Papelea, ICIFED (no verificado)](https://papelea.com/mx/estado-de-coahuila-de-zaragoza/supervision-de-obra-icifed-registro-estatal-de-tramites-y-servicios-retys) · [ASF, auditoría 2012-0144](https://www.asf.gob.mx/Trans/Informes/IR2012i/Documentos/Auditorias/2012_0144_a.pdf) |

**Rango observable**: USD 100–300 por visita humana (A) y USD ≈ 350/mes por
licencia de dron (B). Del satelital puro no hay precio de lista público (D, E).

### 2.2 Propuesta para DGED (inferencia)

| | |
|---|---|
| **Precio** | **MXN 6,000 por obra al mes** (≈ USD 330), mínimo **10 obras × 6 meses** (MXN 360,000). Imagen de 50 cm, cuando el cliente la pida, se factura a costo + 15% (≈ USD 300 por toma con el mínimo de 25 km²) |
| **Modelo** | Por activo-mes, con un mínimo de cartera |
| **Comprador típico** | Área de crédito puente de un banco o de la banca de desarrollo (SHF, Bancomext); desarrollador con 5+ obras; gobierno estatal con obra pública |
| **Lógica** | Una visita humana mensual cuesta USD 100–300 en EE. UU. (A) y en México además implica traslado; el satélite **no reemplaza** la visita que libera el pago, la **programa**: dice qué obra se movió y cuál no antes de mandar a nadie. Por eso el precio va en el rango de una visita, no arriba. El mínimo de cartera existe porque el costo es la puesta en marcha (polígonos, calendario de obra), no la imagen |
| **Qué se mide antes de vender** | Que Sentinel-2 (10 m, gratis) distinga etapas de una nave (terracería → estructura → techo) en las obras de un cliente. Si con 10 m solo se ve "hay techo / no hay techo", el producto es de 50 cm y el precio cambia. **No medido todavía**: por la regla de la casa, no se vende hasta medirlo |
| **No se promete** | Porcentaje de avance físico firmado: eso es del supervisor con cédula |

## 3. Inteligencia de mercado por detección satelital de construcciones nuevas

Suscripción: "qué naves nuevas aparecieron este mes en el corredor", antes de
que salgan en el reporte trimestral de un corredor o en el DENUE.

### 3.1 Comparables

| # | Comparable | Precio público | Modelo de cobro | Comprador típico | Fuente (consulta 2026-10-13) |
|---|---|---|---|---|---|
| A | **ConstructConnect** (proyectos de construcción como prospectos, EE. UU.) | **De tercero**: Starter USD 129/mes por mercado y asiento (mes a mes); Professional desde USD 199/mes por mercado y asiento (anual); Premium desde **USD 10,000/año**. Cifras verificadas por un competidor contra la página del proveedor el 2026-10-06 | Suscripción por mercado × asiento | Contratistas, proveedores de materiales | [ConstructionBids.ai, guía 2026](https://constructionbids.ai/blog/constructconnect-pricing-guide-2026) · [PricingSaaS](https://pricingsaas.com/companies/constructconnect) |
| B | **Building Radar** (detección de proyectos con IA, incluye señales satelitales en su relato comercial) | **No publicado** (cotización a la medida, contrato anual). **De tercero**: USD 500–2,000+/mes según asientos y regiones (estimado de un competidor) | Suscripción anual por regiones y asientos | Proveedores de construcción, fabricantes | [Datarade](https://datarade.ai/data-providers/building-radar/profile) · [Prospeo](https://prospeo.io/s/building-radar-pricing-reviews-pros-and-cons) |
| C | **Planet Analytic Feeds** (detección de edificios y cambios) | **No publicado**: requiere suscripción por área (AOI) y ventana de tiempo, vía ventas. Cadencia mensual en una hoja técnica, semanal en el anuncio de Planet Insights: se contradicen | Suscripción por área y periodo | Gobierno, aseguradoras, analistas | [Planet, Analytic Feeds Viewer](https://docs.planet.com/platform/get-started/analyze-data/analytic-feeds-viewer/) · [Planet, análisis](https://docs.planet.com/develop/apis/analytics/) |
| D | **LandTech** (Reino Unido; filtro de terrenos y alertas) | **Público**: Pro GBP 150/mes + IVA | Suscripción por usuario | Desarrolladores | citado en `08-mercado.md` §1.3 |
| E | **Statista** (dato de mercado genérico, referencia de disposición a pagar por "inteligencia") | Aparece en el buscador: Starter USD 199/mes, Professional USD 1,399/mes. No es comparable de producto, solo de bolsillo | Suscripción por usuario | Analistas | [Statista](https://www.statista.com/statistics/1370409/mexico-construction-production-value-by-state) |

**No encontrado**: precio de **BIMSA Reports** (proyectos de construcción en
México) ni de **SiiLA** (datos inmobiliarios comerciales de México). Los dos
son los competidores locales naturales y ninguno publica tarifa. Tampoco hay
precio público de Colliers/CBRE research: lo regalan como mercadotecnia.

**Rango observable**: USD 1,500–2,400/año por mercado y asiento (A, básico) a
USD 10,000/año (A, Premium); B, de tercero, USD 6,000–24,000/año.

### 3.2 Propuesta para DGED (inferencia)

| | |
|---|---|
| **Precio** | **USD 1,200 al mes por corredor** (USD 14,400/año, anual), 3 asientos, alerta mensual de naves nuevas y en obra con polígono, fecha de primera detección y municipio. Asiento extra USD 100/mes |
| **Modelo** | Suscripción por corredor (área), no por asiento: el valor está en el área cubierta, como en Planet (C) |
| **Comprador típico** | Proveedores que venden a naves nuevas (techos, estructuras, subestaciones, seguridad, montacargas), corredores inmobiliarios, desarrolladores que vigilan la competencia, gobierno estatal (promoción) |
| **Lógica** | Arriba del Premium de ConstructConnect (USD 10,000/año) porque México no tiene base de permisos abierta equivalente y la alternativa es mandar gente a recorrer el corredor; **abajo** del corredor extra de Atlas Operate (USD 48,000/año, D-006), que trae re-score y talleres. Si un cliente de Operate la quiere, va incluida |
| **Qué se mide antes de vender** | Precisión y oportunidad contra una lista pública: Colliers reporta **55 naves en construcción en Monterrey** (2T 2026, `08-mercado.md` §2.1). Si el detector sobre Sentinel-2 encuentra ≥ 80% de ellas y las ve antes que el reporte, se vende; con n = 55 alcanza para concluir (n ≥ 30). Si no, va al cementerio con su número |
