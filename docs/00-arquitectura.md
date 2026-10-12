# Arquitectura de producto — Atlas 0.1

## Problema que se cobra

Una planta que se ancla mal en Nuevo León no falla en un dashboard. Falla cuando el centro de carga no tiene capacidad en el plazo de la nave, cuando el acuífero que “venía en el brochure” está en déficit, o cuando el cruce y el puerto que justificaron el predio no son los que opera el cliente.

El comprador hoy arma eso con un broker, un electricista, un PDF de PRODESEN y una visita. Cada predio es un hilo de correo. No hay un objeto `Site` con evidencia, fecha y supuesto.

Atlas es el sistema donde esa decisión queda escrita, repetible y comparable.

## Usuarios

| Quién | Qué hace en Atlas | Qué no hace |
|---|---|---|
| Analista DGED | Carga predios, corre features, revisa evidencia, publica el memo | No inventa MW |
| Director inmobiliario o de energía del cliente | Lee ranking, mueve un escenario, exporta | No modela la red |
| Consejo / IC del fondo | Lee el memo de 8–12 páginas | No entra al mapa salvo que quiera |

El login del cliente es secundario. El objeto que viaja solo es el **memo**. Si el mapa no sirve para producir el memo, no se enseña.

## Módulos

Seis. Ni uno más en el MVP.

### 1. Registro de objetos

Sistema de registro en Postgres/PostGIS. Un sitio, un parque, una subestación, un acuífero, un corredor y un municipio son filas con geometría. Las relaciones no viven en un grafo aparte: viven en `link`.

Todo número que ve el usuario apunta a una fila de `evidence` (fuente, URL, fecha de extracción, licencia, resolución, confianza).

### 2. Ingesta

Jobs por fuente, no un “lago”. Cada corrida escribe un `dataset_snapshot` inmutable (`inegi.marco.2024`, `osm.power.2026-10-10`, `conagua.sequia.2026-09`). Los features de un sitio se calculan contra un snapshot, nunca contra “lo último que haya en el disco”.

La ingesta de arranque es por corredor: se recorta Nuevo León, no se procesa el país.

### 3. Features de sitio

Función pura de geometría → `site_feature_snapshot.features`. Distancias, clase de peligro, percentil municipal. Si un insumo falta, el feature es `null`. No se imputa con el promedio del corredor.

### 4. Score

`packages/score`, modelo `atlas-screen-0.1.0`. Seis factores, pesos visibles, renormalización si falta un factor, bandera `publishable`.

Un score no se publica si la cobertura de pesos es menor a 0.75 o si falta energía. Energía ausente y un número bonito al lado es el fallo que quema la empresa.

### 5. Escenarios

Tres, paramétricos, sin simulador de red ni hidráulico:

| kind | Parámetro | Efecto |
|---|---|---|
| `load_mw` | MW que el cliente quiere conectar | Castiga holgura `tight` y `constrained` |
| `drought_year` | año seco (tipo 2022) | Fuerza el monitor de sequía a un piso duro |
| `corridor_delay` | minutos extra de ruta | Empeora frontera y puerto |

El resultado que importa es el **cambio de ranking** contra el caso base, no un mapa de calor nuevo.

### 6. Mesa de decisión

Tres piezas de interfaz:

1. **Lista rankeada** del portafolio activo (los predios de este cliente, no todos los parques de México).
2. **Mapa** MapLibre. Capas: sitios, parques, subestaciones, acuífero, peligro de inundación, municipio. El color del sitio es el factor seleccionado, no un “riesgo” mezclado.
3. **Ficha**. Identidad, desglose del score, caveats literales del modelo, evidencias, delta del escenario.

Exportación: un HTML imprimible (el PDF sale del navegador). Plantilla fija. Sin editor de documentos.

## Flujo de un piloto

```text
predios del cliente (pines o polígonos)
        ↓
snap al municipio y al corredor
        ↓
features contra snapshots congelados
        ↓
score base + 3 escenarios
        ↓
analista marca anomalías (subestación OSM duplicada, parque mal dibujado)
        ↓
memo con cobertura, caveats y “qué no dice este estudio”
        ↓
taller de 90 minutos
        ↓
si pagan la anualidad: los mismos objetos siguen vivos y se refrescan cada trimestre
```

## Lo que Atlas no es

- No es Foundry, ni un mercado de datos, ni un gemelo digital de la ciudad.
- No es el mapa de inventario de AMPIP/Colliers. Ese mapa dice cuánta nave hay. Atlas dice si el predio aguanta el supuesto del cliente.
- No es un dictamen eléctrico, hidrológico, ambiental o de seguridad física. Esos se citan cuando existen. Si no existen, el memo lo dice.
- No hay agentes que “recomienden invertir”. Hay una fórmula y una persona que la firma.
- No hay fusión satelital en vivo en v1. Una imagen Sentinel de contexto puede ir al memo como figura; no entra al score.

## Cómo crece sin tirar la ontología

Fase 2 mete objetos nuevos (`Asset`, `InterconnectionCase`, `Concession`, `Alert`) y fuentes nuevas. El `Site` no se reemplaza.

Fase 3 mete hardware como otra evidencia: un sensor de nivel, un medidor, un dron, escriben `evidence` con `confidence = verified` sobre un `Asset` que ya pertenece a un `Site`. Si el sitio no existe como objeto, el dron es un hobby.
