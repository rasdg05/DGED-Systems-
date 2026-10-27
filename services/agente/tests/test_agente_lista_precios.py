"""La lista de precios leída de las cotizaciones del negocio y el cotizador por grupo.

Cada caso sale de una forma real de escribir de Finca Emiliano (2026-07-29 →
2026-10-27), con textos reescritos y teléfonos ficticios: ningún dato de un
cliente final entra a git.
"""
from __future__ import annotations

from datetime import date

import pytest
from agente import agente, canal, cotizador, historial, lectura, lista_precios, perfil, vara
from agente.espacio import Espacio
from agente.historial import Mensaje

T0 = 1790000000            # 2026-09-21, lunes
DIA = 86400
BIENVENIDA = "Gracias por comunicarte con Finca Prueba. Haznos saber tus fechas de interés y la cantidad personas"
FINCA = "Somos Finca Prueba.\nInstalaciones:\n-Capacidad para 37 personas\n-9 Habitaciones\n-Alberca"
QUINTA = ("Quinta Prueba es nuestra opción para ti!\n-5 habitaciones con baño completo\n"
          "-Alberca climatizada (costo adicional*)\nPrecio $ 10,000 por noche, hasta para 20 personas.")


def _m(ident, texto, del_negocio, ts, hilo="5210000000001", tipo="text"):
    return Mensaje(id=ident, hilo=hilo, del_negocio=del_negocio, ts=ts, tipo=tipo, texto=texto)


# ----------------------------------------------------------------- lo que dijo el cliente
@pytest.mark.parametrize("texto, n", [
    ("8 adultos y 4 niños", 12), ("Somos 8 adultos 6 jóvenes y 3 niñas", 17), ("12 adultos y un menor", 13),
    ("De 20 a 25 personas", 25), ("Fin de año y somos 24", 24), ("Cómo para 22 personas aprox", 22),
    ("30 o 33 personas", 33), ("11 huespedes", 11), ("Hola, buenas tardes", None), ("A las 10 de la mañana", None),
])
def test_lectura_cuantos_son(texto, n):
    assert lectura.personas_en(texto) == n


def test_lectura_numero_pelon_solo_si_el_negocio_pregunto():
    """*"20"* a secas son personas si el negocio acababa de preguntarlas; si no, no."""
    pregunta = [_m("a", "Precio?", False, T0), _m("b", "Cuántas personas?", True, T0 + 60), _m("c", "20", False, T0 + 90)]
    assert lectura.personas(pregunta) == 20
    sin = [_m("a", "Precio?", False, T0), _m("b", "Hola buen día", True, T0 + 60), _m("c", "20", False, T0 + 90)]
    assert lectura.personas(sin) is None
    rango = [_m("b", "Cuántas personas ?", True, T0), _m("c", "De 15 a 20", False, T0 + 30)]
    assert lectura.personas(rango) == 20


@pytest.mark.parametrize("texto, esperado", [
    ("Del 23 al 27 de diciembre", (date(2026, 12, 23), date(2026, 12, 27))),
    ("29 de diciembre al 02 de enero", (date(2026, 12, 29), date(2027, 1, 2))),
    ("Dl 31 d dic al 2 d enero", (date(2026, 12, 31), date(2027, 1, 2))),
    ("Del 23 al 25 de. Dic", (date(2026, 12, 23), date(2026, 12, 25))),
    ("16-18 de octubre", (date(2026, 10, 16), date(2026, 10, 18))),
    ("para el 24 de diciembre 2 noches y 3 días", (date(2026, 12, 24), date(2026, 12, 26))),
    ("Del 19 de marzo al 23 de marzo", (date(2027, 3, 19), date(2027, 3, 23))),   # sin año: la próxima vez
    # lo ambiguo no se lee: ¿dos noches o tres? ¿una o dos?
    ("30, 31 de diciembre y 1 de enero", None), ("24 y 25 de diciembre", None), ("El 16 y el 17 2 noches", None),
])
def test_lectura_fechas_solo_sin_ambiguedad(texto, esperado):
    assert lectura.fechas_en(texto, date(2026, 10, 6)) == esperado


