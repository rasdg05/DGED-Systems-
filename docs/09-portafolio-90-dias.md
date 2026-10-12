# Portafolio de 90 días y primeras 20 cuentas

Fecha: 2026-10-12. Se apoya en [08-mercado.md](08-mercado.md) (fuentes y fechas
de consulta ahí). Los precios de aquí son **propuestas para que el dueño
decida**; los que no están en `docs/04-entrega-precios.md` no cambian D-006
hasta que se escriba una decisión nueva en `DECISIONS.md`.

Reglas que este documento respeta:

- Ningún proyecto promete MW por predio (D-003), ni escenarios climáticos que
  no tenemos, ni que el bot cotice solo.
- "No medido" se dice. Las fuentes en vivo de Atlas **no se han probado desde
  esta copia** (`MEMORY/ESTADO.md`): todo proyecto de Atlas arranca con esa
  medición.
- Ninguna proyección de ingresos es un pronóstico: con n = 0 clientes, no hay
  tasa de cierre que citar.

---

## 1. Los proyectos

Tipo de cambio: no se convierte. Lo que el comprador mexicano paga en pesos se
cotiza en MXN; lo de nearshoring, en USD (como dice `04-entrega-precios.md`).

### P1 — Agente de atención y cotización por WhatsApp para PyMEs

| | |
|---|---|
| Cliente | PyME con **cotización compleja** y volumen por WhatsApp: gestorías, refaccionarias, talleres, distribuidores de autos y maquinaria, servicios técnicos. No la tienda que solo contesta horario |
| Entregable | Agente sobre la **API oficial** de WhatsApp: contesta con frases del negocio (citadas, no redactadas), arma el número con las reglas del cliente y **lo manda a aprobar a una persona** antes de salir; escala lo que no sabe; bandeja de aprobación; tablero de **tiempo hasta la respuesta y hasta la cotización**; 30 días en sombra antes de contestar solo lo que no lleva cifra |
| Qué existe | En producción en Gestor Morelos (repo aparte): guardrails de cifra (`services/ai.py::GUARDRAILS`, `test_blindaje.py`), cotizador separado de la IA, voz citada (`respuestas_rapidas.py`, `voz.py`), turno y ráfaga, consultas con *ok* del asesor, sombra contra la casa, tiempos (`/internal/tiempos`). **No existe**: plantilla multi-cliente, conector a la API oficial (Gestor usa un worker no oficial) |
| Esfuerzo | Primer cliente 4–5 semanas (extraer el núcleo a plantilla + Cloud API + reglas del cliente). Siguientes: 2–3 semanas |
| Precio | **Implementación MXN 90,000–180,000** + **MXN 9,000–18,000/mes** (operación, ajustes, reporte de tiempos). El costo por plantilla de Meta se repercute aparte, a costo |
| Comparables | DuoTach publica USD 1,800 de implementación + desde USD 200/mes; Leadsales MXN 2,363–6,017/mes; Wati USD 49–249/mes (de tercero). Nuestro precio está **varias veces arriba** del chatbot genérico porque incluye el cotizador del cliente, la aprobación humana y la medición. Si tres propuestas seguidas no firman a MXN 90k, se recorta alcance (sin cotizador) y se vuelve a medir; no se regala |
| Riesgo | (1) Canal: con worker no oficial el cliente puede perder su número → solo API oficial. (2) Soporte: cada cliente es un sistema vivo; tope de 3 clientes simultáneos hasta tener plantilla. (3) Que el cliente quiera "que cotice solo": no se vende; la cifra la pone el sistema y la aprueba una persona |

### P2 — Atlas Comparativo: dos o tres predios con fecha de decisión

