# Mercado: desmontaje competitivo y demanda

Fecha de consulta de todas las fuentes: **2026-10-12**, salvo que se diga otra.
Solo información pública: sitios, documentación, precios publicados, notas de
prensa. Donde un precio no es público se escribe **"no publicado"**, no un
estimado propio. Las cifras que solo aparecen en un tercero (blog, comparador,
asesor de negociación) se marcan como **"de tercero"**.

> Regla de lectura: una cifra de prensa no es una cifra medida. Aquí se usan
> para dimensionar la conversación, no para meterlas a un modelo.

---

## 1. Desmontaje por segmento

### 1.1 Plataformas de ontología y decisión — Palantir Foundry / AIP

| | |
|---|---|
| Qué vende | Plataforma de datos con ontología (objetos, vínculos, acciones) y capa de IA (AIP) encima; despliegue con ingenieros en sitio |
| A quién | Gobierno y gran empresa. En México, el primer cliente comercial anunciado es **GNP Seguros** (julio 2026): fraude en siniestros, monitoreo de riesgo y suscripción |
| Precio | **No publicado.** De tercero: compromisos comerciales "de ~USD 250k/año en despliegues angostos" y "USD 0.5–2 M/año" en primeros contratos de empresa mediana-grande; ingeniero de campo ~USD 300k/año. Son cifras de asesores de negociación, no de Palantir |
| Datos | Los del cliente. Palantir no vende datos, vende la capa que los une |
| Lo que podemos replicar con datos públicos | **La idea, no el producto**: un contrato de objetos (`Site`, `Municipio`, `SubestacionAprox`…) que se materializa en cada decisión, con su evidencia y su versión. Ya existe en `ontology/atlas.ontology.json` (D-004, D-007). Lo vendible es la **disciplina de ontología aplicada a un problema chico** (un corredor, una cartera de predios, un flujo de cotización), no "un Palantir mexicano" (cementerio: "Plataforma tipo Palantir") |

