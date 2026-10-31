"""La mesa con las órdenes de Gestor (corrida del 2026-10-31): una tabla que lee,
enseña y da permiso; cada orden hace lo suyo; y las marcas de la dueña mandan en
el canal, las rondas y el calendario, no solo en la mesa."""
from __future__ import annotations

import time
from datetime import date

import pytest
from agente import agente, calendario, canal, capacidades, enviador, historial, mesa, ordenes, perfil, rondas, vinculado
from agente.historial import Mensaje
from tests.test_agente_enjambre import HILO, _m, _ronda

DUENA = "5210000000000"
OTRA = "5217770001111"


@pytest.fixture()
def con_mesa(espacio):
    espacio.escribir_json("config.json", dict(espacio.config(), administradores=["+52 777 000 1111"]))
    hace = int(time.time()) - 5 * 3600  # recientes: el semáforo los ve en rojo, no fríos
    historial.guardar(espacio, [
        _m("wamid.E1", "Hola, ¿tienen la quinta libre en noviembre?", ts=hace),
        _m("wamid.E2", "Claro, ¿para qué fechas y cuántas personas?", True, ts=hace + 100),
        _m("wamid.E3", "Del 9 al 11 de noviembre, somos ocho. ¿Cuánto sería?", ts=hace + 200),
        _m("wamid.B1", "Buen día, ¿hacen bodas? Seríamos 120", ts=hace + 300, hilo="5210000004321"),
    ])
    return espacio


_n = iter(range(10_000))


def _orden(espacio, texto, de=DUENA):
    m = Mensaje(f"o{next(_n)}", de, False, int(time.time()) - 3600, "text", texto)
    historial.guardar(espacio, [m])
    return mesa.atender(espacio, m)


# --------------------------------------------------------------- la tabla
def test_la_tabla_tiene_mas_de_50_ordenes_y_cada_una_su_manejador_y_su_ayuda():
    ids = [o.id for o in ordenes.TABLA]
    assert len(ids) == len(set(ids)) >= 50
    assert set(ids) == set(capacidades.MANEJADORES)  # una regla en dos listas no gobierna: aquí se atan
    for o in ordenes.TABLA:
        assert o.ayuda.strip() and o.tema in ordenes.TEMAS and o.quien in (ordenes.TODAS, ordenes.QUIEN_APRUEBA)
        if o.quien == ordenes.QUIEN_APRUEBA:
            assert o.cambia, f"{o.id} pide a quien aprueba pero dice que no cambia nada"


def test_la_ayuda_sale_de_la_tabla_por_tema():
    general = ordenes.ayuda()
    assert all(ordenes.TEMAS[t] in general for t in ("clientes", "rondas", "precios", "calendario"))
    clientes = ordenes.ayuda("clientes")
    assert all(o.ayuda in clientes for o in ordenes.TABLA if o.tema == "clientes")
    assert ordenes.ayuda("cliente") == clientes  # sinónimo


