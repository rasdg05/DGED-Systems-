"""Las jugadas del giro (`agente/jugadas.py`). Cada caso es una frase real del
negocio de Finca Emiliano (sin teléfonos ni nombres de clientes), o el error
que la sesión del 2026-10-27 encontró al medir."""
from __future__ import annotations

import pytest
from agente import historial, jugadas, pendientes
from agente.historial import Mensaje


def _m(ident, texto, del_negocio=False, ts=1790000000, hilo="5210000000001", tipo="text"):
    return Mensaje(id=ident, hilo=hilo, del_negocio=del_negocio, ts=ts, tipo=tipo, texto=texto)


@pytest.mark.parametrize("texto, esperada", [
    # cifra: con miles, pelona de 4 cifras, de 3 con su unidad, dentro de una plantilla
    ("35,000 el fin de semana", "cifra"),
    ("4500 la ncohe", "cifra"),
    ("900 el Día", "cifra"),
    ("Y de las visitas 100 pesos por persona", "cifra"),
    ("Quinta Emiliano es nuestra opción para ti!\n-Jardín\nPrecio $ 10,000 por noche, hasta para 20 personas.",
     "cifra"),
    # disponibilidad
    ("Ya tenemos ocupado esa fecha", "disponibilidad"),
    ("Ya tenemos esa fecha reservada", "disponibilidad"),
    ("Si ese fin va estar rentado pero les enseño del jardín si no tienen problema?", "disponibilidad"),
    ("Si tenemos disponibilidad", "disponibilidad"),
    # pide el dato que falta
    ("Que fecha ?", "pide:fechas"),
    ("Por favor, haznos saber tus fechas de interés y la cantidad personas que asistirán ?", "pide:fechas"),
    ("El fin de semana o solo 1 noche ?", "pide:fechas"),
    ("Cuántas personas ?", "pide:personas"),
    ("El sábado las personas que vienen se van a quedar o solo son visitas?", "pide:personas"),
    ("Es boda ?", "pide:evento"),
    ("Con cuantas habitaciones?", "pide:propiedad"),
    # información
    ("Estamos ubicados en Chiconcuac Morelos\nA 20 minutos de Cuernavaca", "info:ubicacion"),
    ("Morelos", "info:ubicacion"),
    ("37 personas", "info:capacidad"),
    ("Tenemos 2 casas tengo la finca para 37 y a un lado la quinta para 20 más", "info:capacidad"),
    ("Entrada 10:00 am y salida 1:00 pm", "info:incluye"),
    ("Ok los alimentos son con mobiliario", "info:incluye"),
    # el resto
    ("Me envía su ine  por favor", "anticipo"),
    ("Ok déjeme checar", "espera"),
    ("Si quiere videollamada o visita se puede", "visita"),
    ("A qué hora los esperamos mañana ?", "visita"),
    ("Buen día", "saludo"),
    ("Con gusto quedo pendiente", "acuse"),
    ("Ok cuando gusten", "acuse"),
])
def test_jug_frases_reales_del_negocio(texto, esperada):
    assert jugadas.jugada(texto) == esperada


def test_jug_un_ano_o_una_hora_no_es_cifra():
    assert jugadas.jugada("Para el 2027?") != "cifra"
    assert jugadas.jugada("A las 12:00 los veo") != "cifra"
    assert jugadas.jugada("Para 150 personas?") == "pide:personas"


def test_jug_medios():
    assert jugadas.jugada(None, "imagen") == "fotos"
    assert jugadas.jugada(None, "audio") == "medio"


def test_jug_la_tanda_la_decide_lo_que_trae_contenido():
    """20 imágenes y al final *"28,000"*: es una cifra (la muestra a mano lo vio
    mal por leer solo los primeros cinco mensajes)."""
    tanda = [_m(f"f{i}", None, True, tipo="imagen") for i in range(20)] + [_m("x", "28,000", True)]
    assert jugadas.jugada_de_tanda(tanda) == "cifra"
    assert jugadas.jugada_de_tanda([_m("a", "Buen día", True), _m("b", "Para que fecha ?", True)]) == "pide:fechas"


def test_jug_un_si_a_una_pregunta_confirma_y_sin_pregunta_es_acuse():
    si = [_m("s", "Sii", True)]
    assert jugadas.jugada_de_tanda(si, "Oye es petfriendly?") == "confirma"
    assert jugadas.jugada_de_tanda([_m("s", "Si", True)], "Ok serían 18 mil pesos por fin de semana") == "confirma"
    assert jugadas.jugada_de_tanda(si, "Ya llegamos") == "acuse"