def test_lectura_noches_pedidas_sin_fechas():
    assert lectura.noches([_m("a", "Solo una noche de sábado a domingo", False, T0)]) == 1
    assert lectura.noches([_m("a", "Precio?", False, T0), _m("b", "Solo 1 noche ?", True, T0 + 9),
                           _m("c", "Siii", False, T0 + 20)]) == 1
    assert lectura.noches([_m("a", "Costo del fin de semana?", False, T0)]) == 2
    assert lectura.noches([_m("a", "Costo?", False, T0)]) is None


# ----------------------------------------------------------------- leer una cotización
def test_lista_monto_pegado_a_su_unidad_y_las_dos_formas_de_escribir():
    assert lista_precios.montos("12.000 el fin de semana") == [12000]
    assert lista_precios.montos("Mesas con 10 sillas $600,00 c/u") == [600]
    assert lista_precios.montos("5mil pesos la noche") == [5000]
    assert lista_precios.montos("https://maps.google.com/?q=18.775192,-99.201675") == []
    assert lista_precios.montos("entrada 10:00 am y salida 1:00 pm, 50%") == []
    assert lista_precios._monto_de("Se lo dejaría en 36,000 es decir 9,000 la noche") == 9000
    assert lista_precios._monto_de("Está en 10,000 la noche pero podría bajarles a 9,000") == 10000
    partes = lista_precios.clausulas("Con 6 habitaciones 22,000 el fin de semana\nCon 9 habitaciones 28,000 el fin de semana")
    assert len(partes) == 2
    assert lista_precios.clausulas("12,000 el\nFin de semana") == ["12,000 el\nFin de semana"]
    assert lista_precios.clausulas("5500 la noche y el costo de la alberca 900 por el\nDía")[1].startswith("el costo")


def test_lista_la_bienvenida_no_presenta_ninguna_propiedad():
    """La bienvenida lleva el nombre del negocio (*"Finca …"*): no es la finca."""
    assert lista_precios.propiedad_en(BIENVENIDA) is None
    assert lista_precios.propiedad_en(FINCA) == "finca"
    assert lista_precios.propiedad_en(QUINTA) == "quinta"
    assert lista_precios.propiedad_en("Solo tengo la quinta disponible") == "quinta"
    assert lista_precios.propiedad_en("Sería en las dos casas, están juntas") == "ambas"


def _platica(h: str, t: int, cliente: str, presentacion: str | None, precio: str, pregunta: str = "Costo?") -> list:
    salida = [_m(f"{h}a", "¡Hola! Quiero más información", False, t, h),
              _m(f"{h}b", BIENVENIDA, True, t + 2, h),
              _m(f"{h}c", cliente, False, t + 60, h)]
    if presentacion:
        salida.append(_m(f"{h}d", presentacion, True, t + 120, h))
    salida += [_m(f"{h}e", pregunta, False, t + 180, h), _m(f"{h}f", precio, True, t + 240, h)]
    return salida


def test_lista_propiedad_por_la_presentacion_y_grupo_por_el_cliente():
    ms = _platica("5210000000001", T0, "Somos 20 personas", QUINTA, "5,000 la noche")
    obs = lista_precios.observaciones({"5210000000001": ms})
    precio = [o for o in obs if o.id.endswith("f")][0]
    assert (precio.propiedad, precio.personas, precio.unidad, precio.monto_centavos) == ("quinta", 20, "noche", 500000)
    assert precio.grupo == {"id": "5210000000001c", "cita": "Somos 20 personas"}
    plantilla = [o for o in obs if o.id.endswith("d")][0]      # la plantilla con precio también es cotización
    assert (plantilla.personas, plantilla.habitaciones, plantilla.monto_centavos) == (20, 5, 1000000)


def _lista_de(espacio: Espacio, platicas: list[list[Mensaje]]) -> dict:
    historial.guardar(espacio, [m for p in platicas for m in p])
    return lista_precios.leer(espacio, temporadas=[])


