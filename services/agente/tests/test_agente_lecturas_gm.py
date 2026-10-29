"""Corpus de la corrida GM del 2026-10-29: lo que el clasificador de pendientes leía mal.

De dónde sale: los 268 pendientes de Finca Emiliano etiquetados a ciegas por dos
agentes independientes (kappa 0.947, oro en 265). El clasificador acertaba 92.1%
(kappa 0.879); casi todo su error era llamar `espera` a lo que no pide nada
(15 de 21). Cada frase es literal del cliente (sin teléfonos ni nombres) y entró
aquí **antes** del arreglo. Las que no se arreglan quedan en `xfail`: se sabe que
fallan y por qué (n < 5 de su familia, Gestor C9-B4).
"""
from __future__ import annotations

import pytest
from agente import conversacion, pendientes, semaforo
from agente.historial import Mensaje

H = 3600


def _m(i, de_negocio, ts, texto, hilo="h", tipo="text"):
    return Mensaje(i, hilo, de_negocio, ts, tipo, texto)


# --------------------------------------------------------------------------- #
#  No piden nada: aplazan, cierran o agradecen                                 #
# --------------------------------------------------------------------------- #
APLAZA = [
    "Buenas tardes, solo nos faltan por definir tres personas\nGracias por estar pendientes",
    "Hola. Tenemos un familiar hospitalizado y aún no sabemos si si vamos o no.\n"
    "Si después decidimos ir le avisamos, a ver si aún está disponible",
    "Ok me comunico con usted más adelante en l semana",
    "Voy a comentar y le escribo gracias",
]
CIERRA = [
    "Gracias ya tenemos opción",
    "Sera próxima vez ahora no",
    "Ya tengo un lugar tratado",
    "Hola buenos días \nPor motivos de salud tuve que cancelar mi visita.\n"
    "Mis familiares si acudirán, pero ellos ya tienen una reservación por su cuenta.",
]
AGRADECE = [
    "Muchas gracias\nLinda tard e",
    "Entiendo, gracias",
    "que lastima gracias!",
    "Ok te agradezco mucho",
    "😳. Nunca me fijé en eso.\nGracias de todas maneras",
]


@pytest.mark.parametrize("texto", APLAZA + AGRADECE)
def test_gm_no_pide_nada(texto):
    assert conversacion.nada_que_contestar(texto) or conversacion.es_cierre(texto)


@pytest.mark.parametrize("texto", CIERRA)
def test_gm_es_cierre(texto):
    assert conversacion.es_cierre(texto)


@pytest.mark.parametrize("texto", APLAZA + CIERRA + AGRADECE)
def test_gm_el_pendiente_no_espera(texto):
    hilo = [_m("1", False, 0, "Precio para 10?"), _m("2", True, 60, "Son 12,000 el fin de semana"),
            _m("3", False, 3 * H, texto)]
    assert pendientes.leer({"h": hilo})[0].estado == "no_pide"


@pytest.mark.xfail(reason="se fue porque está lejos; n = 1 de su familia", strict=True)
def test_gm_esta_lejos_no_espera():
    assert conversacion.nada_que_contestar(
        "No, es que estamos en Querétaro\nMe salió la publicación y por eso pregunté la ubi")


# --------------------------------------------------------------------------- #
#  Lo que sí sigue pidiendo (que el arreglo no se lo trague)                   #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("texto", [
    "Voy a comentar con mi esposo, me pasa el precio para 20?",
    "Ya tenemos opción para la comida, cuánto sale la noche?",
    "Si después decidimos le aviso. Tienen libre el 14?",
    "Me comunico con usted para apartar, cuál es la cuenta?",
    "Entiendo, y para 15 personas?",
    "Gracias de todas maneras, tienen otra fecha en diciembre?",
    "Sería para 35 personas o 30",
    "Es el máximo de personas?",
    # La prueba de propiedad (1,970 ráfagas) cazó éste: "ya tengo un lugar" + "pero me podrías mandar".
    "Es para el 08/09 noviembre aprox 25 personas\nYa tengo un lugar tratado\nHola buenas tardes\n"
    "Pero me podrías mandar la ubicación por favor",
])
def test_gm_sigue_pidiendo(texto):
    assert not conversacion.nada_que_contestar(texto) and not conversacion.es_cierre(texto)