| | |
|---|---|
| Cliente | Corporativo de manufactura o logístico eligiendo entre predios ya ofertados (el ciclo más corto según `04-entrega-precios.md`). Llega por corredor inmobiliario, shelter o desarrollador |
| Entregable | Memo de 6–8 páginas: los predios lado a lado con sequía, inundación, uso de suelo, acuífero, ruta (si SAKBÉ responde), contexto municipal, cada factor con fuente y corte; escenario de sequía; sección fija **"Qué no dice este estudio"**; nombre del analista DGED |
| Qué existe | `atlas-live-0.1.0`: score con `publishable` (invariante I), conectores INEGI/CONAGUA/Catálogo Único/SAKBÉ, mapa MapLibre, ontología materializada por calificación. **No existe**: plantilla de memo exportable; medición en vivo de las fuentes; claves DENUE/SAKBÉ |
| Esfuerzo | 1 semana de preparación única (medir fuentes, plantilla de memo) + 5 días hábiles por comparativo |
| Precio | **USD 15,000** (hasta 3 predios). **Acreditable al 100%** contra un Atlas Screening firmado dentro de 90 días |
| Comparables | Climate X Spectra Lite: USD 20,000 de entrada, solo ratings, sin memo (AWS Marketplace, público). Jupiter: "desde USD 25,000" según su CEO (prensa). Atlas Screening: USD 55,000 por 12 sitios ≈ USD 4,600/sitio; el comparativo queda en ≈ USD 5,000/sitio, coherente |
| Riesgo | (1) Canibalizar el Screening → crédito al 100% y tope de 3 predios. (2) Fuentes en vivo sin medir → no se vende antes de una corrida real por corredor. (3) Error grosero en un predio conocido → revisión de alguien que haya trabajado parque en NL (`ESTADO.md`, "lo que es del dueño") |

**Requiere decisión del dueño**: es un SKU nuevo debajo de D-006.

### P3 — Evaluación técnica independiente de proyectos

| | |
|---|---|
| Cliente | Quien va a firmar un cheque por un proyecto tecnológico que no sabe auditar: inversionistas y fondos (IA, datos, espacio), corporativos comprando a un proveedor de IA, dependencias evaluando propuestas (p. ej. contrataciones satelitales anunciadas para fines de 2026), aceleradoras |
| Entregable | Dictamen de 10–15 páginas: requisitos explícitos, supuestos, costo defendible contra comparables públicos, riesgos, **hitos verificables con definición de "terminado"**, lo que el proveedor no ha medido, preguntas para la siguiente reunión, recomendación: seguir / seguir con condiciones / no seguir |
| Qué existe | El método, no código: principios de `VISION.md` (hitos, supuestos por escrito, revisión externa), la disciplina "no medido ≠ falló", "n < 30 no concluye", invariantes con test, el cementerio. Este propio repo es la muestra |
| Esfuerzo | 7–10 días hábiles por dictamen |
| Precio | **USD 8,000–15,000** por dictamen según tamaño del proyecto (o su equivalente en MXN para cliente nacional) |
| Comparables | No hay precio público de *technical due diligence* en México (ver 08-mercado §1.6). Referencia por horas: 40–60 h de consultor senior; un dato GSA de un proveedor (2021) pone *Senior Data Scientist* en USD 235.77/h → USD 9,400–14,100. Es un dato aislado y viejo, se dice así |
| Riesgo | (1) Credibilidad sin historial → los dos primeros con descuento declarado a cambio de poder citarlos (sin datos del cliente). (2) Conflicto de interés → cláusula: DGED no vende al evaluado durante 12 meses. (3) Responsabilidad → el dictamen es opinión técnica, no garantía; dicho en contrato y en la portada |

### P4 — Cribado de peligro físico de una cartera (insumo para NIIF S2)

| | |
|---|---|
| Cliente | FIBRAs industriales y desarrolladores emisores (CUE con NIIF S1/S2), banca que financia naves |
| Entregable | Tabla por activo (hasta 50): inundación y laderas (CENAPRED), sismo (CFE), sequía municipal (SMN), disponibilidad del acuífero (CONAGUA/DOF), con banda, fuente y corte; resumen de concentración de la cartera; sección **"Lo que NIIF S2 pide y esto no da"**: escenarios a futuro y pérdida en dinero |
| Qué existe | Sequía, inundación y uso de suelo en el score vivo; resto descrito en `docs/02-fuentes.md` pero sin conector. **No medido**: descarga por servidor de capas CENAPRED, sismo CFE y acuíferos |
| Esfuerzo | 3–4 semanas la primera vez (conectores + corrida por lotes); 1–2 semanas las siguientes |
| Precio | **USD 20,000** hasta 50 activos + USD 150 por activo extra |
| Comparables | Climate X: USD 20,000 base + USD 57–62 por activo comercial, ratings globales con escenarios. Nosotros: sin escenarios, pero fuente oficial mexicana citada por factor y memo firmado. El precio por activo extra va arriba porque incluye revisión del analista |
| Riesgo | (1) El comprador necesita escenarios para cumplir → se dice en la propuesta; DGED es insumo, no el reporte S2. (2) Discrepancia sobre el primer año obligatorio (2025 vs 2026) → no se vende con urgencia regulatoria inventada. (3) Fuentes sin medir → **no se ofrece hasta medirlas** |

