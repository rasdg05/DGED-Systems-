# Plug and play — un negocio nuevo en cinco minutos

Fecha: 2026-10-27 (D-023). El esqueleto de `services/agente` se copia a cada negocio sin tocar código:
un espacio por cliente, con su nombre, su color y su foto.

## Alta de un negocio

1. Abrir `https://<dominio>/negocios?llave=<TENANT_INTERNAL_TOKEN>` (solo DGED; con otra llave responde 404).
2. **Nuevo negocio**: nombre comercial y color de su marca. El identificador se arma solo del nombre
   (`Clínica Dental Sonrisa` → `clinica-dental-sonrisa`) y no cambia después.
3. Copiar los dos enlaces de su renglón y entregarlos:
   - **Panel del dueño**: Inicio, Chats, Asistente y Negocio. Se instala como app desde Safari
     (Compartir → Agregar a pantalla de inicio), con su inicial y su color.
   - **Enlace para conectar**: solo la pantalla de vincular WhatsApp, con su portada.
4. El dueño completa en Negocio sus datos (qué ofrece, cómo cobra, quién aprueba) y sube su foto.

Nace **aprendiendo** (`encendido: sombra`): no le contesta a nadie hasta que su dueño aprueba a su asistente.

## Una demo para un prospecto (D-055)

Un servicio de Railway aparte, sobre su propia rama, con volumen en `/data` y las variables
`TENANT_INTERNAL_TOKEN`, `AGENTE_MUESTRA=<carpeta de muestra/>` (hoy `clinica`) y
`AGENTE_ESPACIO_MUESTRA=<id>`. El primer arranque siembra el espacio con la muestra ficticia, el perfil
aprobado y la Cola con lo que haría el agente; los siguientes no lo tocan. Si el prospecto se queda,
vincula su WhatsApp con `AGENTE_ESPACIO_VINCULADO` y su historial real reemplaza la muestra en un espacio nuevo.

## Lo que hacemos nosotros (taller, sin pestaña)

`/espacios/<id>/banco?llave=<maestra>`: proponer perfil (una pasada del modelo grande sobre el historial),
banco pass^k, sombra, descargar historial. El cliente no lo ve ni por URL (D-022).

## Lo que todavía depende del giro

- El cotizador entiende reglas de renta (noche, fin de semana, temporada, evento, persona extra, mínimo,
  anticipo, depósito). Los servicios por sesión, zona o paquete (clínica, spa) cotizan con `servicios.py` (D-055). Otro giro cotiza con reglas genéricas que se enseñan tal cual; reglas propias de un
  giro nuevo se agregan en `cotizador.py` y en `_regla()` de `paginas.py` **después** de medir su sombra.
- Un lector vinculado por servicio (`AGENTE_ESPACIO_VINCULADO`): un segundo negocio que conecte su WhatsApp
  necesita su propio servicio de Railway hasta que haya coexistencia oficial (D-016) o un lector multi-espacio.
- Subcuentas (dueño, encargado, DGED): pendiente; hoy la llave del panel abre todo lo del negocio.

## Safari en iPhone (lo que hay que cuidar al copiar)

Test `test_pag_reglas_de_safari_en_iphone`. Sin números convertidos en enlace (`format-detection`), ícono PNG de
180 px para la pantalla de inicio, `viewport-fit=cover` y áreas seguras (también laterales), teclado de teléfono
en los campos de teléfono, zonas de toque de 44 px, respaldo sin `color-mix` para iOS 15, y refresco al volver a
la app instalada (iOS no tiene "jalar para recargar" en modo app). Auditado con el perfil de iPhone 15 en Chromium
(9 pantallas, claro y oscuro, sin desbordes ni errores de JS); **no medido en Safari real** (sin WebKit en el entorno).
