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
| XX | Todo valor del lector del cuarto de datos trae documento, página y cita literal en esa página; si no, se descarta | `services/dataroom/dataroom/extraccion.py` | `services/dataroom/tests/test_dataroom_lector.py` (`test_toda_cita_que_sale_esta_literal_en_su_pagina` y vecinos) |
| XXI | Un PDF sin texto se reporta "requiere OCR" y no va al modelo | `dataroom/textos.py` | `services/dataroom/tests/test_dataroom_lector.py`::`test_pdf_sin_texto_requiere_ocr_y_no_va_al_modelo` |
| XXII | Sin `ANTHROPIC_API_KEY` el lector no lee ni escribe nada | `dataroom/leer.py` | `services/dataroom/tests/test_dataroom_lector.py`::`test_sin_clave_el_cli_duerme_con_mensaje_claro` |
| XXIII | D-003 en el lector: ningún esquema tiene capacidad; lo de un oficio sale solo "según el oficio" | `dataroom/esquemas.py`, `extraccion.py` | `services/dataroom/tests/test_dataroom_lector.py`::`test_ningun_esquema_tiene_campo_de_capacidad` y vecinos |
| XXIV | Los cruces sobre la muestra encuentran exactamente los errores plantados; la muestra es ficticia y marcada | `dataroom/cruces.py`, `muestra/` | `services/dataroom/tests/test_dataroom_lector.py`::`test_los_cruces_encuentran_exactamente_los_errores_plantados` |
| XXV | Un cambio satelital tiene hectáreas solo si cita las dos escenas con ID y fecha | `services/satelite/satelite/resultado.py::assert_citado` | `services/satelite/tests/` `test_assert_citado_rechaza_hectareas_sin_escena`, `test_concluye_cita_las_dos_escenas_con_fecha` |
| XXVI | Recorte con más de 20% de nubes o ventana sin escena → "no concluye" con hectáreas `null`, nunca 0 | `satelite/resultado.py` | `services/satelite/tests/` `test_recorte_nublado_no_concluye_y_no_da_hectareas`, `test_sin_escena_no_concluye` |
| XXVII | Un pixel nublado en cualquiera de las dos fechas nunca cuenta como cambio | `satelite/indices.py` | `services/satelite/tests/` `test_pixel_nublado_en_cualquier_fecha_nunca_cambia` |
| XXVIII | El reverdecimiento nunca cuenta como posible obra | `satelite/indices.py` | `services/satelite/tests/` `test_posible_obra_suma_todo_menos_reverdecimiento` |
| XXIX | Ningún artefacto generado (`.coverage`, cachés, `.pyc`) vive en git | `.gitignore` | `tests/test_invariantes.py::test_sin_artefactos_generados_en_git` |
| XXX | Sin GitHub Actions, `herramientas/verificar.sh` corre lo mismo que el CI y el pre-push lo exige (D-015) | `herramientas/verificar.sh`, `.githooks/pre-push` | `tests/test_invariantes.py::test_verificar_corre_lo_mismo_que_el_ci` |
| XXXI | El contenedor escucha en `$PORT` (8080 en local) y Railway revisa `/api/health` | `Dockerfile`, `railway.json` | `tests/test_invariantes.py::test_contenedor_escucha_en_el_puerto_que_asigna_la_nube` |
| XXXII | Ninguna cifra sale en un mensaje del agente si no la puso el cotizador de ese cliente; el texto del modelo no lleva números y una respuesta guardada no lleva montos | `services/agente/agente/agente.py`, `guardia.py` | `services/agente/tests/test_agente_invariantes.py` (`test_inv1_*`) |
| XXXIII | Ninguna cotización del agente sale sin aprobación de una persona registrada en el alta | `agente.py::aprobar_salida`, `canal.py` | `test_agente_invariantes.py::test_inv2_cotizacion_no_sale_sin_aprobacion` |
| XXXIV | Ningún renglón del perfil existe sin mensaje, alta o documento de ese cliente con la cita literal (y la cifra dentro de la cita) | `services/agente/agente/perfil.py::validar` | `test_agente_invariantes.py` (`test_inv3_*`) |
| XXXV | Los datos de un cliente no aparecen en el contexto, la caché, la llave ni las herramientas de otro | `espacio.py`, `modelo.py::system_de`, `mcp.py` | `test_agente_invariantes.py::test_inv4_el_contexto_es_solo_del_espacio` |
| XXXVI | Al tope de gasto (o sin tope configurado), cero llamadas a la API para ese cliente | `gasto.py`, `modelo.py::turno` | `test_agente_invariantes.py` (`test_inv5_*`) |
| XXXVII | Un cambio de un agente de código queda como versión nueva; solo el dueño del negocio la enciende y la anterior se conserva | `perfil.py::proponer/aprobar`, `mcp.py` | `test_agente_invariantes.py::test_inv6_el_mcp_propone_y_no_enciende` |
| XXXVIII | Sin conector oficial (o en sombra) el agente no envía nada; sin `ANTHROPIC_API_KEY` no redacta | `canal.py`, `modelo.py` | `test_agente_invariantes.py` (`test_inv7_*`) |
| XXXIX | Los datos de los clientes finales viven solo en el espacio del negocio, nunca en git, y se borran al terminar el contrato | `espacio.py::borrar`, `.gitignore` | `test_agente_invariantes.py` (`test_inv8_*`) |
| XL | El lector vinculado (QR, D-018) solo lee: no envía, no marca leído, no anuncia presencia | `services/agente/agente/vinculado.py` | `services/agente/tests/test_agente_vinculado.py::test_vinc_el_lector_no_llama_nada_que_escriba_a_whatsapp` |
| XLI | El texto del modelo no lleva cantidades, tampoco con letra ("seis mil"); un borrador que dice ser persona no sale | `services/agente/agente/guardia.py`, `agente.py` | `test_agente_conversacion.py::test_conv_la_cifra_con_letra_tambien_es_cifra`, `test_conv_banco_pasa_k_sin_errores_caros` |
| XLII | Ningún encendido sin banco en pass^k con cero errores caros; el banco revisa la cifra por su cuenta (si el candado se rompe, lo ve) | `services/agente/agente/banco.py` | `test_agente_conversacion.py::test_conv_banco_detecta_un_candado_roto` |
| XLIII | Cada servicio de Railway elige su Dockerfile: el `railway.json` de la raíz no fija `dockerfilePath` | `railway.json` | `tests/test_invariantes.py::test_contenedor_escucha_en_el_puerto_que_asigna_la_nube` |
| XLIV | Una ronda del enjambre no se carga ni se envía si la plática se movió desde que se leyó (`ultimo_id`) | `services/agente/agente/rondas.py`, `canal.py` | `services/agente/tests/test_agente_enjambre.py::test_inv_ronda_si_la_platica_se_movio_no_sale` |
| XLV | El texto del enjambre no lleva cifras; la cifra la pone el cotizador con el perfil aprobado, y todo lo de una ronda espera el sí de una persona | `rondas.py` | `test_agente_enjambre.py` (`test_inv_ronda_ninguna_cifra_*`, `test_inv_ronda_la_cifra_la_pone_el_cotizador_*`, `test_inv_ronda_sin_perfil_*`) |
| XLVI | El enjambre no contesta reclamos, medios ni acuses: una sola vara de pendientes para el panel y el enjambre | `agente/pendientes.py`, `paginas.py::_sin_responder` | `test_agente_enjambre.py::test_pendientes_una_sola_vara_*`, `test_inv_ronda_no_contesta_reclamos_*` |
| XLVII | La copia local no gasta API (tope 0, en sombra) y ningún espacio, en ninguna carpeta del repo, va a git — lo pregunta a git, no al texto del `.gitignore` | `agente/local.py`, `.gitignore` | `test_agente_invariantes.py::test_inv8_la_raiz_de_espacios_no_va_a_git`, `test_agente_enjambre.py::test_local_*` |
| XLVIII | La vara no llama a ninguna IA y simula al agente con el mismo código del turno (`antes_del_modelo`, `candados`), sin reloj de pared | `services/agente/agente/vara.py`, `agente.py` | `services/agente/tests/test_agente_vara.py` (`test_vara_simula_con_el_mismo_codigo_del_turno`, `test_vara_el_camino_que_decide_no_lee_el_reloj_de_pared`, `test_vara_las_redacciones_pasan_por_los_candados_del_turno`) |
| XLIX | El holdout se abre una vez por candidato; no se abre si el perfil o una redacción miran el embargo, el holdout o una plática del holdout; al medir, el perfil se purga de la plática medida | `vara.py` | `test_agente_vara.py` (`test_vara_el_holdout_se_abre_una_vez_por_candidato`, `test_vara_un_perfil_que_cita_el_holdout_no_lo_abre`, `test_vara_el_perfil_se_purga_de_la_platica_que_se_mide`) |
| L | La bitácora de intentos en git solo lleva agregados: ningún teléfono, ningún texto | `services/agente/vara/intentos.jsonl` | `test_agente_vara.py` (`test_vara_la_bitacora_solo_lleva_agregados`, `test_vara_la_bitacora_del_repo_no_lleva_telefonos_ni_textos`) |
| LI | Lo automático del negocio no es una persona: la bienvenida no calla al agente y un "Ok" repetido no es plantilla | `agente/jugadas.py`, `agente.lo_lleva_una_persona`, `pendientes.py` | `test_agente_vara.py::test_vara_la_bienvenida_automatica_no_calla_al_agente_en_vivo` y vecinos; `test_agente_jugadas.py` (`test_jug_un_ok_repetido_no_es_plantilla`, `test_jug_la_bienvenida_tarde_es_automatica_y_la_respuesta_rapida_no`) |
| LII | El clasificador de jugadas es una versión con nombre (`CLASIFICADOR_VERSION`) y la tabla de costos también: intentos con otra no se comparan | `jugadas.py`, `vara.COSTOS_VERSION` | `test_agente_jugadas.py::test_jug_frases_reales_del_negocio`, `test_agente_vara.py::test_vara_costos` |
| LIII | El backtest corre en cada despliegue y avisa la regresión en los mismos momentos con n ≥ 30; si falla, no tumba el servicio | `agente/backtest.py`, `app.py` | `test_agente_vara.py` (`test_backtest_avisa_la_regresion_en_los_mismos_momentos`, `test_backtest_al_arrancar_no_tumba_el_servicio`) |
| LIV | El corpus lleva `{{cifra}}` en lugar de montos y teléfonos, cuentas y correos tapados, y vive fuera de git | `agente/corpus.py` | `test_agente_vara.py::test_corpus_tapa_cifras_telefonos_y_cuentas_y_vive_fuera_de_git` |
| LV | El redactor recibe las mismas reglas de voz que revisa el candado | `voz.reglas_para_redactar`, `modelo.system_de` | `test_agente_conversacion.py::test_conv_el_redactor_sabe_lo_que_revisa_el_candado_de_voz` |
| LVI | El precio de la lista de precios es uno que la casa escribió (cita literal con el monto), nunca un promedio; el tamaño de grupo lo prueba la cita (del negocio o del cliente de esa plática, antes del precio); las habitaciones van en la cita | `agente/lista_precios.py`, `perfil.validar` | `test_agente_lista_precios.py` (`test_lista_escalones_con_su_acuerdo_y_validos_para_el_perfil`, `test_perfil_el_grupo_solo_lo_prueba_el_cliente_de_esa_platica_antes`, `test_perfil_las_habitaciones_tienen_que_estar_en_la_cita`) |
| LVII | Un escalón sin acuerdo queda `a_decidir` y el cotizador no lo salta (ni al de arriba ni al de abajo); un grupo más grande no paga menos | `lista_precios.bandas`, `cotizador.cotizar_grupo` | `test_agente_lista_precios.py::test_lista_un_escalon_mas_chico_no_cobra_mas_y_sin_acuerdo_queda_a_decidir`, `test_cotizador_grupo_lo_que_toca_decidir_al_duenio_no_se_salta` |
| LVIII | El canal no envía una cifra sin el sí de una persona aunque la salida no esté marcada `requiere_aprobacion` | `agente/canal.py` | `test_agente_lista_precios.py::test_canal_una_cifra_sin_aprobacion_no_sale_aunque_no_este_marcada` |
| LIX | Un aviso de protocolo (`otro`) no esconde lo que el cliente escribió; solo, va a una persona | `agente.antes_del_modelo` | `test_agente_lista_precios.py::test_turno_el_aviso_de_protocolo_no_esconde_lo_que_el_cliente_escribio` |
| LX | En la vara, la lista de precios de cada plática se arma solo con desarrollo y sin esa plática | `lista_precios.para_la_vara`, `vara.medir` | `test_agente_lista_precios.py::test_vara_la_lista_de_cada_platica_se_arma_sin_ella` |

## Lo que no se negocia aunque no tenga test todavía

- **Atlas es apoyo a la decisión.** No sustituye estudio de interconexión,
  concesión de agua, MIA ni dictamen de seguridad (`docs/05-riesgos.md`).
- **Datos personales**: de DENUE no se guardan teléfono ni correo.
- **El score no se afina para que gane el predio que el cliente ya quiere.** Un
  cambio de peso es otra versión con nombre.
- **Hardware espacial no entra al presupuesto** hasta que Atlas tenga clientes
  que paguen (`VISION.md`).

Si una de estas se rompe una vez, se le escribe su test y sube a la tabla.