@pytest.mark.parametrize("texto, orden", [
    # lo de antes sigue igual
    ("Estado", "estado"), ("reporte", "estado"), ("¿Pendientes?", "pendientes"), ("cola", "cola"),
    ("Aprueba la ronda", "aprueba"), ("aprueba ronda prueba-1", "aprueba"), ("Enciende el envío", "enciende"),
    ("pausa el envio", "pausa"), ("ayuda", "ayuda"), ("Oye, mañana llega la familia", None),
    # formato de WhatsApp, diagonal, cortesías (Gestor, 2026-10-07)
    ("*Estado*", "estado"), ("/pendientes", "pendientes"), ("oye asistente, ¿cómo vamos?", "estado"),
    ("Pendientes por favor", "pendientes"), ("dime quién contestó", "contestaron"), ("_cola_", "cola"),
    ("¿?", "ayuda"), ("ayuda precios", "ayuda"), ("🙏 hoy", "hoy"), ("como va la semana", "semana"),
    ("¿dónde está el dinero?", "oportunidades"), ("urgentes", "urgentes"), ("promesas", "promesas"),
    ("quejas", "reclamos"), ("nuevos", "nuevos"), ("fotos", "medios"), ("seguimientos", "seguimiento"),
    ("ficha …1234", "ficha"), ("…1234", "ficha"), ("777 123 4567", "ficha"), ("historial 1234", "historial"),
    ("busca boda", "busca"), ("notas", "notas"), ("notas 2", "notas"), ("marcados", "marcados"),
    ("nota 1234 paga el viernes", "nota"), ("No le escribas a 1234", "no_escribir"),
    ("ya puedes escribirle a 1234", "si_escribir"), ("lo llevo 1234", "lo_llevo"), ("yo la atiendo 2", "lo_llevo"),
    ("suelta 1234", "suelta"), ("ya le contesté a 1234", "atendido"), ("cerró 1234 15000", "cerro"),
    ("Dile a 1234 que ya está apartado", "dile"), ("aprueba 1 3 y 5", "aprueba_borradores"),
    ("aprueba todos", "aprueba_borradores"), ("descarta 2", "descarta"), ("descarta la ronda", "descarta_ronda"),
    ("borradores", "borradores"), ("¿qué espera mi sí?", "borradores"), ("rondas", "rondas"),
    ("ronda prueba-1", "ronda"), ("resultados", "desenlace"), ("enviados", "enviados"), ("¿qué no salió?", "fallidos"),
    ("whatsapp", "canal"), ("frena la cola", "pausa"), ("pausa", "pausa"), ("suelta la cola", "enciende"),
    ("ritmo", "ritmo"), ("máximo 50 al día", "tope"),
    ("cotiza 8 personas del 9 al 11 de noviembre", "cotiza"), ("dame la cotización para 25 personas", "cotiza"),
    ("precios", "precios"), ("precios quinta", "precios"), ("perfil", "perfil"), ("propuestas", "propuestas"),
    ("aprueba la versión 4", "aprueba_perfil"), ("faq", "faq"), ("recuerda: la alberca se calienta", "recuerda"),
    ("gasto", "gasto"), ("libre la finca del 9 al 11 de nov", "disponible"), ("calendario", "calendario"),
    ("huecos", "huecos"), ("aparta finca 9-11 nov", "aparta"), ("libera finca del 9 al 11 de nov", "libera"),
    ("reservas", "reservas"), ("bitácora", "bitacora"), ("administradoras", "administradoras"),
    ("agrega administradora 777 123 4567", "agrega_admin"), ("quita administradora 777 123 4567", "quita_admin"),
    ("silencia los reportes", "silencia"), ("pausa los reportes", "silencia"), ("activa los reportes", "activa_reportes"),
    ("deshaz", "deshaz"), ("deshaz eso", "deshaz"),
    # erratas: se corrigen
    ("pendietes", "pendientes"), ("estdo", "estado"), ("/calendaro", "calendario"),
    # plática normal con la dueña: nada
    ("hola", None), ("ok gracias", None), ("Ya llegaron", None), ("Ya rentaron la finca", None),
    ("esta bien", None), ("precio?", None),
])
def test_lee_las_ordenes_como_las_escribe_una_persona(texto, orden):
    assert (ordenes.leer(texto) or {}).get("orden") == orden


def test_los_datos_de_la_orden():
    assert ordenes.leer("cerró 1234 15000") == {"orden": "cerro", "ref": "1234", "monto": "15000"}
    assert ordenes.leer("cerro 777 123 4567 15 mil")["ref"] == "7771234567"  # un teléfono en grupos
    assert ordenes.leer("+52 1 777-123-4567")["ref"] == "5217771234567"
    assert ordenes.leer("aprueba 1 3 y 5")["lista"] == [1, 3, 5]
    assert ordenes.leer("aprueba todos")["lista"] == "todos"
    # Lo que se le dice al cliente y lo que queda en la ficha van con SUS palabras (acentos, cifras).
    assert ordenes.leer("Dile a 1234 que ya está apartado ✅")["texto"] == "ya está apartado"
    assert ordenes.leer("nota 1234 15 personas confirmadas")["texto"] == "15 personas confirmadas"
    assert ordenes.leer("Recuerda: la alberca se calienta con 24 h de aviso")["texto"] == \
        "la alberca se calienta con 24 h de aviso"
    assert ordenes.leer("pendientes 2")["pagina"] == 2


