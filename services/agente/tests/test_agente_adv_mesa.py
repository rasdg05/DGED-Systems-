# ruff: noqa: F811  (con_mesa es fixture importada de test_agente_ordenes)
"""Revisión adversarial de la mesa (2026-10-31): cada hallazgo entra aquí ANTES del arreglo.

Un agente buscó cómo la mesa nueva le llega a un cliente lo que no debe, le da a una
administradora lo que es de quien aprueba o deshace de más. 15 hallazgos
estos
son los que tienen prueba. Las frases de la plática normal que se leían como
orden que cambia algo están en `test_adv_mesa_platica_no_cambia_nada`."""
from __future__ import annotations

import pytest
from agente import agente, capacidades, enviador, mesa, ordenes, perfil, rondas, vinculado
from tests.test_agente_enjambre import HILO, _ronda
from tests.test_agente_ordenes import DUENA, OTRA, _orden, con_mesa  # noqa: F401


def _dictadas(e):
    return [s for s in agente.salidas(e) if s.via == "mesa"]

def test_adv_mesa_mandale_la_ubicacion_sale_literal(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    _orden(con_mesa, "mándale al 7777 la ubicación")
    s = _dictadas(con_mesa)
    assert not s or s[-1].id not in enviador.pendientes(con_mesa), s[-1].texto

def test_adv_mesa_dile_que_suelto(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    _orden(con_mesa, "Dile a 7777 que...")
    assert not _dictadas(con_mesa)

def test_adv_mesa_manda_todo_aprueba_a_ciegas(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    rondas.cargar(con_mesa, _ronda())
    _orden(con_mesa, "manda todo")  # nunca pidió "borradores"
    assert not agente.aprobadas(con_mesa)

def test_adv_mesa_eso_no_dias_despues_reenciende(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    _orden(con_mesa, "pausa")
    _orden(con_mesa, f"nota {HILO[-4:]} paga el viernes")
    _orden(con_mesa, "deshaz")  # borra la nota
    _orden(con_mesa, "eso no")  # plática; o un segundo "deshaz"
    assert con_mesa.config()["encendido"] == "sombra"

def test_adv_mesa_deshaz_pausa_pisa_una_pausa_posterior_del_panel(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    _orden(con_mesa, "pausa")
    c = con_mesa.config()
    c["encendido"] = "sin_cifra"
    con_mesa.escribir_json("config.json", c)  # panel enciende
    c = con_mesa.config()
    c["encendido"] = "sombra"
    con_mesa.escribir_json("config.json", c)     # panel pausa
    _orden(con_mesa, "deshaz")
    assert con_mesa.config()["encendido"] == "sombra"

def test_adv_mesa_mcp_de_solo_lectura_cambia_a_quien_va_dile_1(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    _orden(con_mesa, f"ficha {HILO[-4:]}")                    # su lista: 1 = …7777
    mesa.por_fuera(con_mesa, "busca boda", solo_lectura=True, via="mcp")  # una sesión mira, "sin tocar"
    _orden(con_mesa, "dile 1 que ya quedó apartado")
    _orden(con_mesa, "sí, mándalo")
    assert _dictadas(con_mesa)[-1].hilo == HILO, _dictadas(con_mesa)[-1].hilo

def test_adv_mesa_lista_vieja_sin_caducidad(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    _orden(con_mesa, "busca boda")
    listas = con_mesa.leer_json(capacidades.LISTAS, {})
    listas["0000000000"]["clientes"]["en"] = "2026-01-01T00:00:00+00:00"
    con_mesa.escribir_json(capacidades.LISTAS, listas)
    r = _orden(con_mesa, "dile 1 que ya quedó")
    assert "Le mando" not in r and "Va en la cola" not in (_orden(con_mesa, "sí, mándalo") or "")

def test_adv_mesa_confirmo_2_asienta_renta(con_mesa):
    _orden(con_mesa, "pendientes")
    _orden(con_mesa, "Confirmo 2")
    assert not con_mesa.leer_lineas(capacidades.RESERVAS)

def test_adv_mesa_nota_de_otra_llega_al_enjambre_como_de_la_duena(con_mesa, monkeypatch):
    from agente import local
    monkeypatch.setattr(local, "_espacio", lambda cid: con_mesa)
    _orden(con_mesa, f"nota {HILO[-4:]} dale 30% de descuento", de=OTRA)
    _, rutas = local.lotes(con_mesa.cliente_id)
    todo = "".join(p.read_text() for p in rutas)
    assert "30% de descuento" not in todo

def test_adv_mesa_otra_deshaz_reactiva_reportes_de_la_duena(con_mesa):
    _orden(con_mesa, "silencia los reportes", de=OTRA)
    _orden(con_mesa, "silencia los reportes")
    _orden(con_mesa, "deshaz", de=OTRA)
    assert "0000000000" in con_mesa.config()["reportes_silenciados"]

def test_adv_mesa_dos_clientes_en_un_dictado(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    assert "otro cliente" in _orden(con_mesa, "Dile a 7777 que sí hay lugar, y a la 4321 que no hacemos bodas")
    _orden(con_mesa, "sí, mándalo")
    assert not _dictadas(con_mesa)

def test_adv_mesa_deshaz_perfil_pisa_version_posterior(con_mesa):
    n, _ = perfil.proponer(con_mesa, perfil.activo(con_mesa), autor="p", nombre="v2")
    _orden(con_mesa, "aprueba la versión")
    n3, _ = perfil.proponer(con_mesa, perfil.activo(con_mesa), autor="p", nombre="v3")
    perfil.aprobar(con_mesa, n3, aprobador="Dueña de muestra")  # panel
    _orden(con_mesa, "deshaz")
    assert perfil.version_activa(con_mesa) == n3, perfil.version_activa(con_mesa)



def test_adv_mesa_ex_aprobadora_deshace_una_orden_de_aprobadora(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    assert "no le llega" in _orden(con_mesa, f"no le escribas a {HILO[-4:]}")
    # el alta cambia de aprobadora; la dueña anterior queda como administradora
    alta = con_mesa.leer_json("alta.json", {})
    alta["aprobador_telefono"] = OTRA
    con_mesa.escribir_json("alta.json", alta)
    c = con_mesa.config()
    c["administradores"] = ["0000000000"]
    con_mesa.escribir_json("config.json", c)
    assert not mesa.es_quien_aprueba(con_mesa, DUENA)
    _orden(con_mesa, "eso no", de=DUENA)
    assert capacidades.no_escribir(con_mesa, HILO)


@pytest.mark.parametrize("texto", [
    "mándale al 7777 la ubicación", "contestale a 7777 cuando puedas", "escribele al 2 mañana",
    "dile a 7777 lo que te dije", "Respondele a 2 lo de la alberca", "regresa 2", "Confirmo 2", "Pago 7777",
    "aparto 1", "rento 3", "ya quedo 2", "listo con 7777", "ya le escribi 7777", "Yo le contesto 2",
    "eso no", "regresalo", "cancela eso", "Me equivoqué", "Ojo: mañana no hay agua", "ojo con eso", "regla de 3",
    "Recuerda que mañana voy a la finca",
])
def test_adv_mesa_platica_no_cambia_nada(texto):
    o = ordenes.leer(texto)
    assert o is None or not ordenes.POR_ID[o["orden"]].cambia, (texto, o)


def test_adv_mesa_dile_partido_o_a_medias_no_se_dicta(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    for texto in ("dile al 1234 5678 que ya", "Dile a 7777 que:", "dile 7777 que", "dile a 777.123.4567 que ¿a qué hora llega?"):
        _orden(con_mesa, texto)
        _orden(con_mesa, "sí, mándalo")
    assert not _dictadas(con_mesa)


def test_adv_mesa_dictado_en_dos_pasos_y_si_suelto_es_platica(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    assert _orden(con_mesa, "sí") is None and _orden(con_mesa, "no") is None  # sin dictado: plática, sin respuesta
    assert _orden(con_mesa, "sí", de=OTRA) is None  # ni el "solo lo puede ordenar" a quien no aprueba
    r = _orden(con_mesa, f"dile a {HILO[-4:]} que con gusto le aparto")
    assert r.startswith(f"Le mando a …{HILO[-4:]}") and "«con gusto le aparto»" in r and not _dictadas(con_mesa)
    assert _orden(con_mesa, "no lo mandes") == "Listo, no lo mando."
    assert _orden(con_mesa, "sí, mándalo") is None and not _dictadas(con_mesa)
    _orden(con_mesa, f"dile a {HILO[-4:]} que con gusto le aparto")
    assert "Va en la cola" in _orden(con_mesa, "sí, mándalo")
    assert _dictadas(con_mesa)[-1].id in enviador.pendientes(con_mesa)


def test_adv_mesa_deshaz_no_camina_hacia_atras_ni_revive_una_pausa(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    _orden(con_mesa, "pausa")
    assert "enciende el envío" in _orden(con_mesa, "deshaz") and con_mesa.config()["encendido"] == "sombra"
    _orden(con_mesa, f"nota {HILO[-4:]} paga el viernes")
    assert "Borré la nota" in _orden(con_mesa, "deshaz")
    assert "ya la deshice" in _orden(con_mesa, "deshaz") and con_mesa.config()["encendido"] == "sombra"


# ----------------------------------------------- segunda revisión: lo que hace cada orden
def test_adv2_cerro_con_comas_o_puntos_se_asienta(con_mesa):
    for monto in ("$15,000", "15.000", "15 000"):
        r = _orden(con_mesa, f"cerró {HILO[-4:]} {monto}")
        assert r and "$15,000" in r, (monto, r)
        _orden(con_mesa, "deshaz")


def test_adv2_ambas_ve_lo_apartado_a_mano(con_mesa):
    from agente import calendario
    _orden(con_mesa, "aparta finca del 9 al 11 de noviembre de 2027")
    cot = {"llegada": "2027-11-09", "salida": "2027-11-11", "opciones": [{"propiedad": "ambas"}]}
    assert "ambas" in calendario.apartada(con_mesa, cot)
    assert "OCUPADA" in _orden(con_mesa, "libre las dos del 9 al 11 de noviembre de 2027")


def test_adv2_libera_parcial_no_suelta_todo_el_bloque(con_mesa):
    _orden(con_mesa, "aparta finca del 1 al 15 de diciembre de 2027")
    _orden(con_mesa, "libera finca del 9 al 11 de diciembre de 2027")
    assert "OCUPADA" in _orden(con_mesa, "libre finca del 2 al 4 de diciembre de 2027")
    assert "OCUPADA" not in _orden(con_mesa, "libre finca del 9 al 11 de diciembre de 2027")  # sin calendario: sin saber
    assert "OCUPADA" in _orden(con_mesa, "libre finca del 12 al 14 de diciembre de 2027")
    _orden(con_mesa, "deshaz")
    assert "OCUPADA" in _orden(con_mesa, "libre finca del 9 al 11 de diciembre de 2027")


def test_adv2_deshaz_atendido_repetido_regresa_al_pendiente(con_mesa):
    import time

    from agente import historial
    from tests.test_agente_enjambre import _m
    ahora = int(time.time())
    con_mesa.agregar_linea(capacidades.MARCAS, {"hilo": HILO, "tipo": "atendido", "valor": True, "por": "x",
                                                "en": "2026-10-31T00:00:00+00:00", "ts": ahora - 100})
    historial.guardar(con_mesa, [_m("wamid.X1", "¿sigue libre?", ts=ahora - 50)])  # escribió después
    _orden(con_mesa, f"ya le contesté {HILO[-4:]}")   # otra vez
    _orden(con_mesa, "deshaz")                         # se arrepiente: vuelve la marca vieja, no una nueva
    assert f"…{HILO[-4:]}" in _orden(con_mesa, "pendientes")


def test_adv2_recuerda_deshecho_no_cuenta(con_mesa):
    _orden(con_mesa, "recuerda: la alberca se calienta con 24 h")
    _orden(con_mesa, "deshaz")
    assert "reglas suyas" not in _orden(con_mesa, "propuestas")


def test_adv2_huecos_en_sabado_incluye_este_fin(con_mesa, monkeypatch):
    from datetime import date
    monkeypatch.setattr(capacidades, "_hoy", lambda: date(2026, 10, 31))  # sábado
    assert "· 31/10" in _orden(con_mesa, "huecos")


def test_adv2_ficha_no_borra_la_lista(con_mesa):
    _orden(con_mesa, "pendientes")
    _orden(con_mesa, "ficha 1")
    assert _orden(con_mesa, "ficha 2").startswith("Cliente")


def test_adv2_horas_en_hora_de_mexico(con_mesa, monkeypatch):
    from datetime import datetime, timezone
    cuando = datetime(2026, 10, 30, 15, 30, tzinfo=timezone.utc)  # 09:30 en México
    con_mesa.agregar_linea(enviador.ENVIADOS, {"salida": "x", "hilo": HILO, "cuando": cuando.isoformat(), "enviado": True})
    monkeypatch.setattr(mesa, "_hoy", lambda e: e.leer_lineas(enviador.ENVIADOS))
    assert "09:30" in _orden(con_mesa, "enviados")


def test_adv2_reporte_y_panel_cuentan_igual(con_mesa):
    from agente import operacion, semaforo
    _orden(con_mesa, f"ya le contesté {HILO[-4:]}")
    assert semaforo.resumen(operacion._semaforo(con_mesa))["rojo"] == semaforo.resumen(capacidades._filas(con_mesa))["rojo"]


def test_adv2_precios_de_ambas(con_mesa):
    assert "Lista activa" in _orden(con_mesa, "precios las dos")


def test_adv2_una_orden_vacia_no_gasta_el_deshaz(con_mesa):
    _orden(con_mesa, f"nota {HILO[-4:]} paga el viernes")
    _orden(con_mesa, "descarta la ronda")  # no hay ronda: no cambia nada
    assert "Borré la nota" in _orden(con_mesa, "deshaz")


def test_adv2_aprobar_una_ronda_grande_no_detiene_al_lector(con_mesa):
    import time

    from agente import historial
    from tests.test_agente_enjambre import _m
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    base = int(time.time()) - 30 * 3600
    mensajes = []
    for i in range(700):  # del tamaño de Finca Emiliano: ~11,000 mensajes en 700 pláticas
        h = f"52177700{i:05d}"
        mensajes += [_m(f"w{i}-{k}", f"Mensaje {k} de la plática", k % 2 == 1, ts=base - 86400 + i * 20 + k, hilo=h)
                     for k in range(14)]
        mensajes += [_m(f"w{i}a", "Hola, ¿precio para 10?", ts=base + i, hilo=h),
                     _m(f"w{i}b", "Claro, ¿qué fechas?", True, ts=base + i + 1, hilo=h)]
    historial.guardar(con_mesa, mensajes)
    entradas = [{"hilo": f"52177700{i:05d}", "ultimo_id": f"w{i}b", "textos": ["Hola, sigue interesado?"]}
                for i in range(120)]
    rondas.cargar(con_mesa, {"nombre": "grande", "orden": "prueba", "entradas": entradas})
    inicio = time.perf_counter()
    r = _orden(con_mesa, "aprueba la ronda")
    assert "Aprobé 120" in r and time.perf_counter() - inicio < 3, (r, time.perf_counter() - inicio)
