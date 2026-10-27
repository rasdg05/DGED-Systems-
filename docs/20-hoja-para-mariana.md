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
