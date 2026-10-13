# Ojo satelital de obra — prototipo de detección de cambio con Sentinel-2

Medido el 2026-10-13. Prototipo, **no producto**: habilita lo que
`docs/13-comparables-precio.md` §2 (monitoreo de avance de obra) y §3 (radar de
naves nuevas) dicen que hay que **medir antes de vender**. No entra al número de
Atlas ni toca `services/api/`.

Código: `services/satelite/` (paquete aislado, `requirements.txt` propio).
Tests sin red: `services/satelite/test_satelite.py` (29).

## 1. Cómo funciona

```bash
cd services/satelite && pip install -r requirements.txt
python -m satelite.cambios --lat 25.7789 --lon -100.1886 \
    --antes 2024-01-01:2024-03-31 --despues 2026-07-01:2026-09-30 \
    [--radio 1500] [--nombre apodaca] [--salida carpeta] [-v]
python -m satelite.lote --antes 2024-01-01:2024-04-30 --despues 2026-01-01:2026-04-30 \
    --salida ../../docs/satelite/seca-2024-2026      # los 10 sitios de seed.py + 2 obras
```

1. **Búsqueda** (`satelite/stac.py`): Sentinel-2 L2A en Earth Search
   (Element84), sin clave (`MEMORY/FUENTES.md`, `stac.earthsearch.s2`, VIVA).
   Se descartan escenas con nubosidad publicada ≥ 90 %; las demás se ordenan por
   esa cifra y se evalúan las 8 primeras **por mosaico MGRS**.
2. **Nubes en el recorte, no en la escena**: de cada candidata se lee solo el
   SCL (clasificación de Sen2Cor) del disco pedido. No es superficie observada:
   0 sin dato, 1 saturado, 3 sombra de nube, 8–9 nube, 10 cirro, 11 nieve. La
   nubosidad del recorte es esa fracción dentro del círculo.
3. **Emparejar** (`stac.emparejar`): las dos fechas salen del **mismo mosaico**
   (misma rejilla de 10 m). Entre las escenas limpias (recorte ≤ 5 % nublado)
   se elige el par con el **día del año más parecido**, para que la estación
   pese menos; si una ventana no tiene escena limpia, se toma la menos nublada.
4. **Lectura**: solo la ventana del recorte de cada COG (`rasterio`, lectura
   por rangos HTTP). Bandas: azul, verde, rojo, NIR (10 m) y SWIR 1.6 µm (20 m,
   remuestreado por vecino a 10 m), con la escala y el offset que publica el
   item (`raster:bands`: 0.0001 y −0.1 desde la línea base 04.00).
5. **Índices** (`satelite/indices.py`): NDVI, NDBI, BSI y brillo visible.
6. **Clasificación por píxel** (solo donde se ve la superficie en **las dos**
   fechas y dentro del círculo):

   | Tipo | Regla |
   |---|---|
   | `vegetacion_a_suelo` | NDVI antes ≥ 0.30, ΔNDVI ≤ −0.20, NDVI después < 0.30, y después sigue pareciendo suelo |
   | `vegetacion_a_construido` | lo mismo, pero después BSI ≤ 0 y el brillo sube ≥ 0.04 (techo o pavimento) |
   | `suelo_a_construido` | NDVI < 0.25 en las dos fechas y (ΔBSI ≤ −0.10 con \|Δbrillo\| ≥ 0.04, o brillo +0.08 terminando con BSI ≤ 0) |
   | `reverdecimiento` | ΔNDVI ≥ +0.20 — se reporta aparte y **no cuenta como obra** |

7. **Área mínima**: manchas 4-conexas de 50 píxeles (**0.5 ha**). Una nave
   chica ronda 1 ha; menos de 0.5 ha a 10 m es borde o co-registro.
8. **Salida**: JSON con fechas, IDs y enlaces de las dos escenas, nubosidad del
   recorte y de la escena, hectáreas totales, **hectáreas de posible obra**
   (todo menos reverdecimiento), hectáreas por tipo, zonas con centroide
   lat/lon, todos los umbrales y avisos; y un PNG antes / después / mapa de
   cambio (naranja veg→suelo, rojo veg→construido, magenta suelo→construido,
   verde reverdecimiento, gris nube).

**Regla que no se rompe**: con una ventana sin escena o con el recorte más
nublado que **20 %** en cualquiera de las dos fechas, el resultado es
`"estado": "no_concluye"` y las hectáreas son `null` — nunca 0, porque 0
afirmaría que se miró y no hubo cambio. Hay hectáreas solo si las dos escenas
se citan con ID y fecha (`resultado.assert_citado`).

