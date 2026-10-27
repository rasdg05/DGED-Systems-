# 20 — Hoja para que Mariana confirme la lista de precios

Fecha: 2026-10-27. Sale de `docs/19-lista-de-precios.md` (lo que la casa ya cotizó
por escrito, 217 cotizaciones en 177 pláticas). El texto de abajo se manda tal cual
por WhatsApp. Lo que ella conteste se escribe en la propuesta
(`datos/espacios/finca-quinta/lista_precios/propuesta.json`, fuera de git) y se sube
con `python -m agente.local proponer ... --de-verdad` para que lo apruebe en
Asistente → Precios. **Ningún precio a decidir entra hasta que ella lo diga.**

---

Hola Mariana 👋 Armamos la lista de precios con las cotizaciones que ya has mandado
por WhatsApp. Antes de que el asistente la use, necesito que me confirmes. Contesta
con el número y *sí* o con el precio correcto.

*Lo que ya está claro (confírmalo):*

*FINCA, fin de semana (viernes a domingo), temporada normal*
1. Hasta 13 personas (4 habitaciones): $12,000
2. 14 a 19 personas: $20,000
3. 20 personas (6 habitaciones): $22,000 — a veces diste $25,000 o $28,000
4. 21 a 25 personas (6 habitaciones): $25,000
5. 26 a 30 personas: $30,000
6. 31 a 37 personas: $35,000
7. 38 a 40 personas: $38,000 — a veces diste $35,000

*QUINTA, por noche*
8. 17 a 20 personas, temporada normal: $10,000
9. Fin de año, hasta 10 personas: $8,000
10. Fin de año, 11 a 20 personas: $10,000

*LAS DOS CASAS*
11. 41 a 50 personas, fin de semana: $45,000

*EXTRAS Y REGLAS*
12. Alberca climatizada de la finca: $2,000 por día
13. Alberca climatizada de la quinta: $900 por día
14. Visitas: $100 por persona
15. Fin de año: mínimo 3 noches
16. ¿Fin de año va del 23 de diciembre al 1 de enero (noches)? Si no, ¿de qué día a qué día?
17. ¿Cuánto es el anticipo para apartar? (¿50%?)

*Lo que todavía no tiene un precio fijo (dime cuál es):*

18. Quinta, temporada normal, 5 a 16 personas, por noche. Has dado de $3,000 a $9,000; lo más común, $5,000. ¿Va por escalones? (ej. hasta 10 = ?, 11 a 16 = ?)
19. Quinta, fin de semana completo. Has dado de $6,000 a $15,000; lo más común, $12,000.
20. Finca, una sola noche. Has dado $15,000, $16,000 y $20,000.
21. Finca en fin de año, por noche (una vez diste $17,000).
22. Las dos casas, una sola noche (una vez diste $22,000).
23. ¿Semana Santa, puentes o Navidad antes del 23 tienen otro precio?

*Calendario:*

24. ¿Dónde apuntas hoy lo que ya está rentado? (cuaderno, Google Calendar, Airbnb, Booking)
25. Si usas Airbnb, Booking o Google Calendar, pásame el enlace para *exportar el calendario* (iCal) de cada casa. Así el asistente no cotiza fechas ocupadas. Te digo dónde está en cada una.

Gracias 🙏

---

## Dónde está el enlace del calendario (para la pregunta 25)

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
