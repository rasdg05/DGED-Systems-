# Constitución de DGED — invariantes

> Cada invariante dice **dónde** vive y **qué test** la hace cumplir. Una
> invariante sin test es una intención.

| # | Invariante | Dónde vive | Test que la cuida |
|---|---|---|---|
| I | El número solo existe si sequía, inundación y uso de suelo respondieron (`publishable`) | `services/api/atlas/score.py` | `services/api/test_score.py::test_missing_land_is_not_publishable` |
| II | La ventana DENUE se muestra y no puntúa | `score.py` | `test_score.py::test_window_sample_does_not_change_the_number` |
| III | La ruta SAKBÉ entra solo si devolvió minutos | `score.py` | `test_score.py::test_route_minutes_enter_only_when_present` |
| IV | El producto no afirma megawatts ni capacidad eléctrica en el predio (D-003) | UI, ontología | `tests/test_invariantes.py::test_no_se_afirman_megawatts` |
| V | `SubestacionAprox` existe en la ontología y viaja sin capacidad | `ontology/atlas.ontology.json` | `tests/test_invariantes.py::test_subestacion_sin_capacidad` |
| VI | MapLibre vendido es exactamente 5.6.1 | `services/api/static/maplibre-gl.js` | `tests/test_invariantes.py::test_maplibre_es_5_6_1` |
| VII | Ningún test tapa a otro con el mismo nombre | `tests/`, `services/api/` | `tests/test_invariantes.py::test_ningun_test_tapa_a_otro` |
| VIII | Ninguna clave en el repo (todas vacías en `.env.example`) | `.env.example` | `tests/test_invariantes.py::test_env_example_sin_claves` |
| IX | Toda variable de `.env.example` llega al contenedor | `docker-compose.yml` | `tests/test_invariantes.py::test_compose_pasa_cada_variable_del_env_example` |
| X | Postgres no se publica fuera de la máquina | `docker-compose.yml` | `tests/test_invariantes.py::test_postgres_no_se_publica_a_toda_la_red` |
| XI | Sin `ATLAS_ACCESS_TOKEN` no hay Oráculo; con él, `X-Atlas-Key` obligatoria | `services/api/atlas/access.py` | `services/api/test_access.py` |
| XII | Las rutas que gastan (calificar, Oráculo) tienen tope por IP | `access.guard_score`, `access.guard_oracle` | `test_access.py::test_las_rutas_que_gastan_tienen_su_guardia` |
| XIII | Toda cifra del Oráculo sale de un resultado de herramienta | `services/api/atlas/oracle.py` | `services/api/test_oracle.py` |
| XIV | Una capa sin respuesta (USGS, Overpass) no mueve el número: los pesos son los de 0.1.0 | `services/api/atlas/score.py` | `services/api/test_capas.py::test_unanswered_layers_do_not_move_the_number` |
| XV | Los pesos suman 1 en las 16 combinaciones de capas opcionales | `score.py::_weights` | `test_capas.py::test_weights_sum_to_one_in_every_combination` |
| XVI | `SubestacionAprox` llenada desde OSM no lleva capacidad, MW ni "disponible", ni en llaves ni en texto | `services/api/atlas/main.py::materialize` | `test_capas.py::test_substation_never_claims_capacity` (y V, que ahora también prohíbe `disponible`/`available`) |
| XVII | Una página de error del SMN no se guarda como libro ni tumba el arranque | `connectors/conagua.py` | `test_capas.py::test_smn_html_error_page_is_not_a_workbook` |
| XVIII | Ninguna marca de conflicto de git llega a un commit | todo el repo | `tests/test_invariantes.py::test_sin_marcas_de_conflicto` |
| XIX | Al medir una fuente, un HTTP 200 sin dato es MUERTA y una conexión sin respuesta es NO CONCLUYE, nunca MUERTA (`MEMORY/FUENTES.md`) | `herramientas/medir_fuentes.py` | `tests/test_medir_fuentes.py` |

## Lo que no se negocia aunque no tenga test todavía

- **Atlas es apoyo a la decisión.** No sustituye estudio de interconexión,
  concesión de agua, MIA ni dictamen de seguridad (`docs/05-riesgos.md`).
- **Datos personales**: de DENUE no se guardan teléfono ni correo.
- **El score no se afina para que gane el predio que el cliente ya quiere.** Un
  cambio de peso es otra versión con nombre.
- **Hardware espacial no entra al presupuesto** hasta que Atlas tenga clientes
  que paguen (`VISION.md`).

Si una de estas se rompe una vez, se le escribe su test y sube a la tabla.