Los umbrales son heurísticos de la literatura (0.20 de ΔNDVI es el habitual
para desmonte a 10 m), escritos antes de las corridas, **salvo** dos que se
agregaron en la v0.2 *después* de mirar las obras (`vegetacion_a_construido` y
el aclarado de losa a techo, `DELTA_BRILLO_TECHO`). Ninguno está calibrado
contra obras verificadas.

## 2. Resultados en vivo (2026-10-13)

Radio 1.5 km (707 ha por sitio). **Estación seca contra estación seca**: antes
2024-01-01:2024-04-30, después 2026-01-01:2026-04-30 (`docs/satelite/seca-2024-2026/`,
un JSON y un PNG por sitio, más `resumen.json`).

| Sitio | Antes | Después | Nubes recorte | ha cambio | ha posible obra | veg→suelo | →construido | reverdec. |
|---|---|---|---|---|---|---|---|---|
| apodaca-industrial | S2A_14RLP_20240324_0_L2A | S2A_14RLP_20260326_0_L2A | 0 % / 0 % | 37.87 | 25.17 | 24.61 | 0.56 | 12.70 |
| pesqueria-kia | S2B_14RLP_20240129_0_L2A | S2B_14RLP_20260128_0_L2A | 0 % / 0 % | 296.95 | 29.91 | 29.91 | 0 | 267.04 |
| salinas-hofusan | S2A_14RLP_20240324_0_L2A | S2A_14RLP_20260326_0_L2A | 0 % / 0 % | 43.60 | 41.55 | 38.43 | 3.12 | 2.05 |
| garcia-poniente | S2A_14RLP_20240324_0_L2A | S2A_14RLP_20260326_0_L2A | 0 % / 0 % | 44.81 | 44.14 | 44.14 | 0 | 0.67 |
| ramos-arizpe | S2A_14RLP_20240324_0_L2A | S2A_14RLP_20260326_0_L2A | 0 % / 0 % | 44.06 | 41.28 | 40.74 | 0.54 | 2.78 |
| puerto-interior | S2A_13QHD_20240403_0_L2A | S2C_13QHD_20260403_0_L2A | 0 % / 0 % | 101.99 | 11.87 | 11.87 | 0 | 90.12 |
| el-marques | S2A_14QLH_20240324_0_L2A | S2A_14QLH_20260326_1_L2A | 0 % / 0 % | 365.48 | 43.21 | 43.21 | 0 | 322.27 |
| celaya | S2B_14QKH_20240228_0_L2A | S2B_14QKH_20260227_0_L2A | 0 % / 0 % | 64.06 | 21.86 | 21.86 | 0 | 42.20 |
| slp-industrial | S2A_14QKK_20240304_0_L2A | S2C_14QKK_20260304_0_L2A | 0 % / 0 % | 2.89 | 0 | 0 | 0 | 2.89 |
| leon-sur | S2A_13QHD_20240403_0_L2A | S2C_13QHD_20260403_0_L2A | 0 % / 0 % | 25.38 | 8.77 | 8.77 | 0 | 16.61 |
| **obra BMW SLP** | S2A_14QLK_20240423_0_L2A | S2C_14QLK_20260423_0_L2A | 0 % / 0 % | 67.05 | 45.03 | 24.17 | **20.86** | 22.02 |
| **obra LEGO Ciénega** | S2A_14RLP_20240324_0_L2A | S2A_14RLP_20260326_0_L2A | 0 % / 0 % | 37.82 | 32.26 | 30.77 | 1.49 | 5.56 |

"→construido" suma `vegetacion_a_construido` y `suelo_a_construido`
(`vegetacion_a_construido` solo apareció en Ramos Arizpe, 0.54 ha; el resto es
`suelo_a_construido`). Ningún sitio quedó en
"no concluye": en la estación seca los 12 recortes salieron con 0 % de nubes.
El emparejamiento por día del año funcionó: los 12 pares están a ≤ 2 días del
año de distancia (ver tabla).

### 2.1 Las dos obras con fecha pública