def _platicas_finca() -> list[list[Mensaje]]:
    """Cuatro grupos de 20 a 22,000 (uno a 25,000), tres de 37 a 35,000, dos de 16 a 20,000."""
    datos = [("Somos 20", "22,000 el fin de semana con 6 habitaciones"), ("20 personas", "22,000 el fin de semana con 6 habitaciones"),
             ("seriamos 20 personas", "22,000 el fin de semana con 6 habitaciones"),
             ("Para 20 personas", "25,000 el fin de semana con 6 habitaciones"),
             ("Somos 20 adultos", "22,000 el fin de semana con 6 habitaciones"),
             ("Las 37", "Para 37 personas está en 35,000 el fin de semana"),
             ("Somos 37", "35,000 el fin de semana para 37 personas"),
             ("37 personas", "Hasta 37 personas 35,000 el fin de semana"),
             ("Somos 16", "20,000 el fin de semana"), ("16 personas", "20,000 el fin de semana")]
    return [_platica(f"52100000001{i:02d}", T0 + i * DIA, c, FINCA, p) for i, (c, p) in enumerate(datos)]


def test_lista_escalones_con_su_acuerdo_y_validos_para_el_perfil(tmp_path):
    espacio = Espacio("prueba-lista", tmp_path)
    lista = _lista_de(espacio, _platicas_finca())
    grupo = sorted((r["personas"], r.get("monto_centavos"), r.get("habitaciones"))
                   for r in lista["reglas"] if r["tipo"] == "grupo")
    assert grupo == [(16, 2000000, None), (20, 2200000, 6), (37, 3500000, None)]
    veinte = next(r for r in lista["reglas"] if r.get("personas") == 20)
    assert veinte["evidencia"]["acuerdo"] == 0.8 and veinte["evidencia"]["otros"] == {"25000": 1}
    # el 20 lo dijo el cliente: el origen trae su cita y el perfil la revisa
    assert veinte["origen"]["grupo"]["cita"] in {"Somos 20", "20 personas", "seriamos 20 personas", "Somos 20 adultos"}
    limpio, descartados = perfil.validar(espacio, {"reglas": lista["reglas"]})
    assert descartados == [] and len(limpio["reglas"]) == len(lista["reglas"])


def test_lista_un_escalon_mas_chico_no_cobra_mas_y_sin_acuerdo_queda_a_decidir(tmp_path):
    """Monótona: un grupo más grande no paga menos. Sin acuerdo, el escalón queda
    escrito como `a_decidir` (sin monto) y el cotizador no lo salta."""
    platicas = _platicas_finca() + [
        _platica("5210000000201", T0 + 30 * DIA, "Somos 10", FINCA, "4,500 el fin de semana"),
        _platica("5210000000202", T0 + 31 * DIA, "Somos 10", FINCA, "12,000 el fin de semana"),
        _platica("5210000000203", T0 + 32 * DIA, "Somos 10", FINCA, "9,000 el fin de semana"),
        _platica("5210000000204", T0 + 33 * DIA, "Somos 30", FINCA, "21,000 el fin de semana"),  # 30 por menos que 20
    ]
    lista = _lista_de(Espacio("prueba-lista", tmp_path), platicas)
    tabla = sorted((r["personas"], r.get("monto_centavos"), bool(r.get("a_decidir")))
                   for r in lista["reglas"] if r["tipo"] == "grupo")
    montos = [m for _, m, decidir in tabla if not decidir]
    assert montos == sorted(montos)                              # el de 30 a 21,000 no hace un escalón más barato
    hasta_10 = min(t for t in tabla if t[0] >= 10)
    assert hasta_10[2] and hasta_10[1] is None                   # 4,500 / 9,000 / 12,000 para 10: sin acuerdo
    p = {"reglas": lista["reglas"]}
    for n in (8, 10, 12):
        assert not cotizador.cotizar_grupo(p, n).completa        # ni salta al de arriba ni al de abajo
    assert cotizador.cotizar_grupo(p, 20).completas[0].unitario == 2200000


