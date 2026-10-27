# 20 — Hoja para que Mariana confirme la lista de precios

Fecha: 2026-10-27. Sale de `docs/19-lista-de-precios.md` (lo que la casa ya cotizó
por escrito, 217 cotizaciones en 177 pláticas). El texto de abajo se manda tal cual
por WhatsApp. Lo que ella conteste se escribe en la propuesta
(`datos/espacios/finca-quinta/lista_precios/propuesta.json`, fuera de git) y se sube
con `python -m agente.local proponer ... --de-verdad` para que lo apruebe en
Asistente → Precios. **Ningún precio a decidir entra hasta que ella lo diga.**
Versión corta a pedido del dueño ("parece examen"): la lista va en bloque para un
solo "sí" y se preguntan 3 cosas. Lo que no se pregunta y sigue a decidir: finca en
fin de año por noche, las dos casas una noche, anticipo, Semana Santa y puentes; se
piden cuando salgan en una plática.

---

Hola Mariana 👋 Armé la lista de precios con lo que ya cotizas por WhatsApp. ¿Está bien así?

*Finca* (fin de semana)
Hasta 13 personas $12,000 · hasta 19 $20,000 · 20 $22,000 · hasta 25 $25,000 · hasta 30 $30,000 · hasta 37 $35,000 · hasta 40 $38,000

*Quinta* (por noche)
Hasta 20 personas $10,000 · fin de año hasta 10 personas $8,000

*Las dos casas* (fin de semana): $45,000
*Alberca*: finca $2,000 / quinta $900 por día · *Visitas*: $100 por persona
*Fin de año* (23 dic – 1 ene): mínimo 3 noches

Solo me faltan 3 cosas:
1. ¿Cuánto cobras la quinta para grupos chicos (menos de 16) y por fin de semana?
2. ¿Cuánto cobras la finca por una sola noche?
3. ¿Dónde apuntas lo que ya está rentado? Si es en Airbnb, Booking o Google Calendar, te pido el enlace para conectarlo.

Gracias 🙏

---

## Lo que contestó — 2026-10-27 (WhatsApp, capturas del dueño)

| Hora | Quién | Texto literal | Cómo se lee |
|---|---|---|---|
| 12:31 | DGED | La hoja de arriba, tal cual | |
| 13:47 | Mariana | "Si ándale así" | **La lista en bloque queda confirmada** (finca por grupo, quinta 10k y fin de año 8k, las dos casas 45k, alberca, visitas, mínimo 3 noches en 23 dic – 1 ene). |
| 14:02 | Mariana | "1.depende si son menos habitaciones como 3 podría dejarles en 5,000 para 6 personas" | Quinta chica: **5,000 para 6 personas con 3 habitaciones**, en "podría". No dice si es la noche (lo más probable: es la moda de lo que ya cotizó la noche, 7 de 14) ni contesta la quinta en **fin de semana**. Sigue a decidir. |
| 14:02 | Mariana | "Una sola noche para 25 podría variar si 12,000 o 15" | Finca una noche para 25: **entre 12,000 y 15,000**, sin decir qué decide. Sigue a decidir; el cotizador no elige una de las dos. |
| 14:12 | Mariana | "3. Ya estoy anotando en google calentar pero tenngo que hacerlo y compartirtelo" | Calendario: **Google Calendar**, todavía a medias. |
| 14:15 | DGED | "No, nada más es para que lo tengas en calendar de tu cuenta y se conectas con la misma herramienta" | Falta el enlace iCal secreto de su cuenta (instrucciones abajo). |

Qué hacer con esto, en la máquina donde vive `datos/espacios/finca-quinta/`:

1. En `lista_precios/propuesta.json`, marcar la lista en bloque como confirmada por
   ella con la cita de las 13:47, y subirla (`python -m agente.local proponer ...
   --de-verdad`) para que la apruebe en Asistente → Precios. Confirmar por WhatsApp
   no es aprobar en la pantalla: la cifra sale hasta que la apruebe ahí.
2. **No** volver regla los 5,000 de la quinta chica ni la finca una noche: los dos
   llevan "podría" y el segundo da dos cifras. Para cerrarlos, una pregunta cada uno:
   - "¿Los $5,000 de la quinta para 6 son por noche? ¿Y por fin de semana?"
   - "Para la finca una noche con 25, ¿qué hace que sea $12,000 o $15,000? (¿día de la semana, temporada, alberca?)"
3. Cuando tenga el calendario en su cuenta, pedirle la dirección secreta iCal y darla
   de alta con `agente.calendario fuente` (no va a git ni al chat).

## Dónde está el enlace del calendario (para la pregunta 3)

- **Airbnb**: Anuncios → la casa → Disponibilidad → Conectar calendarios →
  *Exportar calendario* → copiar el enlace.
- **Booking.com**: Extranet → Tarifas y disponibilidad → Sincronizar calendarios →
  *Exportar calendario* → copiar el enlace.
- **Google Calendar** (en computadora): Configuración → el calendario de la casa →
  *Dirección secreta en formato iCal* → copiar.

Cada enlace se da de alta con
`python -m agente.calendario fuente finca-quinta <finca|quinta> <airbnb|booking|google> <url>`
o con `POST /espacios/finca-quinta/calendario/fuentes`. Los enlaces abren el
calendario a quien los tenga: no van a git ni al chat.