# --------------------------------------------------------------------------- #
#  La cotización prometida que no llegó                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("promesa, acuse", [
    ("Le envío una cotización", "Si por favor"),
    ("Le envío una cotización", "Si gracis"),
    ("Le hago una cotización", "Gracias"),
])
def test_gm_el_si_a_una_cotizacion_prometida_es_promesa_nuestra(promesa, acuse):
    """El cliente aceptó ("sí, por favor") y la cotización no llegó: la pelota es nuestra.
    Antes quedaba en gris como "cerrada" (3 de 268, de 214 a 530 h)."""
    hilo = [_m("1", False, 0, "Cuánto sería con banquete para 40?"), _m("2", True, 60, promesa),
            _m("3", False, 120, acuse)]
    fila = semaforo.leer({"h": hilo}, 30 * H)[0]
    assert (fila.estado, fila.color) == ("promesa", "rojo")


def test_gm_la_promesa_cumplida_no_es_promesa():
    """Prometió la ubicación y la mandó (un adjunto después): el "Ok" del cliente sí cierra."""
    hilo = [_m("1", False, 0, "Y si podríamos ir a verla"), _m("2", True, 60, "Le envío la ubicación"),
            _m("3", True, 70, "[otro]", tipo="location"), _m("4", False, 120, "Ok")]
    assert semaforo.leer({"h": hilo}, 30 * H)[0].estado == "cerrada"


def test_gm_la_promesa_sin_contestar_tambien_es_promesa():
    hilo = [_m("1", False, 0, "Cuánto sería con banquete?"), _m("2", True, 60, "Le hago una cotización")]
    assert semaforo.leer({"h": hilo}, 30 * H)[0].estado == "promesa"


# --------------------------------------------------------------------------- #
#  Lo que el cotizador leía mal (vara c1, desarrollo: el monto coincidía con la  #
#  casa en 15 de 37). Cada cifra igual espera el sí de una persona (XXXIII),   #
#  pero salía mal armada.                                                      #
# --------------------------------------------------------------------------- #
from agente import lectura  # noqa: E402


@pytest.mark.parametrize("texto", ["Son 3 años\nCosto ???", "son 2 noches", "Son 5 habitaciones?", "van 4 meses"])
def test_gm_una_edad_o_una_cuenta_de_noches_no_son_personas(texto):
    assert lectura.personas_en(texto) is None


@pytest.mark.parametrize("texto, n", [("Somos 20", 20), ("son 12 personas", 12), ("Para 15", 15),
                                      ("Somos 8 adultos y 3 niños de 5 años", 11)])
def test_gm_las_personas_se_siguen_leyendo(texto, n):
    assert lectura.personas_en(texto) == n


def test_gm_sabado_y_entregar_el_domingo_es_una_noche():
    hilo = [_m("1", False, 0, "Qué costo tiene el fin de semana. Sábado y entregar la casa el domingo")]
    assert lectura.noches(hilo) == 1
    assert lectura.noches([_m("1", False, 0, "del viernes al domingo")]) == 2


@pytest.mark.parametrize("texto", ["Me podrá dar el costo de 1 y 2 habitaciones por favor",
                                   "Cuánto cuesta por habitación?", "precio de una recamara"])
def test_gm_el_precio_de_un_cuarto_no_se_cotiza_como_la_casa(texto):
    assert lectura.pide_por_cuarto(texto)


@pytest.mark.parametrize("texto", ["Y de renta por habitación?\nComo hotel o toda la finca", "Precio para 20 personas",
                                   "Cuántas habitaciones tiene"])
def test_gm_no_todo_lo_que_dice_habitacion_pide_un_cuarto(texto):
    assert not lectura.pide_por_cuarto(texto)