def test_lista_temporada_alta_observada_va_a_confirmar():
    h = "5210000000301"
    ms = [_m("x1", "Del 23 al 27 de diciembre, 15 personas", False, T0, h),
          _m("x2", "Mínimo 3 noches por ser temporada alta", True, T0 + 60, h),
          _m("y1", "29 de diciembre al 2 de enero", False, T0 + DIA, "5210000000302"),
          _m("y2", "Es que en esa temporada si es solo por 3 noches", True, T0 + DIA + 60, "5210000000302")]
    hilos = {}
    for m in ms:
        hilos.setdefault(m.hilo, []).append(m)
    temporadas, minimos = lista_precios.temporada_observada(hilos)
    assert temporadas[0]["desde"] == "12-23" and temporadas[0]["hasta"] == "01-01" and temporadas[0]["a_confirmar"]
    assert minimos[0]["noches"] == 3 and "3 noches" in minimos[0]["origen"]["cita"]


# ----------------------------------------------------------------- el perfil revisa el grupo
def _espacio_con(tmp_path, mensajes):
    espacio = Espacio("prueba-grupo", tmp_path)
    historial.guardar(espacio, mensajes)
    return espacio


def _regla(personas=20, cita="25,000 con 6 habitaciones", grupo=None, **extra):
    origen = {"tipo": "mensaje", "id": "n1", "cita": cita}
    if grupo is not None:
        origen["grupo"] = grupo
    return {"tipo": "grupo", "propiedad": "finca", "unidad": "fin_de_semana", "personas": personas,
            "monto_centavos": 2500000, "origen": origen, **extra}


@pytest.mark.parametrize("grupo, motivo", [
    ({"id": "c1", "cita": "Somos 20 personas"}, ""),
    ({"id": "c1", "cita": "Somos 30 personas"}, "la cita del grupo no está literal"),
    ({"id": "c2", "cita": "Somos 25"}, "no dice 20 personas"),
    ({"id": "n0", "cita": "Para 20 personas"}, "lo dice el cliente, no el negocio"),
    ({"id": "c9", "cita": "Somos 20"}, "misma plática, antes"),
    ({"id": "c3", "cita": "Somos 20"}, "misma plática, antes"),
    (None, "cifra que no está en la cita"),
])
def test_perfil_el_grupo_solo_lo_prueba_el_cliente_de_esa_platica_antes(tmp_path, grupo, motivo):
    h = "5210000000401"
    espacio = _espacio_con(tmp_path, [
        _m("n0", "Para 20 personas tenemos lugar", True, T0, h), _m("c1", "Somos 20 personas", False, T0 + 10, h),
        _m("c2", "Somos 25", False, T0 + 20, h), _m("n1", "25,000 con 6 habitaciones", True, T0 + 30, h),
        _m("c3", "Somos 20", False, T0 + 40, h), _m("c9", "Somos 20", False, T0, "5210000000402")])
    _, descartados = perfil.validar(espacio, {"reglas": [_regla(grupo=grupo)]})
    if not motivo:
        assert descartados == []
    else:
        assert motivo in descartados[0]["motivo"]


def test_perfil_las_habitaciones_tienen_que_estar_en_la_cita(tmp_path):
    h = "5210000000501"
    espacio = _espacio_con(tmp_path, [_m("n1", "Para 20 personas 25,000 el fin de semana", True, T0, h)])
    _, descartados = perfil.validar(espacio, {"reglas": [_regla(cita="Para 20 personas 25,000 el fin de semana",
                                                                habitaciones=6)]})
    assert "['6']" in descartados[0]["motivo"]


def test_perfil_un_numero_pelon_prueba_el_grupo_si_contestaba_cuantas_personas(tmp_path):
    h = "5210000000601"
    espacio = _espacio_con(tmp_path, [
        _m("c0", "Precio?", False, T0, h), _m("n0", "Cuántas personas?", True, T0 + 10, h),
        _m("c1", "20", False, T0 + 20, h), _m("n1", "25,000 con 6 habitaciones", True, T0 + 30, h)])
    _, descartados = perfil.validar(espacio, {"reglas": [_regla(grupo={"id": "c1", "cita": "20"})]})
    assert descartados == []


# ----------------------------------------------------------------- el cotizador por grupo
def _r(propiedad, unidad, personas, pesos=None, temporada=None, **extra):
    r = {"tipo": "grupo", "propiedad": propiedad, "unidad": unidad, "personas": personas, **extra}
    if pesos is None:
        r["a_decidir"] = True
    else:
        r["monto_centavos"] = pesos * 100
    if temporada:
        r["temporada"] = temporada
    return r


