# Producto 4 — Agente a la medida que se construye con los datos del negocio

Fecha: 2026-10-21. Dirección del dueño (D-016). **Especificación y entrega para
la siguiente sesión de código; aquí no hay código.** Parte de P1
(`docs/09-portafolio-90-dias.md`): mismo precio, mismo cliente, mismas reglas.

## La idea en una línea

El negocio no se adapta a la plataforma: la plataforma se arma alrededor del
negocio. El cliente da unos datos básicos, conecta su WhatsApp Business con un
QR y, a partir de su propio historial, el sistema construye su perfil, su voz
y sus reglas de cotización. **Lo que vale es el dato del negocio, no el
software.**

## Lo que se hereda (repos aparte, hay que agregarlos a la sesión)

| De | Qué se toma | Dónde vive hoy |
|---|---|---|
| `rasdg05/Gestor-Morelos` | El núcleo del agente: guardrails de cifra (`services/ai.py::GUARDRAILS`, `test_blindaje.py`), cotizador separado de la IA, voz citada (`respuestas_rapidas.py`, `voz.py`), turno y ráfaga, consultas con *ok* del asesor, sombra contra la casa, tiempos (`/internal/tiempos`) | En producción, un solo negocio, worker **no oficial** |
| `rasdg05/fq-bot` | La vara de medición: holdout fuera de tiempo, placebo, cobertura junto al acierto, "n < 30 no concluye" (`herramientas/vara.py` también replicado en Gestor) | Repo aparte |
| Este repo | Ontología como contrato JSON materializado (`ontology/atlas.ontology.json`, D-004), Oráculo con cifras verificadas contra herramientas (D-010), llave interna y tope por IP (`services/api/atlas/access.py`), memoria e invariantes con test | `main` |

La siguiente sesión empieza con `add_repo` de los dos repos y lee su
`MEMORY/` antes de extraer nada.

## El flujo

1. **Alta (≈5 min).** Formulario corto: giro, nombre comercial, qué vende,
   cómo cobra hoy (lista de precios, foto, PDF o "de memoria"), horario, quién
   aprueba las cotizaciones y su teléfono.
2. **Conexión por QR, por la vía oficial.** El cliente escanea un QR desde su
   app de WhatsApp Business y queda conectado a la **Cloud API** sin perder su
   app ni su número: es el *Embedded Signup* con **coexistencia** de Meta
   (app de WhatsApp Business + Cloud API en el mismo número, con importación
   de historial). **No medido**: si está disponible para números de México,
   cuánto historial importa de verdad (se anuncian hasta 6 meses) y qué exige
   el alta de la app de Meta de DGED (Business verification, revisión de la
   app). Es lo primero que se mide, antes de escribir el conector
   (regla de `CLAUDE.md`: una fuente se mide antes de escribir su código).
3. **Simbiosis (ingesta del historial).** Del historial importado y de lo que
   dio el alta salen, en este orden:
   - **Perfil del negocio** como contrato JSON por cliente, igual que la
     ontología de Atlas: objetos del giro (en la demo: `Propiedad`, `Tarifa`,
     `Temporada`, `Reserva`, `Evento`, `Prospecto`), sus campos y de qué
     mensaje salió cada dato.
   - **Voz**: frases reales del negocio, citadas con su mensaje de origen.
   - **Reglas candidatas de cotización** (por noche, por fin de semana, por
     evento, por persona, depósito, anticipo) como **tabla de datos**, no como
     texto para el modelo.
   - **Preguntas frecuentes** y qué casos escala hoy la persona.
   Nada de esto se activa solo: el dueño del negocio lo aprueba en una
   pantalla de revisión. Cada dato muestra el mensaje de donde salió; lo que no
   tiene origen no entra (la misma regla del lector del cuarto de datos, D-013).
4. **Sombra (30 días, como P1).** El agente redacta y no envía; se compara
   contra lo que la persona contestó de verdad. Métricas de la vara: % que la
   persona habría enviado sin editar, errores de cifra (deben ser 0, porque la
   cifra la pone el cotizador), tiempo hasta la respuesta y hasta la
   cotización. **n < 30 conversaciones no concluye** para encender nada.
5. **Encendido por partes.** Primero contesta solo lo que no lleva cifra; la
   cotización siempre sale con aprobación de una persona (P1, sin excepción).
6. **Afinación con Claude desde el día uno.** Cada cliente tiene un espacio
   con llave interna (`TENANT_INTERNAL_TOKEN`, mismo patrón que
   `ATLAS_ACCESS_TOKEN`) y un servidor MCP con herramientas para un agente de
   código: leer el perfil, ver conversaciones en sombra, ver métricas, proponer
   un cambio de regla o de voz. **Una propuesta no se aplica sola**: queda como
   versión nueva con nombre y se activa cuando la aprueba el dueño del negocio.
   Así se afina el modelo del negocio desde la primera instalación sin tocar
   producción a mano.

## El canal: por qué no el QR de WhatsApp Web

Conectar escaneando el QR de **WhatsApp Web** (venom-bot, whatsapp-web.js,
Baileys) es el worker no oficial que usa Gestor Morelos. `08-mercado.md` §1.5 y
P1 ya lo dejaron escrito: con ese canal **el cliente puede perder su número**, y
para clientes se usa solo la API oficial. La coexistencia de Meta da la misma
experiencia que buscamos (QR, la app sigue funcionando, se trae historial) por
la vía oficial. Si la medición del paso 2 sale MUERTA para México, el plan B se
decide con el dueño y va al cementerio con su fecha; no se cambia de canal en
silencio.

