# Plan de 12 semanas

Fecha de arranque de referencia: semana del **13 de octubre de 2026**. Una persona construye, con revisión externa de un conocedor de parques en Nuevo León en las semanas 9 y 10. Si esa revisión no existe, no se sale a vender.

Cada semana cierra con algo que se puede abrir, no con un avance porcentual.

## Semana 1 — Contrato interno

- Congelar este directorio como alcance. Cambios solo por nota en `DECISIONS.md`.
- Conseguir el PRODESEN vigente y escribir la clase de holgura de Noreste en una fila `evidence`, aunque sea `tight` o `moderate`, con párrafo citado y página.
- Lista de 10 sitios reales públicos (parques con coordenadas en su propia web) para la prueba. No son una demo comercial todavía.
- Salida: `DECISIONS.md` con la clase eléctrica y los 10 nombres.

## Semana 2 — El número existe antes que el mapa

- Aplicar `ontology/001_init.sql` en Postgres local.
- Dejar `packages/score` como dependencia del futuro job, sin cambiar la fórmula.
- Fixture JSON de los 10 sitios con features **a mano y marcados `manual`**, para atravesar ficha y memo antes de tener ETL.
- Salida: un score publicable y uno no publicable corridos desde SQL o desde un script de una sola vía.

## Semana 3 — Geografía que no miente

- Cargar marco geoestadístico recortado a los municipios del corredor.
- Cargar acuíferos de NL y el monitor de sequía del último corte.
- Snap: cada sitio de prueba muestra municipio, `cvegeo` y acuífero.
- Salida: tres sitios abiertos al azar caen en el municipio correcto.

## Semana 4 — Electricidad de cribado

- Cargar subestaciones y líneas OSM del recorte.
- Calcular `distSubstationKm` y `voltageKnown`.
- Revisar a mano las cinco subestaciones más cercanas a los 10 sitios. Suprimir las que estén mal.
- Salida: ningún sitio de prueba usa una subestación claramente falsa. Los que no tengan voltaje quedan capados por el modelo, sin excepción en la UI.

## Semana 5 — Agua y peligro

- Feature de sequía municipal y clase de inundación (buffer 500 m).
- Zona sísmica y laderas.
- Salida: la ficha de un sitio en zona de inundación alta lo dice con la clase cruda al lado del puntaje.

## Semana 6 — Ruta, gente, contexto delictivo

- Minutos a Puente Colombia y a Altamira para los 10 sitios.
- Percentil laboral municipal.
- Percentil de incidencia. Releer las frases. Si una suena a diagnóstico del predio, se cambia el texto del código.
- Salida: dos sitios del norte del área metropolitana rankean mejor en logística que dos del sur, o se documenta por qué no. Si el router no discrimina, se arregla el router, no el peso.

## Semana 7 — Mesa de decisión

- Lista rankeada, mapa del corredor, ficha con raw + caveat + snapshot.
- Cambiar de escenario no recarga “un insight”: recalcula y muestra quién subió y quién bajó.
- Salida: demo de 8 minutos sin decir “imaginen que aquí iría”.

## Semana 8 — Memo

- Plantilla HTML de 8–12 páginas con la sección fija de limitaciones.
- Los números del memo salen del `score_snapshot`, no se vuelven a teclear.
- Salida: imprimir a PDF un sitio y un portafolio de 12 sin editar texto a mano.

## Semana 9 — Adversario

- El revisor de NL intenta romper cinco fichas.
- Cada error grosero se vuelve un `analyst_note` y, si es del modelo, un test.
- Salida: lista de errores cerrada o explícitamente aceptada.

## Semana 10 — Paquete de venta

- Un memo de muestra **anonimizado** si hace falta (sitio público, sin cliente).
- SOW de una página con precio, exclusiones y calendario de 6 semanas.
- Lista de cinco empresas con nombre de persona. No se manda nada todavía.
- Salida: el SOW cabe en un correo.

## Semana 11 — Las cinco conversaciones

- Se habla con las cinco. Se enseña el memo, no un pitch de plataforma.
- Se anota la objeción literal. Las objeciones no cambian el alcance de esta versión salvo que revelen un error de la semana 9.
- Salida: bitácora de objeciones en `DECISIONS.md`.

## Semana 12 — Cerrar o repetir

- Si hay un interesado con predios: propuesta Screening a USD 55,000 o 70,000 según quién traiga los puntos.
- Si no hay interesado: no se abre el Bajío. Se rehace la lista de cinco con la objeción que más se repitió.
- Salida: una propuesta enviada, o una razón escrita de por qué las cinco dijeron que no.

## Después de la semana 12

Solo si hay piloto firmado o una objeción que ya esté pagada:

- Segundo corredor.
- `InterconnectionCase` para meter el oficio que el cliente sí tiene.
- Refresco trimestral automatizado.

Sensores, drones y cualquier pieza física quedan fuera de este calendario.