### P5 — Auditoría de un modelo con la vara de validación

| | |
|---|---|
| Cliente | Fintech, área de riesgo de crédito, gestor de inversiones o equipo de ciencia de datos con un modelo que "funciona en el backtest" y está por ir a producción o a un comité |
| Entregable | Reporte: holdout fuera de tiempo sellado, validación purgada, placebo, DSR, PBO, cobertura junto al acierto, fugas encontradas; veredicto con la n de cada afirmación |
| Qué existe | La vara de fq-bot y su réplica en Gestor Morelos (`herramientas/vara.py`). **No existe**: versión que corra sobre datos de un tercero sin tocar su infraestructura |
| Esfuerzo | 2–3 semanas |
| Precio | **USD 12,000–20,000** |
| Comparables | Sin precio público encontrado; mismo comparable de horas senior que P3 (60–85 h) |
| Riesgo | (1) Datos confidenciales → se trabaja en la infraestructura del cliente, con NDA. (2) Entidades reguladas tardan en dar de alta proveedores → el ciclo puede pasar de 90 días. (3) Que el modelo falle y el cliente quiera otro veredicto → el reporte no se reescribe; una corrida nueva es otra versión |

### P6 — Ficha de evidencia de un polo o parque (promoción)

| | |
|---|---|
| Cliente | Secretarías estatales de desarrollo económico y desarrolladores que promueven un polo o parque (Plan México, Polos del Bienestar) |
| Entregable | Página pública del polo con sus restricciones físicas y conectividad, cada dato con fuente y corte, actualización trimestral y bitácora de cambios; versión para inversionista |
| Qué existe | Mapa, ontología, score, conectores. **No existe**: vista pública por polo, refresco programado |
| Esfuerzo | 4–6 semanas |
| Precio | **MXN 600,000–1,200,000** el primer año (ancla: Atlas Operate USD 96,000/año) |
| Comparables | Ninguno público. AMPIP y los corredores publican inventario, no restricciones |
| Riesgo | **Compra pública: el ciclo casi seguro pasa de 90 días.** En 90 días se siembra (una ficha de demostración con un parque público), no se cobra. Lenguaje de seguridad: "contexto municipal" como techo |

### P7 — Atlas Screening (el piloto ya definido)

Se mantiene como está en `04-entrega-precios.md`: **USD 55,000** (USD 70,000 si
DGED construye el universo), 6 semanas, 50% al firmar. En este portafolio es el
**destino** de P2, no la puerta: con ciclo de comité, firmarlo dentro de 90
días es posible pero no se planea sobre eso.

---

## 2. Orden recomendado

| # | Proyecto | Por qué primero | Precio |
|---|---|---|---|
| 1 | **P1 Agente WhatsApp** | El código ya corre en producción con dinero real; ciclo de PyME en días; cobra en pesos desde el mes 1 y deja mensualidad | MXN 90k–180k + MXN 9k–18k/mes |
| 2 | **P2 Atlas Comparativo** | Ciclo más corto de Atlas (decisión con fecha), ticket que un gerente aprueba sin comité, y abre el Screening con crédito al 100% | USD 15,000 |
| 3 | **P3 Evaluación técnica** | Cero código nuevo, 7–10 días, y es la línea que mejor sostiene el relato ante inversionistas: "auditamos antes de que nos auditen" | USD 8,000–15,000 |

P4 entra cuarto, **solo después de medir** que CENAPRED, sismo CFE y acuíferos
responden desde un servidor. P5 se ofrece a quien llegue por P3. P6 se siembra.

**Aritmética, no pronóstico.** Si en 90 días cerraran 3 agentes, 1 comparativo y
2 dictámenes, serían MXN 270k–540k de implementación + mensualidades, más
USD 31k–45k. Con n = 0 no hay forma de decir qué tan probable es; el
indicador que se mide es **propuestas enviadas con nombre, empresa y alcance**,
no ingresos esperados.

---

## 3. Primeras 20 cuentas objetivo

Organizaciones, no personas. El contacto con nombre lo consigue el dueño; aquí
no se guardan datos personales.