# ----------------------------------------------------------------- lo automático
def _hilos_con(textos_repetidos: dict[str, int]) -> dict[str, list[Mensaje]]:
    hilos = {}
    for texto, n in textos_repetidos.items():
        for i in range(n):
            h = f"52{abs(hash(texto)) % 1000:03d}{i:04d}"
            hilos[h] = [_m(f"c{h}", "Hola", hilo=h), _m(f"n{h}", texto, True, ts=1790000100, hilo=h)]
    return hilos


def test_jug_un_ok_repetido_no_es_plantilla():
    """Hallazgo 2026-10-27: *"Ok"* (26 usos), *"Si"* (21) y *"Sí claro"* (21)
    contaban como plantillas: 21 hilos de Finca Emiliano parecían sin persona."""
    hilos = _hilos_con({"Ok": 26, "Sí claro": 21, "Gracias por comunicarte. ¿Qué fechas tienen?": 20})
    assert jugadas.plantillas(hilos) == {"Gracias por comunicarte. ¿Qué fechas tienen?"}


def test_jug_la_bienvenida_tarde_es_automatica_y_la_respuesta_rapida_no():
    fija = "Somos Finca. Capacidad para muchas personas y alberca"
    hilo = [
        _m("c1", "Hola", ts=1000),
        _m("n1", fija, True, ts=1000 + 3600),          # abre el intercambio: bienvenida que llegó tarde
        _m("c2", "Precio?", ts=1000 + 7200),
        _m("n2", fija, True, ts=1000 + 7200 + 5),       # a los 5 s: contestador
        _m("c3", "¿Y la alberca?", ts=1000 + 9000),
        _m("n3", fija, True, ts=1000 + 9000 + 600),     # a los 10 min y tras otro del negocio: la eligió una persona
    ]
    assert jugadas.automaticas(hilo, {fija}) == {"n1", "n2"}


def test_jug_pendientes_cuentan_el_ok_de_una_persona(espacio):
    fija = "Gracias por comunicarte. ¿Qué fechas tienen?"
    mensajes = []
    for i in range(jugadas.USOS_DE_PLANTILLA):
        h = f"54{i:03d}"
        mensajes += [_m(f"p{i}", "Info", hilo=h), _m(f"q{i}", fija, True, ts=1790000001, hilo=h),
                     _m(f"r{i}", "¿Precio para 10?", ts=1790000002, hilo=h)]
    # Una persona contestó "Ok" en un hilo (y "Ok" se repite en todos lados: no es plantilla)
    mensajes += [_m("o1", "Ok", True, ts=1790000001 + 3600, hilo="54000"),
                 _m("o2", "¿Y para 12?", ts=1790000001 + 7200, hilo="54000")]
    historial.guardar(espacio, mensajes)
    lista = {p.hilo: p for p in pendientes.leer(historial.hilos(espacio)) if p.hilo.startswith("54")}
    assert lista["54000"].hubo_persona and not lista["54001"].hubo_persona


# ----------------------------------------------------------------- los momentos
def test_jug_momentos_saltan_lo_automatico_y_lo_que_no_es_venta():
    fija = "Gracias por comunicarte. ¿Qué fechas tienen?"
    hilos = _hilos_con({fija: 20})
    venta = "5219990000001"
    hilos[venta] = [
        _m("v1", "¡Hola! Quiero más información", ts=100, hilo=venta),
        _m("v2", fija, True, ts=101, hilo=venta),                 # automática: no es momento
        _m("v3", "Del 13 al 15 de noviembre, 20 personas", ts=200, hilo=venta),
        _m("v4", "25,000 el fin de semana", True, ts=900, hilo=venta),
    ]
    # La dueña como clienta de otro negocio: no es plática de venta
    ajeno = "5219990000002"
    hilos[ajeno] = [_m("a1", "¡Hola! Quiero más información", True, ts=100, hilo=ajeno),
                    _m("a2", "Bienvenido a la tienda", ts=120, hilo=ajeno),
                    _m("a3", "Me podrías cotizar decoración", True, ts=130, hilo=ajeno)]
    moms = [m for m in jugadas.momentos(hilos) if m.hilo in (venta, ajeno)]
    assert [(m.id, m.casa) for m in moms] == [("v4", "cifra")]
    assert [x.id for x in moms[0].prefijo] == ["v1", "v2", "v3"]
    assert moms[0].entrante.id == "v3"