LISTA = {"temporadas": [{"nombre": "fin_de_ano", "desde": "12-23", "hasta": "01-01", "fin_de_ano": True}],
         "reglas": [
             _r("finca", "fin_de_semana", 19, 20000, evidencia={"n": 5}), _r("finca", "fin_de_semana", 20, 22000, habitaciones=6),
             _r("finca", "fin_de_semana", 25, 25000), _r("finca", "fin_de_semana", 37, 35000, evidencia={"n": 22}),
             _r("finca", "noche", 40),
             _r("quinta", "noche", 16), _r("quinta", "noche", 20, 10000, evidencia={"n": 18}),
             _r("quinta", "noche", 20, 10000, temporada="fin_de_ano"),
             _r("ambas", "fin_de_semana", 50, 45000),
             {"tipo": "minimo_noches", "propiedad": "quinta", "noches": 3, "temporada": "fin_de_ano"},
             {"tipo": "anticipo", "propiedad": "finca", "pct": 50},
             {"tipo": "extra", "concepto": "alberca", "propiedad": "finca", "unidad": "dia", "monto_centavos": 200000},
             {"tipo": "extra", "concepto": "alberca", "propiedad": "quinta", "unidad": "dia", "monto_centavos": 90000},
         ]}


def test_cotizador_grupo_el_escalon_mas_chico_que_cabe():
    c = cotizador.cotizar_grupo(LISTA, 21)
    finca = next(o for o in c.completas if o.propiedad == "finca")
    assert (finca.escalon, finca.unitario, finca.unidad) == (25, 2500000, "fin_de_semana")
    assert "Finca para 20 personas con 6 habitaciones: $22,000 el fin de semana." in cotizador.cotizar_grupo(LISTA, 20).texto()


def test_cotizador_grupo_lo_que_toca_decidir_al_duenio_no_se_salta():
    """12 personas en la quinta: su escalón (hasta 16) está a decidir; no se le
    cobra lo de 20. Con la quinta como propiedad de la plática, se pasa a la finca."""
    c = cotizador.cotizar_grupo(LISTA, 12, propiedad="quinta")
    assert [o.propiedad for o in c.completas] == ["finca"]
    solo_quinta = {"reglas": [r for r in LISTA["reglas"] if r.get("propiedad") == "quinta"], "temporadas": []}
    c = cotizador.cotizar_grupo(solo_quinta, 12)
    assert not c.completa and "a decidir" in "; ".join(c.faltan)


def test_cotizador_grupo_la_propiedad_de_la_platica_y_las_dos_solo_si_no_cabe():
    assert [o.propiedad for o in cotizador.cotizar_grupo(LISTA, 18, propiedad="quinta").completas] == ["quinta"]
    assert {o.propiedad for o in cotizador.cotizar_grupo(LISTA, 18).completas} == {"finca", "quinta"}
    assert [o.propiedad for o in cotizador.cotizar_grupo(LISTA, 45).completas] == ["ambas"]
    assert "ambas" not in {o.propiedad for o in cotizador.cotizar_grupo(LISTA, 30).opciones}
    c = cotizador.cotizar_grupo(LISTA, 80)
    assert not c.completa and "80 personas" in c.faltan[0]


def test_cotizador_grupo_con_fechas_fin_de_semana_o_por_noche():
    viernes = date(2026, 11, 6)
    c = cotizador.cotizar_grupo(LISTA, 20, viernes, date(2026, 11, 8), propiedad="finca")
    assert c.completas[0].total == 2200000 and "del 6 al 8 de noviembre de 2026 (2 noches" in c.texto()
    assert "Se aparta con el 50%" in c.texto()
    # de domingo a martes no es fin de semana: la finca no tiene precio por noche para 20
    c = cotizador.cotizar_grupo(LISTA, 20, date(2026, 11, 8), date(2026, 11, 10), propiedad="finca")
    assert [o.propiedad for o in c.completas] == ["quinta"] and c.completas[0].total == 2000000


