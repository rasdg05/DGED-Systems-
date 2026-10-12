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
| VIII | Ninguna clave en el repo (`INEGI_TOKEN`, `SAKBE_TOKEN` vacías en `.env.example`) | `.env.example` | `tests/test_invariantes.py::test_env_example_sin_claves` |
| IX | Al medir una fuente, un HTTP 200 sin dato es MUERTA y una conexión sin respuesta es NO CONCLUYE, nunca MUERTA (`MEMORY/FUENTES.md`) | `herramientas/medir_fuentes.py` | `tests/test_medir_fuentes.py` |

## Lo que no se negocia aunque no tenga test todavía

- **Atlas es apoyo a la decisión.** No sustituye estudio de interconexión,
  concesión de agua, MIA ni dictamen de seguridad (`docs/05-riesgos.md`).
- **Datos personales**: de DENUE no se guardan teléfono ni correo.
- **El score no se afina para que gane el predio que el cliente ya quiere.** Un
  cambio de peso es otra versión con nombre.
- **Hardware espacial no entra al presupuesto** hasta que Atlas tenga clientes
  que paguen (`VISION.md`).

Si una de estas se rompe una vez, se le escribe su test y sube a la tabla.