def test_dinero_en_centavos():
    assert ordenes.monto_centavos("15000") == ordenes.monto_centavos("15,000") == ordenes.monto_centavos("15.000") \
        == ordenes.monto_centavos("15 mil") == 1_500_000
    assert ordenes.monto_centavos("1.5mil") == 150_000 and ordenes.monto_centavos("950.50") == 95_050
    assert ordenes.monto_centavos("quince") is None and ordenes.monto_centavos("") is None


def test_fechas_como_las_escribe_la_duena():
    hoy = date(2026, 10, 31)
    assert ordenes.fechas_de("del 9 al 11 de noviembre", hoy) == (date(2026, 11, 9), date(2026, 11, 11))
    assert ordenes.fechas_de("9-11 nov", hoy) == (date(2026, 11, 9), date(2026, 11, 11))
    assert ordenes.fechas_de("9/11 al 11/11", hoy) == (date(2026, 11, 9), date(2026, 11, 11))
    assert ordenes.fechas_de("pronto", hoy) is None


def test_parece_orden_no_le_contesta_a_la_platica_normal():
    for normal in ("mañana llega la familia", "esta bien", "sale", "Listo, ya quedo", "ya pagó la señora"):
        assert ordenes.parece_orden(normal) is None, normal
    assert ordenes.parece_orden("pendints") == "pendientes"
    assert ordenes.parece_orden("/calendaro") == "calendario"


# ------------------------------------------------------------- la mesa
def test_una_errata_lee_pero_no_cambia(con_mesa):
    rondas.cargar(con_mesa, _ronda())
    assert "Quiso decir" in _orden(con_mesa, "apruebe la ronda")  # se lee "apruebo la ronda": se pregunta
    assert not agente.aprobadas(con_mesa)
    assert _orden(con_mesa, "pendietes").startswith("Pendientes")  # leer, sí


def test_lo_que_cambia_solo_lo_ordena_quien_aprueba(con_mesa):
    cambian = [o for o in ordenes.TABLA if o.quien == ordenes.QUIEN_APRUEBA]
    assert len(cambian) >= 15
    for texto in ("no le escribas a 0007", "cerró 0007 15000", "aparta finca del 9 al 11 de noviembre de 2027",
                  "dile a 0007 que hola", "máximo 10 al día", "agrega administradora 777 999 8888"):
        assert "solo lo puede ordenar" in _orden(con_mesa, texto, de=OTRA), texto
    assert not con_mesa.leer_lineas(capacidades.MARCAS) and not con_mesa.leer_lineas(capacidades.RESERVAS)
    assert _orden(con_mesa, "pendientes", de=OTRA).startswith("Pendientes")  # leer lo puede cualquiera


def test_no_entendi_solo_cuando_parece_orden(con_mesa):
    assert _orden(con_mesa, "Oye, mañana llega la familia") is None
    assert _orden(con_mesa, "/pendints").startswith("Pendientes")  # la errata se corrige y se lee
    assert "Quiso decir" in _orden(con_mesa, "/pendints de la semana")  # no encaja: se sugiere


@pytest.mark.parametrize("texto", [o.ayuda.split(":")[0].split(" · ")[0].replace("…", "") for o in ordenes.TABLA
                                   if o.quien == ordenes.TODAS and not o.cambia])
def test_cada_orden_de_lectura_contesta_sin_tronar(con_mesa, texto):
    r = _orden(con_mesa, texto)
    assert r and "No pude con esa orden" not in r, (texto, r)


def test_listas_numeradas_y_ficha(con_mesa):
    r = _orden(con_mesa, "pendientes")
    assert "1) …" in r
    ficha = _orden(con_mesa, "ficha 1")
    assert ficha.startswith("Cliente …") and "Fechas: del 09/11" in ficha
    assert "Lo último que dijo" in _orden(con_mesa, f"ficha {HILO[-4:]}")
    assert "No encontré" in _orden(con_mesa, "ficha 9876")
    assert "no hay un 7" in _orden(con_mesa, "ficha 7")
    assert "Cliente:" in _orden(con_mesa, "historial 1")
    assert "boda" in _orden(con_mesa, "busca bodas") or "Nadie" in _orden(con_mesa, "busca bodas")
    assert "1) …4321" in _orden(con_mesa, "busca boda")