def test_cotizador_grupo_temporada_con_su_tabla_y_su_minimo():
    c = cotizador.cotizar_grupo(LISTA, 15, date(2026, 12, 29), date(2027, 1, 2))
    assert [(o.propiedad, o.total) for o in c.completas] == [("quinta", 4000000)]   # la finca no tiene tabla de fin de año
    c = cotizador.cotizar_grupo(LISTA, 15, date(2026, 12, 31), date(2027, 1, 2), propiedad="quinta")
    assert not c.completa and any("mínimo de 3 noches" in f for f in c.faltan)
    # una estancia que cruza el fin de la temporada no se cotiza sola: lo ve una persona
    cruza = cotizador.cotizar_grupo(LISTA, 15, date(2026, 12, 30), date(2027, 1, 3), propiedad="quinta")
    assert not cruza.completa and "cruza dos temporadas" in "; ".join(cruza.faltan)


def test_cotizador_grupo_sin_fechas_la_unidad_que_pidio_el_cliente():
    assert cotizador.cotizar_grupo(LISTA, 18, propiedad="quinta").completas[0].unidad == "noche"
    c = cotizador.cotizar_grupo(LISTA, 30, noches=1, propiedad="finca")
    assert not c.completa                                       # una noche para 30 en la finca: a decidir


def test_cotizador_extra_por_propiedad():
    assert cotizador.extra(LISTA, "alberca", "quinta")["monto_centavos"] == 90000
    assert cotizador.extra(LISTA, "alberca", None) is None       # dos precios, sin saber de cuál casa


# ----------------------------------------------------------------- en el turno
BASE = {"cliente_id": "prueba", "hilo": "5210000000701", "responde_a": "x"}


def _turno(*mensajes):
    hilo = [_m(f"t{i}", t, n, T0 + i * 60, BASE["hilo"]) for i, (t, n) in enumerate(mensajes)]
    return agente.antes_del_modelo(BASE, hilo[-1], hilo, LISTA)


def test_turno_cotiza_por_grupo_sin_modelo_y_espera_aprobacion():
    s = _turno(("Hola, somos 20", False), (QUINTA, True), ("Cuánto cuesta?", False))
    assert s.via == "cotizador" and s.requiere_aprobacion and "$10,000 la noche" in s.texto
    assert s.cotizacion["modo"] == "grupo"


def test_turno_sin_personas_las_pregunta_como_la_casa():
    s = _turno(("Que precio tiene?", False))
    assert s.via == "cotizador" and s.texto == agente.PIDE_PERSONAS and not s.requiere_aprobacion
    # y cuando contesta, cotiza
    s = _turno(("Que precio tiene?", False), (agente.PIDE_PERSONAS, True), ("37", False))
    assert s.via == "cotizador" and "$35,000" in s.texto and s.requiere_aprobacion


@pytest.mark.parametrize("pregunta", ["Y con cuánto se aparta?", "Cuánto cuesta el evento para 50?",
                                      "Qué costo tienen las mesas?"])
def test_turno_apartado_y_eventos_no_se_cotizan_como_hospedaje(pregunta):
    s = _turno(("Somos 20", False), (FINCA, True), (pregunta, False))
    assert s is None or s.via != "cotizador"


def test_turno_la_alberca_con_el_precio_de_su_casa():
    s = _turno(("Somos 10", False), (QUINTA, True), ("Cuánto es lo de la alberca climatizada?", False))
    assert s.via == "cotizador" and "$900 el día" in s.texto and s.requiere_aprobacion


def test_turno_incompleta_va_a_la_persona_con_el_borrador():
    s = _turno(("Somos 12", False), ("Solo tengo la quinta", True), ("Precio por noche?", False))
    sola = {"reglas": [r for r in LISTA["reglas"] if r.get("propiedad") == "quinta"], "temporadas": []}
    hilo = [_m("u0", "Somos 12", False, T0, BASE["hilo"]), _m("u1", "Precio por noche?", False, T0 + 60, BASE["hilo"])]
    s = agente.antes_del_modelo(BASE, hilo[-1], hilo, sola)
    assert s.via == "persona" and s.texto == agente.LO_CONFIRMO and "a decidir" in s.motivo and s.cotizacion