## Que no se coma el presupuesto de API

El costo se diseña desde el principio, no se descubre en la factura:

- **Una pasada cara, una sola vez.** El perfil del negocio se construye una vez
  con el modelo grande (`claude-opus-5-5`); después se actualiza por
  diferencias, no se reconstruye.
- **Historial en lote.** La clasificación de mensajes del historial va por la
  Batch API y con el modelo chico (`claude-haiku-5-5`). Es trabajo de fondo,
  no de tiempo real.
- **Turnos de rutina con el modelo chico**; el grande solo para lo que el chico
  escala y para la afinación.
- **Perfil en caché**: el contrato del negocio va al inicio del prompt para que
  la caché de prompts lo reuse en cada turno.
- **Respuestas guardadas primero**: si una pregunta frecuente ya tiene frase
  aprobada, se contesta sin llamar al modelo.
- **Tope por cliente** (`TENANT_TOPE_USD_MES`) y contador de gasto por cliente.
  Al llegar al tope el agente deja de llamar a la API y todo pasa a la persona.
- Precios por token: **se consultan con la skill `claude-api` al implementar**,
  no de memoria. Con esos precios se calcula el costo de un cliente típico
  antes de prometer la mensualidad (MXN 9,000–18,000).

## Invariantes que la siguiente sesión escribe como test

Hoy son notas (regla de `CLAUDE.md`). Suben a `MEMORY/CONSTITUCION.md` cuando
tengan su test:

1. Ninguna cifra sale en un mensaje si no la produjo el cotizador de ese
   cliente (se hereda de `GUARDRAILS`/`test_blindaje.py`).
2. Ninguna cotización sale sin aprobación de una persona.
3. Ningún dato del perfil existe sin el mensaje o documento de donde salió.
4. Los datos de un cliente nunca aparecen en el contexto, la caché ni las
   herramientas de otro.
5. Al llegar al tope de gasto, cero llamadas a la API para ese cliente.
6. Un cambio propuesto por un agente de código no toca producción hasta que se
   aprueba; queda como versión nueva y la anterior se conserva.
7. Sin conector oficial configurado, el agente no envía nada (duerme con
   mensaje claro, como el Oráculo sin clave).
8. No se guardan datos personales de los clientes finales fuera del espacio del
   negocio, y se borran al terminar el contrato.

## Orden de trabajo para la siguiente sesión

1. `add_repo` de Gestor-Morelos y fq-bot; leer su `MEMORY/`.
2. Medir la coexistencia de Meta y el alta de la app de DGED. Resultado a
   `MEMORY/FUENTES.md` o al cementerio.
3. Extraer el núcleo de Gestor a un paquete con un cliente por espacio
   (`services/agente/`), con los tests de blindaje que ya existen.
4. Perfil del negocio como contrato JSON y la pantalla de aprobación.
5. Cotizador por reglas de datos, con la demo de propiedades vacacionales como
   primer caso.
6. Sombra y vara; tablero de tiempos.
7. Llave interna y MCP de afinación.
8. Tope de gasto y contador por cliente.

No se empieza por la pantalla. Un agente bonito que inventa una tarifa es peor
que no tener agente.

## Primera demo: propiedades vacacionales (2026-10-22)

Cliente: un familiar del dueño con dos propiedades. Una **finca** para eventos
o familias grandes y una **quinta** más chica. Quiere llenarlas de manera
sostenible. No se guardan nombres ni teléfonos en el repo.

Al día de la demo **el producto no existe en código**. La demo es: la
presentación (`docs/presentacion/`), el flujo de este documento y la captura
de los datos que harán falta. Lo que hay que salir sabiendo, por propiedad:

- Capacidad (personas que duermen, aforo de evento) y qué incluye.
- Tarifas: por noche, fin de semana, semana, evento; temporada alta y baja;
  mínimo de noches; precio por persona extra.
- Depósito, anticipo, cancelación, horario de entrada y salida, reglas (ruido,
  hora límite de evento, mascotas, alberca).
- Dónde vive hoy el calendario (cuaderno, Google Calendar, Airbnb/Booking con
  iCal) y quién confirma.
- Por dónde llegan los prospectos y cuántos al mes; cuántos se pierden por
  tardar en contestar.
- Con su permiso, 20 a 50 conversaciones reales de WhatsApp para la voz y las
  reglas (sabiendo que n < 30 no concluye).
- Qué significa "llenar de manera sostenible" para ellos: ocupación, menos
  descuento, clientes que regresan, menos días muertos entre semana.

Casos de uso del agente para este giro: contestar disponibilidad y qué
incluye, armar la cotización con sus reglas para que la aprueben, dar
seguimiento a prospectos que no contestaron, avisar de huecos entre semana a
clientes anteriores (solo con plantillas aprobadas por Meta y con su permiso) y
lista de espera para fechas llenas.

## Lo que es del dueño

- Cuenta de Meta Business de DGED, verificación y la app para el Embedded
  Signup.
- Clave de Anthropic para el agente (y si va con la misma cuenta que el
  Oráculo y el lector).
- Si el familiar es cliente que paga o caso de demostración citado (y con qué
  nombre se cita).
- El tope de gasto por cliente que se acepta antes de ajustar la mensualidad.