def test_una_lista_de_otra_administradora_no_cambia_la_mia(con_mesa):
    _orden(con_mesa, "busca boda")                  # la dueña: 1 = …4321
    _orden(con_mesa, "busca quinta", de=OTRA)       # la otra: 1 = el de la quinta
    assert "…4321" in _orden(con_mesa, "ficha 1")


# ------------------------------------------------------- marcas y candados
def test_no_le_escribas_detiene_canal_y_rondas_y_se_deshace(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    assert "no le llega" in _orden(con_mesa, f"no le escribas a {HILO[-4:]}")
    _, descartadas = rondas.validar(con_mesa, _ronda())
    assert descartadas and descartadas[0]["motivo"] == capacidades.NO_SE_LE_ESCRIBE
    s = agente.Salida(cliente_id=con_mesa.cliente_id, hilo=HILO, responde_a="wamid.E3", via="regla", texto="Hola")
    assert canal.motivo_para_no_enviar(con_mesa, s) == capacidades.NO_SE_LE_ESCRIBE
    assert "Listo" in _orden(con_mesa, "deshaz")
    assert canal.motivo_para_no_enviar(con_mesa, s) == ""
    assert not rondas.validar(con_mesa, _ronda())[1]


def test_lo_llevo_yo_calla_al_equipo_pero_no_a_ella(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, "enciende el envío")
    _orden(con_mesa, f"lo llevo {HILO[-4:]}")
    s = agente.Salida(cliente_id=con_mesa.cliente_id, hilo=HILO, responde_a="wamid.E3", via="ronda", texto="Hola")
    assert canal.motivo_para_no_enviar(con_mesa, s) == capacidades.LO_LLEVA
    _orden(con_mesa, f"dile a {HILO[-4:]} que el 9 sí está libre, son $5,000")
    r = _orden(con_mesa, "sí, mándalo")
    assert "Va en la cola" in r  # sus palabras, con cifra: la puso una persona
    dictada = [x for x in agente.salidas(con_mesa) if x.via == "mesa"][-1]
    assert dictada.texto == "el 9 sí está libre, son $5,000" and dictada.aprobada_por == "Dueña de muestra"
    assert dictada.id in enviador.pendientes(con_mesa)
    assert "(lo lleva usted)" in _orden(con_mesa, "pendientes") or "No hay" in _orden(con_mesa, "pendientes")
    _orden(con_mesa, f"suelta {HILO[-4:]}")
    assert canal.motivo_para_no_enviar(con_mesa, s) == ""


def test_dile_en_pausa_queda_aprobado_y_sale_al_encender(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    _orden(con_mesa, f"dile a {HILO[-4:]} que con gusto")
    r = _orden(con_mesa, "sí, mándalo")
    assert "no sale por ahora" in r and "enciende el envío" in r
    assert not enviador.pendientes(con_mesa)
    assert "Ya van a la cola 1" in _orden(con_mesa, "enciende el envío")


def test_atendido_sale_de_pendientes_hasta_que_vuelva_a_escribir(con_mesa):
    _orden(con_mesa, f"ya le contesté a {HILO[-4:]}")
    assert f"…{HILO[-4:]}" not in _orden(con_mesa, "pendientes")
    historial.guardar(con_mesa, [_m("wamid.E9", "¿Siguen ahí?", ts=int(time.time()) + 60)])  # vuelve a escribir
    assert f"…{HILO[-4:]}" in _orden(con_mesa, "pendientes")


def test_borradores_numerados_aprobar_y_descartar(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    rondas.cargar(con_mesa, _ronda())
    assert "Primero escriba borradores" in _orden(con_mesa, "aprueba 1")
    lista = _orden(con_mesa, "borradores")
    assert "1) …" in lista and "Esperan su sí (1)" in lista
    assert "no hay 4" in _orden(con_mesa, "aprueba 4")
    assert "Descarté 1" in _orden(con_mesa, "descarta 1")
    assert "No hay nada esperando" in _orden(con_mesa, "borradores")
    salida = agente.salidas(con_mesa)[-1]
    assert canal.motivo_para_no_enviar(con_mesa, salida) == capacidades.DESCARTADA  # el canal lo sabe
    assert "Regresé 1" in _orden(con_mesa, "deshaz")
    _orden(con_mesa, "borradores")
    assert "Aprobé 1 mensaje a su nombre" in _orden(con_mesa, "aprueba 1")
    assert "no se puede deshacer" in _orden(con_mesa, "deshaz")


def test_descarta_la_ronda_y_el_detalle(con_mesa):
    rondas.cargar(con_mesa, _ronda())
    assert "Descarté 1 mensaje de la ronda prueba-1" in _orden(con_mesa, "descarta la ronda")
    assert "Aprobé 0" in _orden(con_mesa, "aprueba la ronda")  # lo descartado no se aprueba
    assert "descartados 1" in _orden(con_mesa, "ronda prueba-1")
    assert "prueba-1" in _orden(con_mesa, "rondas")


def test_cerro_asienta_en_centavos_y_reservas_del_mes(con_mesa):
    assert "$15,000" in _orden(con_mesa, f"cerró {HILO[-4:]} 15 mil")
    assert con_mesa.leer_lineas(capacidades.RESERVAS)[-1]["monto_centavos"] == 1_500_000
    assert "1" in _orden(con_mesa, "reservas") and "$15,000" in _orden(con_mesa, "reservas")
    assert "Rentó" in _orden(con_mesa, f"ficha {HILO[-4:]}")
    _orden(con_mesa, "deshaz")
    assert "no hay rentas" in _orden(con_mesa, "reservas")


def test_nota_queda_en_la_ficha_con_sus_palabras(con_mesa):
    _orden(con_mesa, f"nota {HILO[-4:]} Pagará el anticipo el viernes")
    assert "Pagará el anticipo el viernes" in _orden(con_mesa, f"ficha {HILO[-4:]}")
    assert "Pagará" in _orden(con_mesa, "notas")


# ----------------------------------------------------------- calendario
def test_aparta_a_mano_bloquea_la_cotizacion_al_enviar_y_se_libera(con_mesa):
    cot = {"propiedad": "finca", "llegada": "2027-11-09", "salida": "2027-11-11"}
    assert calendario.apartada(con_mesa, cot) == ""
    r = _orden(con_mesa, "aparta finca del 9 al 11 de noviembre de 2027")
    assert r.startswith("Apartado: finca")
    assert "finca" in calendario.apartada(con_mesa, cot)  # el canal lo revisa justo antes de mandar (LXIII)
    assert "OCUPADA" in _orden(con_mesa, "libre finca del 10 al 12 de noviembre de 2027")
    assert not calendario.Ocupacion.de(con_mesa).configurada  # lo apartado a mano no inventa un calendario
    assert "Liberé 1" in _orden(con_mesa, "libera finca del 9 al 11 de noviembre de 2027")
    assert calendario.apartada(con_mesa, cot) == ""
    _orden(con_mesa, "deshaz")
    assert "finca" in calendario.apartada(con_mesa, cot)


def test_aparta_sin_fechas_o_sin_propiedad_pregunta(con_mesa):
    assert "¿Cuál propiedad?" in _orden(con_mesa, "aparta del 9 al 11 de noviembre de 2027")
    assert not capacidades.apartados_a_mano(con_mesa)


# ------------------------------------------------------------ precios
def test_cotiza_para_la_duena_con_la_lista_aprobada(con_mesa):
    r = _orden(con_mesa, "cotiza 8 personas quinta del 9 al 11 de noviembre de 2027")
    assert r.startswith("Para 8 personas") and "$" in r and "Calendario quinta" in r
    assert "Es para usted" in r
    assert "falta" in _orden(con_mesa, "cotiza 8 personas").lower() or "$" in _orden(con_mesa, "cotiza 8 personas")


def test_precios_perfil_y_aprobar_una_version_se_deshace(con_mesa):
    assert "Lista activa (versión 1)" in _orden(con_mesa, "precios")
    assert "quinta" in _orden(con_mesa, "precios quinta").lower()
    n, _ = perfil.proponer(con_mesa, perfil.activo(con_mesa), autor="prueba", nombre="v2")
    assert f"versión {n}" in _orden(con_mesa, "propuestas")
    assert f"Versión {n} activa" in _orden(con_mesa, "aprueba la versión")
    assert perfil.version_activa(con_mesa) == n
    assert "Regresé a la versión 1" in _orden(con_mesa, "deshaz")
    assert perfil.version_activa(con_mesa) == 1


def test_recuerda_no_se_activa_solo(con_mesa):
    antes = perfil.activo(con_mesa)
    assert "No cambia lo que el agente contesta" in _orden(con_mesa, "recuerda: la alberca se calienta con 24 h")
    assert perfil.activo(con_mesa) == antes
    assert "1 reglas suyas" in _orden(con_mesa, "propuestas")


# ------------------------------------------------------------- envío y mesa
def test_tope_no_pasa_el_techo_y_se_deshace(con_mesa):
    assert "hasta 50" in _orden(con_mesa, "máximo 50 al día")
    assert enviador.Ritmo.de(con_mesa).tope_dia == 50
    _orden(con_mesa, "máximo 500 al día")
    assert enviador.Ritmo.de(con_mesa).tope_dia == enviador.TOPE_DIA
    _orden(con_mesa, "deshaz")
    assert enviador.Ritmo.de(con_mesa).tope_dia == 50


def test_una_pausa_no_se_levanta_con_deshaz(con_mesa):
    vinculado.publicar(con_mesa, "conectado")
    rondas.cargar(con_mesa, _ronda())
    _orden(con_mesa, "enciende el envío")
    _orden(con_mesa, "pausa")
    assert con_mesa.config()["encendido"] == "sombra"
    assert "enciende el envío" in _orden(con_mesa, "deshaz")
    assert con_mesa.config()["encendido"] == "sombra"


def test_administradoras_y_reportes(con_mesa):
    assert "ya puede escribirle" in _orden(con_mesa, "agrega administradora 777 999 8888")
    assert mesa.es_admin(con_mesa, "5217779998888")
    assert "no se le quita" in _orden(con_mesa, "quita administradora 52 1 000 000 0000".replace("52 1 000 000 0000", "000 000 0000"))
    _orden(con_mesa, "quita administradora 777 999 8888")
    assert not mesa.es_admin(con_mesa, "5217779998888")
    _orden(con_mesa, "silencia los reportes", de=OTRA)
    from datetime import datetime, timezone
    n = mesa.reporte_si_toca(con_mesa, datetime(2026, 10, 30, 16, 0, tzinfo=timezone.utc))  # 10:00 en México
    assert n == 1 and all(e["para"] != OTRA for e in con_mesa.leer_lineas(mesa.SALIDA)
                          if e["texto"].startswith("Reporte"))
    assert "sin reportes" in _orden(con_mesa, "administradoras")


def test_una_orden_que_truena_no_tumba_al_lector(con_mesa, monkeypatch):
    monkeypatch.setitem(capacidades.MANEJADORES, "estado", lambda p: 1 / 0)
    assert "No pude con esa orden" in _orden(con_mesa, "estado")
    assert con_mesa.leer_lineas(mesa.BITACORA)[-1]["orden"] == "error:estado"


# ------------------------------------------------- la mesa por fuera de WhatsApp
def test_la_mesa_por_http_solo_lee_sin_de_verdad_y_solo_con_la_maestra(con_mesa):
    from agente.app import app
    from agente.espacio import llave_de
    from fastapi.testclient import TestClient
    http, base = TestClient(app), f"/espacios/{con_mesa.cliente_id}"
    maestra, del_cliente = {"llave": "secreto-de-prueba"}, {"llave": llave_de(con_mesa.cliente_id)}
    tabla = http.get(f"{base}/mesa/ordenes.json", params=del_cliente).json()["ordenes"]
    assert len(tabla) == len(ordenes.TABLA) and {"id", "ayuda", "quien", "cambia"} <= set(tabla[0])
    assert http.post(f"{base}/mesa", params=del_cliente, json={"texto": "pendientes"}).status_code == 404
    r = http.post(f"{base}/mesa", params=maestra, json={"texto": "pendientes"}).json()
    assert r["orden"] == "pendientes" and r["respuesta"].startswith("Pendientes")
    r = http.post(f"{base}/mesa", params=maestra, json={"texto": f"no le escribas a {HILO[-4:]}"}).json()
    assert "solo lee" in r["respuesta"] and not capacidades.marcas(con_mesa)
    r = http.post(f"{base}/mesa", params=maestra, json={"texto": f"no le escribas a {HILO[-4:]}", "de_verdad": True}).json()
    assert "no le llega" in r["respuesta"] and capacidades.no_escribir(con_mesa, HILO)
    assert con_mesa.leer_lineas(mesa.BITACORA)[-1]["orden"] == "no_escribir (http)"
    assert "No es una orden" in http.post(f"{base}/mesa", params=maestra, json={"texto": "hola"}).json()["respuesta"]


def test_la_mesa_desde_el_taller(con_mesa, monkeypatch, capsys):
    import json as json_

    from agente import local
    pedidos = []

    def pedir(metodo, ruta, cuerpo=None, **_):
        pedidos.append((metodo, ruta, cuerpo))
        return json_.dumps(mesa.por_fuera(con_mesa, cuerpo["texto"], solo_lectura=not cuerpo["de_verdad"],
                                          via="taller")).encode()
    monkeypatch.setattr(local, "_pedir", pedir)
    assert local.main(["mesa", con_mesa.cliente_id, "borradores"]) == 0
    assert "No hay nada esperando" in capsys.readouterr().out
    local.main(["mesa", con_mesa.cliente_id, "pausa el envío"])
    assert "solo lee" in capsys.readouterr().out
    local.main(["mesa", con_mesa.cliente_id, "pausa el envío", "--de-verdad"])
    assert "pausa" in capsys.readouterr().out.lower() and pedidos[-1][2]["de_verdad"] is True


def test_el_mcp_pregunta_a_la_mesa_y_no_cambia_nada(con_mesa):
    from agente import mcp
    s = mcp.Servidor(con_mesa)
    assert "preguntar_a_la_mesa" in {h["name"] for h in mcp.HERRAMIENTAS}
    r = s.atender({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "preguntar_a_la_mesa", "arguments": {"texto": "pendientes"}}})
    assert "Pendientes" in r["result"]["content"][0]["text"]
    r = s.atender({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                   "params": {"name": "preguntar_a_la_mesa", "arguments": {"texto": f"cerró {HILO[-4:]} 15000"}}})
    assert "solo lee" in r["result"]["content"][0]["text"] and not con_mesa.leer_lineas(capacidades.RESERVAS)


def test_el_enjambre_no_recibe_a_quien_la_duena_aparto_y_lleva_sus_notas(con_mesa, monkeypatch):
    import json as json_

    from agente import local
    monkeypatch.setattr(local, "_espacio", lambda _id: con_mesa)
    _orden(con_mesa, f"nota {HILO[-4:]} Prefiere que le hablen por la tarde")
    _, escritos = local.lotes(con_mesa.cliente_id, dias=100_000)
    platicas = [p for r in escritos for p in json_.loads(r.read_text(encoding="utf-8"))["platicas"]]
    assert next(p for p in platicas if p["hilo"] == HILO)["notas_de_la_duena"] == ["Prefiere que le hablen por la tarde"]
    _orden(con_mesa, "no le escribas a 4321")
    _orden(con_mesa, f"lo llevo {HILO[-4:]}")
    resumen, escritos = local.lotes(con_mesa.cliente_id, dias=100_000)
    assert resumen["fuera_por_la_duena"] == 2
    assert not any(p["hilo"] in (HILO, "5210000004321") for r in escritos
                   for p in json_.loads(r.read_text(encoding="utf-8"))["platicas"])


def test_la_novedad_va_una_sola_vez_en_el_reporte(con_mesa):
    from datetime import datetime, timezone
    mesa.reporte_si_toca(con_mesa, datetime(2026, 10, 30, 16, 0, tzinfo=timezone.utc))   # 10:00
    mesa.reporte_si_toca(con_mesa, datetime(2026, 10, 31, 2, 0, tzinfo=timezone.utc))    # 20:00
    reportes = [e["texto"] for e in con_mesa.leer_lineas(mesa.SALIDA) if e["para"] == DUENA]
    assert len(reportes) == 2 and mesa.NOVEDAD[1] in reportes[0] and mesa.NOVEDAD[1] not in reportes[1]
    for orden in ("contestaron", "ficha 1234", "huecos", "borradores", "deshaz"):  # lo que anuncia, se entiende
        assert ordenes.leer(orden), orden
