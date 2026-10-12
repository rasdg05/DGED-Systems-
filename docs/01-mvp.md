# Alcance del MVP

Horizonte: **12 semanas** hasta poder cobrar un piloto. No hasta “cobertura nacional”.

## Se vende esto

**Atlas Screening**, un proyecto cerrado.

- Un corredor: Monterrey industrial.
- Hasta **12 sitios** traídos por el cliente, o un parque con sus lotes si ya tiene el polígono.
- Universo de contexto del corredor (parques públicos, subestaciones, municipios) para que el predio se compare contra vecinos, no contra la nada.
- Score base + tres escenarios.
- Memo de decisión.
- Cinco asientos y 90 días de acceso de lectura.
- Un taller.

Criterio de “se puede vender”: un analista DGED produce el memo de un predio real en **dos días hábiles** después de recibir las coordenadas, sin pedirle a ingeniería un script nuevo.

## Dentro del software

- Esquema de [ontology/001_init.sql](../ontology/001_init.sql) aplicado.
- Pipeline repetible de las fuentes marcadas “MVP” en [02-fuentes.md](02-fuentes.md), recortadas al corredor.
- `scoreSite()` en producción, misma versión que los tests.
- Lista, mapa, ficha, selector de escenario, export HTML.
- Bitácora del analista: una nota por sitio (`analyst_note`), porque el modelo va a equivocarse en voz alta y eso también es evidencia.

## Fuera, a propósito

| Fuera | Por qué | Cuándo entra |
|---|---|---|
| Bajío, Juárez, Saltillo como producto | Diluye la ingesta | Semana 13+, como corredor 2, cobrado aparte |
| MW disponibles por predio | No hay fuente pública sitio a sitio | Solo como `InterconnectionCase` que aporte el cliente |
| Flujo de potencia, PLD nodal, cola de interconexión CENACE | Licencia y otro producto | Fase 2 si un piloto lo paga |
| Score de seguridad “del parque” | El dato es municipal | Se queda como contexto. Nunca como semáforo de la caseta |
| Usuarios, SSO, facturación | El primer cheque es transferencia contra SOW | Al segundo cliente concurrente |
| App móvil | El usuario está en una sala | No |
| Agentes LLM que redactan el memo | Alucinan MW | Un redactor puede *ayudar* a pasar viñetas ya calculadas. El número sale del score |
| Satélite como feature del score | Se ve serio y no cambia el ranking | Figura opcional en el memo |
| Hardware | No hay sitio instrumentado | Fase 3 |

## Definición de hecho

1. Diez sitios reales del AMM corren de punta a punta.
2. En al menos tres, una persona que haya trabajado un parque en NL revisa la ficha y no encuentra un error grosero (subestación en el centro de la ciudad equivocada, acuífero de otro estado, tiempo de ruta absurdo).
3. Subir la carga de 5 MW a 40 MW en un sitio con holgura `tight` le baja el factor eléctrico y puede cambiar el orden. El test de código ya lo exige; el mapa tiene que mostrarlo.
4. El memo incluye la sección fija **“Qué no dice este estudio”**.
5. `node --test packages/score/score.test.mjs` pasa en CI.

## Métrica comercial, no de vanidad

- Semana 12: cinco conversaciones con nombre, empresa y predio, no “leads”.
- Éxito de los primeros 90 días: **un piloto firmado**. No MRR, no cobertura de estados.
