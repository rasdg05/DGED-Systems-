# Arranque en frío — UX y UI del agente a la medida

Fecha: 2026-10-27. Brief para la siguiente sesión, que empieza sin contexto. Leer
antes `MEMORY/00-INDICE.md`, `MEMORY/ESTADO.md`, `DECISIONS.md` (D-016 a D-019) y
`docs/15-agente-a-la-medida.md`.

## El encargo (del dueño)

> "Esto tiene que parecer el Airbnb de Apple."

Lo que le pareció mal de la versión del 2026-10-27, dicho por él: el logo arriba,
el letrero "agente a la medida" ("naco y carente de gusto y estilo todo el sitio"),
las píldoras. Un primer rediseño sobrio (claro, serif, pestañas subrayadas) está
desplegado (`dd8e03a`); es el punto de partida, no el destino.

## Dónde está todo

| Qué | Dónde |
|---|---|
| Servicio en Railway | environment **WhatsApp**, servicio `fabulous-consideration`, dominio `fabulous-consideration-whatsapp.up.railway.app`, rama `claude/agente-a-la-medida`, variable `RAILWAY_DOCKERFILE_PATH=services/agente/Dockerfile`, volumen en `/data` |
| Pantallas | `services/agente/agente/paginas.py` (HTML del servidor, un solo `CSS`, `pagina()` arma todo) |
| Rutas | `/espacios/<id>` tablero · `/alta` · `/vincular` · `/conversaciones` · `/revision` (perfil) · `/banco` · `/v/<id>?t=` (lo único que ve el negocio) |
| Llaves | `?llave=` con `TENANT_INTERNAL_TOKEN` (abre todo) o la derivada del cliente; el enlace del negocio usa `llave_de_vinculacion` y solo abre `/v/` |
| Pruebas de pantallas | `services/agente/tests/test_agente_paginas.py`, `test_agente_vinculado.py` (fijan textos clave: no los rompas sin cambiar el test a propósito) |
| Capturas | se sacan con Playwright y el Chromium de `/opt/pw-browsers` sirviendo la muestra ficticia (ver el historial de esta sesión: `servir.py` + `shots.py` en el scratchpad; rehacerlos es corto) |

Primer negocio: **Finca Emiliano** (espacio `finca-quinta`; propiedades Finca
Emiliano y Quinta Emiliano; Chiconcuac, Xochitepec, Morelos; WhatsApp Business
+52 1 777 496 9880; aprueba Mariana Díaz). Alta completa. Falta: que vinculen su
WhatsApp con el enlace del tablero. Su sitio `fincaemiliano.com(.mx)` no resuelve.
Material visual que ellos publican: volante "Desconectar entre semana ¡Sí se
puede!" (verde bosque, serif, fotos de alberca, jardín, terraza, mesa de evento);
pedir las fotos originales para usarlas.

## Dirección propuesta (superada por D-020: se hizo a mano, sin Basecoat)

- **Componentes: Basecoat** (`github.com/hunvreus/basecoat`, MIT): shadcn/ui en
  HTML + Tailwind sin React, con plantillas Jinja. Encaja con páginas hechas en el
  servidor. Decidir: CDN fijado a versión exacta vs. CSS compilado y vendido en el
  repo (si se vende, regla de `CLAUDE.md`: no se edita a mano).
- **Apple**: fuente del sistema (`-apple-system`), título grande, listas agrupadas
  tipo Ajustes, barras con vidrio (`backdrop-filter`), mucho aire, movimiento sutil.
- **Airbnb**: la foto del negocio como protagonista, tarjetas redondeadas con
  sombra suave, un solo color de acento. Para Finca Emiliano, el verde de su marca.
- **Dos públicos distintos**: el negocio (`/v/`, una sola tarea: vincular; luego
  aprobar perfil y cotizaciones) y nosotros (tablero, conversaciones, banco). Lo del
  negocio va primero y con su marca; lo nuestro puede ser más denso.

## Lo que no se negocia (viene de las invariantes)

- Teléfono del cliente final enmascarado en pantallas; todo texto de cliente escapado.
- El enlace `/v/` no enseña conversaciones, perfil, conteos ni menú (test).
- Cada dato del perfil se enseña con el mensaje de donde salió.
- Nada se enciende sin aprobación del dueño; cotización con aprobación de una persona.
- Sin scroll horizontal a 390 px; funciona sin JS salvo aprobar y guardar.
- Sin datos inventados en maquetas: la muestra es ficticia y está marcada.

## Pendientes alrededor

- Rotar `TENANT_INTERNAL_TOKEN` (quedó escrito en el chat del 2026-10-27).
- Rotar las claves que Railway pidió revocar (incidente del 2026-10-21), en Gestor también.
- Gestor: `test_toque_manana::test_3162_sale_con_morelos_y_la_vieja_se_retira` falla
  en `main` desde `32c1880` (la ronda se renombró a `-numero-2`); no es de la
  corrección de cifras (`4f03c48`).