| # | Organización | Tipo | Proyecto | Por qué (evidencia pública) |
|---|---|---|---|---|
| 1 | Fibra Mty (FMTY) | FIBRA industrial | P4, P2 | Tomó el control de Fibra Macquarie en 2026 (> 80% de aceptación, 343 naves): integra una cartera nueva y es emisora con NIIF S2 |
| 2 | FIBRA Prologis (FIBRAPL) | FIBRA industrial | P4, P2 | Compras en Monterrey, Toluca y Juárez (USD 67.1 M, dic 2025) y un parque en Monterrey (USD 32.7 M, ago 2026): due diligence de adquisiciones |
| 3 | Corporación Inmobiliaria Vesta | Desarrollador emisor | P2, P7, P4 | Desarrollador industrial listado (oferta subsecuente de ~USD 240 M, [Bloomberg Línea](https://www.bloomberglinea.com/latinoamerica/mexico/vesta-recauda-us240-millones-en-una-oferta-subsecuente-de-acciones/), fecha no confirmada); norte y Bajío; emisor con obligación de reporte |
| 4 | Fibra Uno / Fibra Next | FIBRA | P4 | Fibra Next pujó por Fibra Macquarie en 2026: busca crecer en industrial |
| 5 | AMPIP | Asociación | Canal P7/P6 | ~150 socios, ~95% de los parques privados, > USD 5,000 M/año; quiere "mapas de oportunidad" por sector. Canal **después** de un memo real (`04-entrega-precios.md`) |
| 6 | Clúster Energético de Nuevo León | Asociación | P6, P2 | Diagnostica que el cuello es transmisión y distribución: socio natural para el capítulo eléctrico regional (sin MW por predio) |
| 7 | CAINTRA Nuevo León | Cámara industrial | Canal P2, P1 | Agrupa a la industria de NL que relocaliza o amplía |
| 8 | index Nuevo León | Asociación IMMEX | Canal P2 | Manufactureras de exportación eligiendo naves |
| 9 | Colliers México | Corredor/research | Canal P2 | Publica absorción y disponibilidad de Monterrey; no publica restricciones físicas por predio: DGED como capítulo que les falta para sus inquilinos |
| 10 | CBRE México | Corredor/research | Canal P2 | Mismo argumento; publica inventario y renta de Monterrey |
| 11 | Solili | Datos de mercado | Alianza | Vende inventario a MXN 1,449/mes; el memo de restricciones físicas complementa sin competir |
| 12 | Secretaría de Economía de Nuevo León | Gobierno estatal | P6, P3 | > 250 parques en 15 municipios (boletín 2025); promoción con evidencia |
| 13 | Secretaría de Economía de Coahuila | Gobierno estatal | P6 | Top 5 en anuncios de inversión (Integralia) |
| 14 | Secretaría de Desarrollo Económico Sustentable de Guanajuato | Gobierno estatal | P6 | Bajío: segundo corredor de Atlas; Guanajuato aparece entre los estados con polos del Bienestar |
| 15 | Secretaría de Economía (federal), Polos de Desarrollo Económico para el Bienestar | Gobierno federal | P3, P6 | Promotora y convocante de los polos; comités técnicos de evaluación por polo (DOF/Gaceta 2026) |
| 16 | Secihti (programa satelital Ixtli) | Gobierno federal | P3 | Constelación de MXN 540 M con contratación prevista a fines de 2026; 19 entidades gastaron MXN 172 M en imágenes en 2024: evaluación independiente de propuestas |
| 17 | AMIS | Asociación aseguradora | P4 | Otis costó ~MXN 35,500 M en indemnizaciones; capa de peligro mexicana con fuente citada para suscripción de daños |
| 18 | Bancomext | Banca de desarrollo | P4, P3 | Financia infraestructura industrial y exportadora; evaluación de proyectos y peligro físico de garantías |
| 19 | AMDA (distribuidores de automotores) | Asociación PyME/mediana | Canal P1 | Cotización compleja por WhatsApp; Gestor Morelos ya es del sector vehicular |
| 20 | CANACINTRA | Cámara PyME industrial | Canal P1, P3 | Volumen de PyMEs con cotización técnica por WhatsApp |

Fuentes de las filas: ver [08-mercado.md](08-mercado.md) §1.3 y §2. Las filas 3,
7, 8, 18, 19 y 20 se apoyan en lo que la organización es públicamente; su
interés específico **no está medido** y se confirma en la primera conversación.

---

## 4. Lo que es del dueño

1. Aprobar o no el SKU **P2 a USD 15,000** con crédito al Screening (sería D-009).
2. Decidir si P1 se ofrece con el nombre de Gestor Morelos como caso (es su
   negocio; los datos de sus clientes nunca salen).
3. Elegir las tres primeras cuentas de la tabla para conversación con nombre.