def test_turno_el_aviso_de_protocolo_no_esconde_lo_que_el_cliente_escribio():
    """Hallazgo 2026-10-27: `[otro]` (reacción, edición, llaves de WhatsApp) llegaba
    justo después del texto del cliente (475 de 710) y el turno lo leía como "foto
    o audio": todo a una persona sin leer el texto."""
    h = BASE["hilo"]
    hilo = [_m("v0", "Somos 20, precio?", False, T0, h), _m("v1", None, False, T0 + 1, h, tipo="otro")]
    s = agente.antes_del_modelo(BASE, hilo[-1], hilo, LISTA)
    assert s.via == "cotizador" and "$22,000" in s.texto
    solo = [_m("v1", None, False, T0, h, tipo="otro")]
    assert agente.antes_del_modelo(BASE, solo[-1], solo, LISTA).via == "persona"
    foto = [_m("v0", "Somos 20, precio?", False, T0, h), _m("v2", None, False, T0 + 1, h, tipo="imagen")]
    assert agente.antes_del_modelo(BASE, foto[-1], foto, LISTA).via == "persona"


def test_canal_una_cifra_sin_aprobacion_no_sale_aunque_no_este_marcada(tmp_path, monkeypatch):
    """Defensa de fondo de la invariante XXXIII: si alguien olvida `requiere_aprobacion`."""
    monkeypatch.setenv("WHATSAPP_TOKEN", "t")
    espacio = Espacio("prueba", tmp_path)
    espacio.escribir_json("config.json", {"phone_number_id": "100000000000001", "encendido": "sin_cifra"})
    s = agente.Salida(cliente_id="prueba", hilo="h", responde_a="x", via="cotizador", texto="Finca: $22,000.")
    assert "cifra sin aprobación" in canal.motivo_para_no_enviar(espacio, s)
    sin_cifra = agente.Salida(cliente_id="prueba", hilo="h", responde_a="x", via="cotizador", texto=agente.PIDE_PERSONAS)
    assert canal.motivo_para_no_enviar(espacio, sin_cifra) == ""


# ----------------------------------------------------------------- en la vara
def test_vara_la_lista_de_cada_platica_se_arma_sin_ella(tmp_path):
    """Su propia cotización no vota el precio con el que se le califica."""
    espacio = Espacio("prueba-lista", tmp_path)
    platicas = _platicas_finca()
    historial.guardar(espacio, [m for p in platicas for m in p])
    completo, por_hilo = lista_precios.para_la_vara(espacio, None, historial.cargar(espacio))
    tiene_16 = [r for r in completo["reglas"] if r.get("personas") == 16 and not r.get("a_decidir")]
    assert tiene_16                                                # dos pláticas de 16: entra
    una_de_16 = platicas[8][0].hilo
    sin = por_hilo(una_de_16)
    assert not [r for r in sin["reglas"] if r.get("personas") == 16 and r.get("monto_centavos") == 2000000]
    assert all(r["origen"]["id"] not in {m.id for m in platicas[8]} for r in sin["reglas"] if "origen" in r)


def test_vara_con_tope_cero_lo_del_modelo_va_a_una_persona():
    h = "5210000000801"
    ms = (_m("w0", "¿Tienen estacionamiento techado?", False, T0, h), _m("w1", "Sí claro", True, T0 + 60, h))
    momento = vara.jugadas.Momento(id="w1", hilo=h, ts=T0 + 60, entrante=ms[0], prefijo=ms[:1], tanda=ms[1:],
                                   casa="confirma", cliente=ms[0].texto)
    assert vara.simular(momento, LISTA)["bot"] == "ia"
    assert vara.simular(momento, LISTA, tope_cero=True)["bot"] == "persona"


def test_panel_precios_muestra_la_lista_por_grupo_sin_palabras_de_desarrollo():
    from agente import paginas

    assert paginas._regla(_r("finca", "fin_de_semana", 20, 22000, habitaciones=6)) == \
        ("Hasta 20 personas · 6 habitaciones · el fin de semana", "$22,000")
    assert paginas._regla(_r("quinta", "noche", 16, evidencia={"desde_personas": 5}))[1] == "Usted lo decide"
    assert paginas._regla(LISTA["reglas"][-1]) == ("Alberca el día", "$900")
