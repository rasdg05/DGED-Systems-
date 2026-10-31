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