Fuentes:
[Expansión, 2026-07-08](https://expansion.mx/tecnologia/2026/07/08/palantir-llega-a-mexico-con-gnp-seguros) ·
[Business Wire, comunicado GNP](https://www.businesswire.com/news/home/20260707514163/en/Palantir-Expands-Its-Presence-in-Mexico-and-Strengthens-Its-AI-Offering-in-the-Insurance-Sector-with-GNP-Seguros/) ·
[B.D. Emerson, costo de Palantir (de tercero)](https://www.bdemerson.com/article/palantir-cost) ·
[Redress Compliance (de tercero)](https://redresscompliance.com/palantir-aip-foundry-negotiation.html) ·
[CostBench (de tercero)](https://costbench.com/software/ai-ml-platforms/palantir-aip/)

**Lectura para DGED:** que la aseguradora más grande de México compre ontología
+ IA en 2026 valida el lenguaje ("objetos, evidencia, decisiones") ante un
comité mexicano. No valida que nos compren *a nosotros* la plataforma: el
tamaño de ticket de Palantir está dos órdenes arriba de lo que DGED puede
entregar con una persona.

### 1.2 Riesgo climático físico por activo

| Empresa | Qué vende | A quién | Precio público | Datos |
|---|---|---|---|---|
| **Jupiter Intelligence** (ClimateScore Global, FloodScore, HeatScore…) | Métricas de peligro y pérdida a futuro por coordenada, API y reportes | Aseguradoras (Zurich, Liberty Mutual, QBE, MS&AD), utilities, ciudades | **No publicado.** Declaración del CEO citada en prensa: de USD 25k a contratos multimillonarios; un perfil de 2022 dice "USD 1 M/año en adelante". Contradictorias | Modelos climáticos globales + modelos propios |
| **XDI** (Climate Risk Hub) | Pérdida anual esperada por activo ("Technical Insurance Premium"), escenarios IPCC/NGFS, reportes estandarizados | Bancos, gobiernos, corporativos; descuento o pro bono a reguladores/ONG | **No publicado** (solo "contáctenos") | Modelos de ingeniería de daño por tipo de activo |
| **Moody's** (Climate on Demand, base RMS) | Puntaje de riesgo físico y, en Pro, daño + interrupción de negocio en dinero por activo | Inversionistas, crédito, aseguradoras | **No publicado** | Modelos catastróficos RMS + escenarios |
| **Climate X** (Spectra) | Ratings de peligro por activo | Bancos hipotecarios, inmobiliario comercial | **Público en AWS Marketplace**: Spectra Lite USD 20,000 base (1 escenario, 3 peligros, solo ratings); excedente USD 62 por activo comercial (251–500) y USD 57 (>500) | Modelos propios |
| **First Street** | Riesgo por propiedad (EE. UU.) | Inmobiliario, hipotecas | API: **no publicado** | Modelos propios; solo EE. UU. |

Fuentes:
[Trellis sobre Jupiter (precio citado al CEO)](https://trellis.net/article/climate-risk-analytics-software-scene-expanding/) ·
[S&P perfil Jupiter](https://sp-edge.com/companies/626274) ·
[Coverager, ClimateScore Global](https://coverager.com/jupiter-announces-launch-of-climatescore-global/) ·
[xdi.systems](https://xdi.systems/) ·
[Moody's Climate on Demand](https://climate.moodys.com/climate-on-demand) ·
[AWS Marketplace, Climate X Spectra Lite](https://aws.amazon.com/marketplace/pp/prodview-52oe5cileyk7a) ·
[BatchData, guía de APIs (de tercero)](https://batchdata.io/blog/climate-risk-real-estate-apis-buyer-guide)

**El único precio de lista verificable del segmento es el de Climate X: USD 20k
de entrada y ~USD 60 por activo comercial.** Esa es la vara de comparación
honesta para un cribado de riesgo físico de cartera.

**Qué podemos replicar con datos públicos de México (función, no código):**

- Peligro **actual** por activo con fuentes oficiales: inundación y laderas
  (Atlas Nacional de Riesgos, CENAPRED), sismo (regionalización CFE), sequía
  municipal (SMN/CONAGUA), disponibilidad de acuífero (DOF/CONAGUA). La mitad ya
  está en `services/api/atlas/connectors/` y en `docs/02-fuentes.md`.
- Bandas tipo "bajo / medio / alto" por peligro, con la fuente y el corte.
- **Lo que no podemos replicar:** pérdida esperada en pesos y escenarios a 2050
  sin un modelo de daño ni proyecciones climáticas regionalizadas. **No
  medido**: si existe una fuente pública mexicana de proyecciones descargable
  por servidor. Hasta medirla, el producto dice "peligro actual", no "riesgo
  climático futuro".

### 1.3 Inteligencia inmobiliaria industrial y selección de sitio

#### México

| Actor | Qué vende | A quién | Precio público | Datos |
|---|---|---|---|---|
| **Solili** | Marketplace + reportes de mercado por corredor; inventario, vacancia, rentas; "libros de opciones" | Corredores, inquilinos, desarrolladores | **Sí**: membresía Industrial **MXN 1,449/mes** (93+ reportes por corredor, filtros, libros de opciones); Oficina MXN 949/mes. Corporativo: no publicado | Levantamiento propio de inventario; 15 mercados industriales |
| **Datoz** (Monterrey) | Datos de mercado industrial/oficinas; "Datoz AI", consultor con IA sobre 10+ años y 24 mercados (lanzado marzo 2026) | Corredores, desarrolladores, bancos | **No publicado** (demo) | Base propia |
| **SiiLA** | Transacciones de arrendamiento y venta, estadísticas | Inmobiliario comercial | No publicado | Base propia |
| **Colliers / CBRE / JLL / Newmark** | Reportes trimestrales gratuitos (gancho), corretaje, representación de inquilino, *site selection* | Inquilinos corporativos, desarrolladores, fondos | Reportes gratis; corretaje por comisión (no publicado) | Levantamiento propio |
| **AMPIP** (con socios de investigación) | Directorio de parques, "Atlas AMPIP", estudios sectoriales, promoción | Sus ~150 socios, gobierno, inversionistas | Membresía no publicada | Lo que reportan sus socios |
| **Shelters y asesores de nearshoring** (Tetakawi, OBG, despachos como Holland & Knight) | *Site selection*, estimación de costos, operación bajo shelter, permisos | Manufacturero extranjero que entra a México | **No publicado** | Propios + experiencia |

Cifras del mercado que publican ellos mismos (ver §2): Solili Q3 2026,
inventario nacional 115.1 M m², vacancia 5.5%; Colliers Monterrey 2T 2026,
absorción neta 690,857 m², disponibilidad 7.3%; CBRE Monterrey 2T 2026,
inventario 17.99 M m², vacancia 6.8%, renta promedio USD 6.98/m²/mes.

Fuentes:
[Solili, membresía](https://www.solili.mx/membresia/) ·
[Solili, reporte industrial 3T 2026 (2026-10-05)](https://www.solili.mx/noticias/reporte-industrial-solili-tercer-trimestre-2026/8177/) ·
[El Financiero, Datoz AI (2026-03-19)](https://www.elfinanciero.com.mx/opinion/de-jefes/2026/03/19/datoz-lanza-consultor-inteligente/) ·
[The Manufacturer, SiiLA](https://www.themanufacturer.com/articles/siila/) ·
[Vanguardia/Reforma, Colliers Monterrey 2T 2026 (2026-07-08)](https://vanguardia.com.mx/noticias/mexico/sube-167-absorcion-de-naves-industriales-en-monterrey-pese-a-incertidumbre-por-t-mec-DA22004997) ·
[Cluster Industrial, CBRE Monterrey](https://clusterindustrial.com.mx/monterrey-suma-casi-18-millones-de-m2-industriales-y-mantiene-crecimiento-sostenido-cbre/) ·
[Tetakawi, servicios](https://go.tetakawi.com/shelter-services) ·
[OBG Nearshoring](https://oxfordbusinessgroup.com/nearshoring) ·
[Holland & Knight, nearshoring](https://www.hklaw.com/en/services/practices/international-business-and-trade/nearshoring)

**Lectura para DGED (confirma `docs/05-riesgos.md`):** el inventario y la
renta ya están vendidos, y baratos (MXN 1,449/mes). Competir ahí es perder. El
hueco es **el predio contra sus restricciones físicas** (agua, sequía,
inundación, red eléctrica regional, ruta), con la fuente y el corte de cada
dato, en un memo que alguien firma. Ninguno de los actores de arriba publica
eso como producto.

#### Global — LandTech (Reino Unido)

| | |
|---|---|
| Qué vende | LandInsight: búsqueda de terrenos con propietario, restricciones de planeación, datos ambientales e infraestructura; *Site Sourcing Tool*, alertas |
| A quién | Desarrolladores y promotores de suelo en Reino Unido |
| Precio | **Público**: Pro **GBP 150/mes** + IVA (500 consultas de propietario/mes, restricciones de política, ambientales parciales). Unlimited y Enterprise/API: no publicado |
| Datos | Registros públicos del Reino Unido (propiedad, planeación) + capas ambientales |
| Lo replicable | El flujo **"filtra el universo por restricciones → lista corta → alerta cuando algo cambia"**. En Atlas es el precio alterno de USD 70k ("búsquenme dónde") y la alerta de Operate. México no tiene registro de propiedad abierto equivalente: el predio lo trae el cliente o el parque |

Fuentes: [land.tech/pricing](https://land.tech/pricing) ·
[land.tech, planes LandInsight](https://land.tech/landinsight-pricing-plans)

### 1.4 Observación de la Tierra

| Actor | Qué vende | Precio público | Nota México |
|---|---|---|---|
| **Planet** | PlanetScope diario (3 m), SkySat (alta resolución), plataforma Insights | Página de precios con suscripción de entrada ~USD 2,700/año por ubicaciones, marcada "próximamente"; de tercero (SkyWatch, jun 2026): SkySat ~USD 10–12/km², mínimo 25 km². Un documento G-Cloud 2024 de un revendedor: paquete PlanetScope global GBP 150,000/12 meses | No se encontró contrato público con el gobierno mexicano |
| **Satellogic** | Constelación como servicio, imágenes submétricas | No publicado | Carta de intención con la Agencia Espacial Mexicana (dic 2022); no se encontró ejecución |
| **Copernicus Sentinel-1/2, Landsat** | Imágenes abiertas (10–30 m) | Gratis | Base de cualquier producto DGED de Fase 2 |
| **Gobierno de México (Ixtli)** | Constelación propia de 4 satélites, MXN 540 M, órbita hacia 2028; contratación prevista a fines de 2026 | — | Secihti: en 2024, 19 entidades gastaron MXN 172 M en imágenes; más de 50 entidades las usan |

Fuentes:
[planet.com/pricing](https://www.planet.com/pricing/) (la página no se pudo leer completa desde servidor; cifras vía búsqueda) ·
[SkyWatch, Planet (de tercero)](https://skywatch.com/geospatial-data-providers/planet/) ·
[G-Cloud 14, lista de precios de revendedor](https://assets.applytosupply.digitalmarketplace.service.gov.uk/g-cloud-14/documents/93283/624361565153865-pricing-document-2024-05-06-2002.pdf) ·
[Via Satellite, Satellogic–AEM (2022-12-13)](https://www.satellitetoday.com/government-military/2022/12/13/mexico-explores-dedicated-earth-observation-program-with-satellogic/) ·
[Expansión, satélites mexicanos (2026-03-03)](https://expansion.mx/empresas/2026/03/03/mexico-lanza-cuatro-satelites-seguridad-clima)

**Lectura para DGED:** el dato satelital es commodity (Sentinel es gratis) y el
cuello del comprador público mexicano no es la imagen, es **convertirla en un
indicador que una dependencia pueda usar** (MXN 172 M en imágenes en 2024, sin
dato público de cuánto de eso se volvió decisión). Coincide con `VISION.md`:
EO es Fase 2 y entra por la misma ontología. **Satélite como factor del score
sigue fuera** (`docs/01-mvp.md`).

### 1.5 Agentes de atención y cotización por WhatsApp (PyMEs)

| Actor | Qué vende | Precio público |
|---|---|---|
| **Leadsales** (MX) | CRM conversacional multicanal con automatización | De su blog (2026): MXN 2,362.92 / 3,239.88 / 6,016.92 al mes (3–5 usuarios); otra página suya dice USD 97/mes. Inconsistente |
| **Wati** | Bandeja y chatbot sobre la API oficial | De tercero: USD 49 / 99 / 249 al mes; su soporte confirma cobro prepagado por conversación |
| **Treble** | Automatización de WhatsApp para empresa | No publicado |
| **DuoTach** | Agente con IA | Publica USD 1,800 de implementación + desde USD 200/mes |
| **Meta (costo de fondo)** | WhatsApp Business Platform | Desde 2025-07-01 cobra **por plantilla entregada**; mensajes de servicio dentro de la ventana de 24 h, gratis; utilidad dentro de la ventana, gratis; México con tarifa de marketing rebajada desde 2025-10-01. Las tarifas en MXN están en el archivo de la tarjeta de precios, no en el texto de la página |

Fuentes:
[Leadsales vs Treble](https://leadsales.io/blog/treble-vs-leadsales-1/) ·
[Leadsales vs Wati](https://leadsales.io/blog/leadsales-vs-wati/) ·
[Wati, soporte de precios](https://support.wati.io/es/articles/11462997-comprension-de-los-planes-de-precios-de-wati) ·
[DuoTach](https://duotach.com/blog/mejores-chatbots-whatsapp-mexico) ·
[Leadsales, costo de un agente IA](https://leadsales.io/blog/cuanto-cuesta-implementar-agente-ia-en-whatsapp/) ·
[Meta, precios de WhatsApp Business Platform](https://developers.facebook.com/docs/whatsapp/pricing)

**Lectura para DGED:** el mercado de "chatbot" es barato y saturado
(USD 50–250/mes). Lo que nadie de la tabla publica es lo que Gestor Morelos ya
hace en producción y tiene escrito con tests: **el bot no inventa una cifra**
(la pone el cotizador), **escala en lugar de contestar mal**, la voz se cita del
negocio y **el tiempo hasta la cotización se mide** (`/internal/tiempos`). Eso se
vende como proyecto a la medida para PyMEs con cotización compleja
(trámites, refacciones, servicios técnicos), no como SaaS de USD 49.

**Riesgo duro:** Gestor Morelos usa un worker de WhatsApp **no oficial**. Para un
cliente se usa la API oficial de Meta (Cloud API), con su costo por plantilla y
su aprobación de plantillas. Vender sobre el canal no oficial expone al cliente
a que le bloqueen el número.

### 1.6 Evaluación técnica independiente y validación de modelos

No se encontró ningún precio público de "ingeniero independiente" ni de
*technical due diligence* para proyectos de tecnología en México; las búsquedas
devuelven tarifas de ingeniería estructural para vivienda, que no son
comparables. Referencia de tarifa por hora: una lista de precios GSA de un
proveedor (2021) trae "Senior Data Scientist" a USD 235.77/h; es **un dato de un
proveedor y de 2021**, no un benchmark. La herramienta pública CALC+ de GSA
permite consultar techos vigentes; **no se consultó en vivo** desde este
servidor.

Fuentes:
[GSA, guía CALC+](https://buy.gsa.gov/pricing/assets/documents/user-guides/CALC%2B%20User%20Guide%20for%20Labor%20Ceiling%20Rates.pdf) ·
[Lista GSA de un proveedor (2021)](https://www.gsaadvantage.gov/ref_text/GS10F0354T/0WD65Y.3S3J4P_GS-10F-0354T_GS10F0354TJUNE222021GS10F0354TSAPERETEXTFILE.DOC)

**Lo vendible:** la "vara" de fq-bot (holdout fuera de tiempo, placebo, DSR,
PBO, cobertura) y la disciplina de Gestor Morelos ("aprobada no es entregada",
"n < 30 no concluye") como **dictamen independiente** de un proyecto o de un
modelo antes de que alguien firme el cheque. El comparable de precio es tiempo
de consultor senior, no software.

---

## 2. Demanda: quién compra en México

### 2.1 Las cifras de fondo

| Dato | Cifra | Fuente |
|---|---|---|
| IED 2025 (preliminar) | **USD 40,871 M**, +10.8%, récord; 67.7% reinversión de utilidades, **18% nuevas inversiones** | [Secretaría de Economía vía Proyectos México](https://www.proyectosmexico.gob.mx/?p=159372) · [Bloomberg Línea](https://www.bloomberglinea.com/latinoamerica/mexico/inversion-extranjera-en-mexico-anota-record-en-2025-aun-con-desaceleracion-de-flujos-de-eeuu/) |
| IED 1T 2026 | USD 23,591 M (récord trimestral) | [American Industrial Magazine, 2026-07-03](https://www.americanindustrialmagazine.com/blogs/industria/nearshoring-en-mexico-2026-cifras-de-ied-parques-industriales-y-estados) · [México ¿cómo vamos?](https://mexicocomovamos.mx/wp-content/uploads/2026/06/20260525_PublicacionMCV_IED_1T2026.docx.pdf) |
| Anuncios de inversión ligados a nearshoring | USD 106,161 M en 421 anuncios, ene-2023 a jun-2025 (Integralia) | [Vanguardia, Integralia](https://vanguardia.com.mx/dinero/dinero-local/nearshoring-coahuila-se-mantiene-en-top-5-de-inversiones-afirma-integralia-CJ16684897) |
| Anunciado vs construido | ~14.7% de lo anunciado llega a construcción (análisis sin autor nombrado, datos a 3T 2025) | [American Industrial Magazine](https://www.americanindustrialmagazine.com/blogs/industria/nearshoring-en-mexico-2026-cifras-de-ied-parques-industriales-y-estados) — **no verificado en la fuente primaria** |
| Parques industriales | 477 en operación en 28 estados, 103 en construcción (AMPIP 2026, citado por tercero); otra nota de AMPIP: 491 y 82. Las cifras no coinciden entre notas | [American Industrial Magazine](https://www.americanindustrialmagazine.com/blogs/industria/nearshoring-en-mexico-2026-cifras-de-ied-parques-industriales-y-estados) · [Cluster Industrial](https://clusterindustrial.com.mx/ampip-fortalece-la-atraccion-de-inversion-con-inteligencia-sobre-cadenas-productivas/) |
| Inversión anual de socios AMPIP | > USD 5,000 M/año; ~150 socios, ~95% de los parques privados | [México Industry](https://mexicoindustry.com/noticia/ampip-refuerza-el-liderazgo-industrial-con-nuevo-consejo-2026-2027) |
| Plan México, primeros parques | 20 parques, 15 desarrolladores, > USD 711 M, 3.5 M m², ~245 empresas, 10 estados (incluye NL); meta de 100 (2026-03-09) | [Cluster Industrial](https://clusterindustrial.com.mx/ampip-entrega-primeros-20-parques-industriales-del-plan-mexico-con-inversion-de-711-mdd/) |
| Polos de Desarrollo Económico para el Bienestar | Primero inaugurado en Huamantla, Tlaxcala (2026-04-12), > USD 540 M privados; declaratorias 2026 (Cancún, Tuxpan); promotora: Secretaría de Economía | [El Imparcial](https://www.elimparcial.com/mexico/2026/04/13/claudia-sheinbaum-inaugura-en-tlaxcala-el-primer-polo-de-desarrollo-para-el-bienestar-con-inversion-de-540-mdd-y-mas-de-cinco-mil-empleos/) · [Proyectos México, ficha](https://www.proyectosmexico.gob.mx/proyecto_inversion/polos-de-desarrollo-economico-para-el-bienestar/) |
| Monterrey 2T 2026 (Colliers) | Absorción neta 690,857 m² (+166.7% a/a), disponibilidad 7.3%, 55 naves en construcción (1.32 M m²; 60% especulativas), renta de salida USD 7.05/m²/mes | [Vanguardia/Reforma, 2026-07-08](https://vanguardia.com.mx/noticias/mexico/sube-167-absorcion-de-naves-industriales-en-monterrey-pese-a-incertidumbre-por-t-mec-DA22004997) |
| Nacional 3T 2026 (Solili) | Inventario 115.1 M m², vacancia 5.5%; "las empresas ajustan o posponen proyectos" por la revisión del T-MEC | [Solili, 2026-10-05](https://www.solili.mx/noticias/reporte-industrial-solili-tercer-trimestre-2026/8177/) |
| Red eléctrica | CFE: 47 proyectos de transmisión en construcción (MXN 71 mil M) y 77 por licitar (abr 2026); Clúster Energético NL: el cuello es transmisión y distribución, no generación; solicitudes de conexión en NL esperando a CENACE | [Líder Empresarial](https://www.liderempresarial.com/puede-esta-inversion-reducir-los-apagones-en-nuevo-leon/) · [Cluster Industrial](https://clusterindustrial.com.mx/el-desafio-energetico-de-la-industria-en-mexico/) · [BNamericas](https://bnamericas.com/en/news/mexicos-nuevo-leon-state-unveils-energy-plan-for-nearshoring-demand) (403 desde servidor; cifra vía búsqueda) |
| Pérdidas aseguradas por catástrofe | Huracán Otis (2023): AMIS estimó ~MXN 35,500 M en indemnizaciones | [El Financiero](https://www.elfinanciero.com.mx/economia/2023/12/07/entra-otis-al-top-3-de-los-siniestros-mas-caros-del-sector-asegurador/) · [AMIS, avance a ene-2024](https://ern.com.mx/web/sites/default/files/convencion2024/presentaciones/3%20AvanceOTIS12enero_AMIS.pdf) |
| Regulación climática | CNBV incorporó NIIF S1/S2 a la Circular Única de Emisoras (DOF 2025-01-28); el primer ejercicio reportado es 2025 según EY y KPMG (Persefoni dice 2026: **discrepancia**). EY (oct 2026): 62% de organizaciones tiene dificultad para medir el impacto financiero de riesgos de sostenibilidad | [KPMG](https://kpmg.com/mx/es/tendencias/2025/02/ao-cnbv-emisores-mexico-estandares-sostenibilidad-internacional-2025.html) · [EY, comunicado oct 2026](https://www.ey.com/es_mx/newsroom/2026/10/organizaciones-medir-impacto-financiero-riesgos-sostenibilidad) · [Persefoni](https://persefoni.com/blog/mexicos-issb-sustainability-reporting-standards) |

**Lo que dicen juntas:** el dinero existe y es récord, pero (a) casi todo es
reinversión, no llegada nueva; (b) solo una fracción de lo anunciado se
construye; (c) en 3T 2026 la demanda se frena por el T-MEC. El comprador de 2026
**no compra entusiasmo, compra no equivocarse**: agua, red, sequía, ruta. Eso es
exactamente lo que Atlas dice y lo que el inventario de Solili/Colliers no dice.

### 2.2 Compradores por tipo, con evidencia

| Tipo | Por qué compraría | Evidencia pública | Ciclo esperado |
|---|---|---|---|
| **Desarrolladores de parques** (socios AMPIP) | Defender un parque ante un inquilino grande que pregunta por agua y red; elegir dónde comprar reserva territorial | > USD 5,000 M/año de inversión de socios; 103 parques en construcción; 60% de lo que se construye en Monterrey es especulativo (riesgo de vacancia) | Medio. El campeón es el director de desarrollo |
| **FIBRAs industriales** | Due diligence de adquisiciones; reporte NIIF S2 de riesgo físico de la cartera | Consolidación 2026: Fibra Mty tomó el control de Fibra Macquarie (> 80% de aceptación, 343 naves); FIBRA Prologis compró en Monterrey, Toluca y Juárez (USD 67.1 M, dic 2025) y un parque en Monterrey (USD 32.7 M, ago 2026). Son emisoras: les aplica la CUE | Medio-largo. Comité de inversión |
| **Empresas que relocalizan** | Elegir entre dos o tres predios con fecha | IED de nuevas inversiones ~18% de USD 40.9 M; automotriz y electromovilidad ~60% de los anuncios 2026 (Integralia, citado por tercero) | **Corto** si la decisión ya tiene fecha. Llegan vía corredor o shelter |
| **Gobiernos estatales de desarrollo económico** | Promover polos y parques con evidencia; priorizar infraestructura | Plan México (100 parques meta), Polos del Bienestar con comités técnicos de evaluación; Hidalgo con presupuesto 2026 para parques | **Largo** (licitación, presupuesto anual). No cierra en 90 días salvo adjudicación directa por monto |
| **Aseguradoras** | Suscripción de daños industriales con peligro por coordenada; modelación catastrófica | Otis: ~MXN 35,500 M; GNP compra Foundry/AIP para riesgo y suscripción (2026) | Largo; compran a proveedores globales (Moody's/RMS). DGED entra como capa de datos México, no como modelo cat |
| **Bancos de desarrollo y comerciales** | Crédito a parques y naves; reporte TCFD/NIIF S2 | Banorte (Afore XXI Banorte) publica reporte TCFD 2025 | Largo |
| **PyMEs con cotización compleja** | Responder y cotizar más rápido por WhatsApp sin que el bot invente precios | Mercado de herramientas USD 50–250/mes (saturado); implementaciones a la medida publicadas desde USD 1,800 | **Corto** (días a semanas), ticket chico |

Fuentes adicionales:
[El CEO, Fibra Mty–Macquarie](https://elceo.com/mercados/fibra-mty-avanza-en-adquisicion-de-fibra-macquarie-tras-obtener-respaldo-de-mas-del-80-de-los-tenedores/) ·
[Mercado, FIBRA Prologis](https://mercado.com.ar/ladrillos-y-proyectos/fibra-prologis-adquiere-tres-inmuebles-logisticos-en-mexico-por-us-671-millones) ·
[The Logistics World, FIBRA Prologis Monterrey](https://thelogisticsworld.com/actualidad-logistica/fibra-prologis-adquiere-parque-industrial-en-monterrey) ·
[Cluster Industrial, Hidalgo 2026](https://clusterindustrial.com.mx/hidalgo-destina-mas-de-52-8-mdp-en-2026-para-modernizar-parques-industriales-clave/) ·
[Xataka, 15 polos](https://www.xataka.com.mx/otros-1/mexico-quiere-fabricar-comprar-afuera-asi-seran-15-parques-industriales-que-arrancan-2026) ·
[Banorte XXI, TCFD 2025](https://www.xxi-banorte.com/wp-content/themes/banorte-xxi/assets/asg/reporte-tcfd-2025.pdf) ·
[Secretaría de Economía NL, boletín feb 2025](https://www.nl.gob.mx/sites/default/files/repositorio/Dependencias/Secretar%C3%ADa%20de%20Econom%C3%ADa/Noticias/20250205_03_nl_lider_bienes.docx)

### 2.3 Lo que NO se encontró (y no se inventa)

- Ninguna **licitación pública vigente** de "estudio de selección de sitio" o
  "factibilidad de parque industrial" en 2026. Hay que buscar en los portales
  estatales y en ComprasMX directamente; no se hizo desde aquí.
- Ningún **precio público** de Palantir, Jupiter, XDI, Moody's, First Street,
  Datoz, Treble, Tetakawi ni de un dictamen técnico independiente en México.
- El dato de **14.7% anunciado→construido** no tiene autor nombrado.
- Las cifras de parques AMPIP difieren entre notas (477/491 en operación).

Cada uno de estos es una pregunta a medir, no una premisa.