**BMW San Luis Potosí — centro de producción de módulos de baterías.** Obra
arrancada el **2024-05-03**, **81,876 m²** (8.19 ha), en el complejo de BMW en
Villa de Reyes ([Mexico Industry, 2024-05-03](https://mexicoindustry.com/noticia/arranca-bmw-construccion-del-centro-de-produccion-de-modulos-de-baterias-en-slp);
[Cluster Industrial, fecha anunciada](https://clusterindustrial.com.mx/bmw-anuncia-la-fecha-para-el-inicio-de-construccion-del-centro-de-produccion-de-baterias-en-slp/);
[BMWBlog, 2024-03-27](https://www.bmwblog.com/2024/03/27/bmw-to-break-ground-for-battery-production-center-in-san-luis-potosi)).
Punto: OSM/Nominatim "BMW Planta San Luis Potosi" (21.96826, −100.84917).

- Escena antes: 2024-04-23, **diez días antes** de la primera piedra.
- Detectado: una zona `suelo_a_construido` de **9.89 ha** con centroide en
  (21.96754, −100.84303), a ~600 m al oriente del punto. Nominatim
  (reverse, zoom 18) la ubica **dentro del polígono "BMW Planta San Luis
  Potosi"** de OpenStreetMap. En el PNG se ve como techo claro nuevo sobre lo
  que en abril de 2024 era terreno.
- Con línea base 2022-04-04 (`docs/satelite/obras-2022-2026/`) la misma zona
  sale con **10.89 ha**.
- **Lectura**: coincide en tiempo (aparece después de la primera piedra) y en
  orden de magnitud (9.9 ha detectadas contra 8.2 ha de nave; la diferencia es
  razonable si incluye patios y pavimento). **No está verificado** que esa
  zona sea el edificio de baterías y no otro dentro del complejo: no se
  encontró plano público con la ubicación del edificio.

**LEGO Ciénega de Flores — nave de 59,000 m².** Inversión de USD 205 M para
una nave de 59,000 m², "lista en mayo de 2025"
([Tus Buenas Noticias, 2023-11-14](https://www.tusbuenasnoticias.com/amp/noticias/buenas-noticias/2023/11/14/25854-asi-lucira-la-planta-mas-grande-del-mundo-de-lego-y-estara-en-nuevo-leon)).
La nota **no da fecha de inicio de obra**. Punto: OSM/Nominatim "LEGO
Operaciones de México" (25.89245, −100.23967).

- 2024-03 → 2026-03: solo 1.49 ha `suelo_a_construido`. 2022-03 → 2026-03:
  12.31 ha `suelo_a_construido` en varias zonas (la mayor, 4.06 ha en
  25.8808, −100.2440), más 137 ha de reverdecimiento (marzo de 2022 fue de
  sequía severa en Monterrey; el verde de 2026 no es obra).
- **Lectura**: **no se puede confirmar ni descartar**. Sin la fecha de inicio
  ni el polígono de la nave no se sabe si en marzo de 2024 ya estaba techada
  (en ese caso no hay nada que detectar en 2024→2026), ni cuál de las zonas
  2022→2026 es la nave de LEGO y cuáles son naves vecinas del parque Nexxus.

**Tercera obra buscada y no usada**: Volvo/Mack en Ciénega de Flores, primera
piedra el **2024-10-15**, predio de 127 ha
([Publimetro, 2024-10-15](https://www.publimetro.com.mx/nuevo-leon/2024/10/15/samuel-garcia-coloca-la-primera-piedra-de-volvo-en-cienega-de-flores/)).
No se corrió: ni Nominatim ni las notas dan su ubicación, y una coordenada
adivinada sería un dato inventado. Es el siguiente caso a medir en cuanto se
tenga el punto.

### 2.2 Las ventanas del ejemplo del CLI (estaciones distintas)

Con antes 2024-01-01:2024-03-31 y después 2026-07-01:2026-09-30 (seca contra
lluvias) cada resultado carga el aviso de estación distinta. Cifras completas en
`docs/satelite/estaciones-distintas-resumen.json` (los PNG no se versionan).
Los 12 recortes también salieron con 0 % de nubes: en una ventana de tres meses
siempre hubo al menos una escena limpia.

| Sitio | Fechas | ha cambio | reverdecimiento | suelo→construido |
|---|---|---|---|---|
| El Marqués | 2024-03-29 → 2026-07-22 | 597.64 | 588.37 | 0 |
| Pesquería | 2024-01-09 → 2026-09-15 | 465.68 | 436.60 | 0 |
| Puerto Interior | 2024-01-04 → 2026-09-22 | 345.22 | 345.22 | 0 |
| Celaya | 2024-03-29 → 2026-07-22 | 326.58 | 326.58 | 0 |
| obra BMW SLP | 2024-01-09 → 2026-09-20 | 94.29 | 51.55 | **13.69** |
| obra LEGO | 2024-03-29 → 2026-07-22 | 39.90 | 4.80 | 3.31 |

Entre seca y lluvias el "cambio" es sobre todo cultivo y matorral que
reverdecen (hasta 588 de 707 ha): la cifra total deja de decir algo sobre
obra. `suelo_a_construido` sigue siendo estable: en BMW vuelve a salir (13.7
ha) y en los 10 sitios de `seed.py` da entre 0 y 2.2 ha. **Por eso el uso
recomendado es misma estación contra misma estación**.

### 2.3 Qué dice esto (y qué no)

- **n = 2 obras con fecha, 1 detectada con ubicación plausible, 1 no
  concluyente. n < 30 no concluye precisión** ni a favor ni en contra.
- `suelo_a_construido` es la señal más específica: en los 10 sitios dio entre 0
  y 3.1 ha, y en BMW, 20.9 ha. Las zonas grandes de `vegetacion_a_suelo` (García
  44 ha, El Marqués 43 ha, Salinas 38 ha) caen sobre todo en cauces, matorral
  y parcelas (ver PNG): son **desmonte, sequía o cosecha**, no
  necesariamente obra. Contarlas como "naves nuevas" inflaría el radar.
- El reverdecimiento grande (El Marqués 322 ha, Pesquería 267 ha) es riego o
  cultivo y se reporta aparte para no esconderlo.

## 3. Límites

- **10 m por píxel.** Una nave de 1 ha son 100 píxeles; una ampliación de
  0.3 ha no pasa el área mínima. Se ve "hay techo / no hay techo" y terracería;
  **no** se distinguen etapas de estructura (columnas, armaduras) ni avance
  porcentual. Para el producto de avance de obra (§2 de
  `13-comparables-precio.md`) eso deja la venta como "la obra se movió o no",
  no "va al 60 %".
- **Nubes.** En las 26 corridas en vivo (12 + 12 + 2) ninguna quedó en "no
  concluye": con ventanas de 3–4 meses siempre hubo un recorte limpio, aun en
  lluvias. Con ventanas cortas (un mes, para reporte mensual) no será así: una
  sola escena del Bajío sale con 78–81 % de nubes (`MEMORY/FUENTES.md`, Silao,
  2026-10-10). El camino "no concluye" está probado **solo con tests
  sintéticos**, no en vivo. El SCL tampoco es perfecto: nubes finas o sombras
  mal clasificadas pueden pasar como cambio.
- **Revisita ~5 días** (S2A, S2B y S2C): con nubes, la cadencia real en
  lluvias puede ser de semanas. Un reporte mensual es realista; uno semanal, no.
- **Estación y sequía.** Comparar estaciones distintas o un año seco contra uno
  húmedo produce cientos de hectáreas de cambio de vegetación que no es obra.
  Mitigación actual: ventanas en los mismos meses y emparejar por día del año.
- **Sin normalización radiométrica ni co-registro fino** entre fechas; el
  desfase de Sentinel-2 es típicamente subpíxel, pero los bordes de naves
  pueden dar franjas de 1 píxel (el área mínima las quita casi todas).
- **El tipo es aproximado**: techo y pavimento no se separan; techos oscuros o
  verdes no aclaran y pueden no salir como construido.
- **Ubicación del punto**: el radio cubre el entorno, no el predio; sin
  polígono del cliente, una zona de cambio puede ser del vecino.

## 4. Qué costaría más resolución

Precios de `docs/13-comparables-precio.md` §2.1 (consulta 2026-10-13), no
re-verificados aquí:

- **Imagen de 50 cm bajo pedido** (SkySat vía SkyWatch): **USD 10–12 por km²**
  de archivo, **mínimo 25 km²** por pedido (≈ USD 250–300 por toma). Una obra
  con su entorno cabe sobradamente en 25 km²; un corredor completo no: el disco
  de 1.5 km de este prototipo son 7 km².
- Para el **radar de naves** (§3) no hace falta 50 cm: Sentinel-2 sirve como
  disparador gratuito y la imagen fina se compra solo donde salió
  `suelo_a_construido`.
- Para **avance de obra** (§2) con etapas, 50 cm o dron (DroneDeploy
  USD 4,188/año por licencia, el vuelo lo pone el cliente).

## 5. Qué sigue para pasar de prototipo a producto

1. Medir contra la lista de 55 naves en construcción de Colliers en Monterrey
   (2T 2026, `08-mercado.md` §2.1) con sus polígonos: ahí n ≥ 30 y se puede
   hablar de precisión (criterio de §3.2: ≥ 80 % detectadas).
2. Ubicar la obra de Volvo en Ciénega de Flores con fuente y correrla.
3. Polígono del predio como entrada (en vez de punto y radio) para que el
   cambio del vecino no cuente.
