"""Lo exportado de Gestor Morelos: cada caso es una frase que allá salió mal una vez."""
from __future__ import annotations

import pytest
from agente import agente, conversacion
from agente.historial import Mensaje
from conftest import ModeloFalso, entrante


@pytest.mark.parametrize("texto", [
    "Ok gracias", "Muchas gracias por la información", "Va, lo platico con mi esposa y le aviso",
    "Bueno gracias", "Gracias a usted", "👍", "Ok, mañana le mando la foto", "Lo pienso y te aviso",
    "Muy amable", "Quedo al pendiente", "Aún estoy evaluando", "Ok\nlo reviso", "Saludos, bendiciones",
])
def test_conv_acuses_no_piden_nada(texto):
    assert conversacion.nada_que_contestar(texto)


@pytest.mark.parametrize("texto", [
    "Hola", "Hola buenas tardes",                # el saludo solo sí pide respuesta
    "Ok, y cuánto sale el fin de semana?",       # sigue pidiendo
    "Gracias, somos 25 personas",                # trae un dato
    "Si",                                        # puede contestar una pregunta del negocio
    "Lo pienso, ¿tienen alberca?",
])
def test_conv_lo_que_si_pide_respuesta(texto):
    assert not conversacion.nada_que_contestar(texto, con_si=False)


@pytest.mark.parametrize("texto, esperado", [
    ("quiero mi dinero de vuelta", True), ("me cobraron de más el depósito", True),
    ("son unos rateros", True), ("ya contesten pendejos", True),
    ("vergüenza no mames que bonito lugar", False), ("es para uso personal", False),
])
def test_conv_reclamo(texto, esperado):
    assert conversacion.es_reclamo(texto) is esperado


def test_conv_eres_bot_va_antes_que_pedir_persona():
    assert conversacion.pregunta_si_es_bot("eres humano?") and conversacion.pide_persona("eres humano?")
    assert conversacion.pide_persona("quiero hablar con el encargado")
    assert not conversacion.pide_persona("es para uso personal")


@pytest.mark.parametrize("texto, esperado", [
    ("Gracias, ya rentamos en otro lado", True), ("Ya reservé en otra, gracias", True),
    ("Ya encontramos, gracias", True), ("Ya apartamos, ¿cuánto es el depósito?", False),
    ("Gracias, nos decidimos por otro lugar en hidalgo 😊", True), ("muchas gracias, sera en otra ocasion", True),
    ("Nos decidimos por otra fecha, tienen el 14?", False),
    ("No me interesa", True), ("Está muy caro, gracias", True), ("Número equivocado", True),
    ("Ya no, gracias", True), ("Ya reservé, ¿cuánto es el depósito?", False),
])
def test_conv_cierre(texto, esperado):
    assert conversacion.es_cierre(texto) is esperado


def test_conv_rafaga_junta_lo_del_cliente_y_para_en_el_negocio():
    m = [Mensaje("1", "h", False, 0, "text", "Hola"), Mensaje("2", "h", True, 10, "text", "Buenas, dígame"),
         Mensaje("3", "h", False, 20, "text", "Para el 14"), Mensaje("4", "h", False, 30, "text", "Para el 14"),
         Mensaje("5", "h", False, 40, "text", "[sticker]"), Mensaje("6", "h", False, 50, "text", "somos 20")]
    assert conversacion.rafaga(m) == "Para el 14\nsomos 20"
    lejos = m[:3] + [Mensaje("7", "h", False, 20 + 3600, "text", "sigue en pie?")]
    assert conversacion.rafaga(lejos) == "sigue en pie?"


@pytest.mark.parametrize("textos, senal", [
    ([], "silencio"), (["Va, lo apartamos"], "acepta"), (["Ok"], "tibio"),
    (["Ok lo platico y le aviso"], "respondio"), (["Está muy caro, gracias"], "cierra"),
    (["A qué cuenta le deposito?"], "acepta"),
])
def test_conv_el_ok_que_aplaza_no_es_si(textos, senal):
    assert conversacion.senal_tras_la_cotizacion(textos) == senal


# --- En el turno del agente ---------------------------------------------------- #
def test_conv_el_acuse_calla_sin_llamar_al_modelo(espacio):
    falso = ModeloFalso("No debió llamarse [[META persona=no]]")
    s = agente.decidir(espacio, entrante("Ok muchas gracias, lo platico y le aviso"), falso)
    assert s.via == "silencio" and s.texto == "" and falso.llamadas == []


def test_conv_reclamo_y_persona_van_a_una_persona_sin_modelo(espacio):
    falso = ModeloFalso()
    assert "reclamo" in agente.decidir(espacio, entrante("Me cobraron de más el depósito"), falso).motivo
    assert "persona" in agente.decidir(espacio, entrante("quiero hablar con el encargado"), falso).motivo
    assert falso.llamadas == []


def test_conv_eres_bot_se_contesta_con_la_verdad(espacio):
    s = agente.decidir(espacio, entrante("Estoy hablando con un bot?"), ModeloFalso())
    assert s.via == "regla" and "asistente automático" in s.texto and "persona" in s.texto
    assert not agente.voz.hallazgos(s.texto, agente.perfil.activo(espacio))


def test_conv_en_vivo_no_habla_encima_de_una_persona(espacio):
    from agente import historial
    hilo = "5210000000001"
    ultimo = max(m.ts for m in historial.hilos(espacio)[hilo])
    nuevo = entrante("¿Y tienen alberca?", hilo=hilo, ts=ultimo + 600, ident="wamid.ENCIMA")
    falso = ModeloFalso("Sí, la finca tiene alberca. [[META persona=no]]")
    assert agente.decidir(espacio, nuevo, falso, en_vivo=True).via == "silencio"
    assert agente.decidir(espacio, nuevo, falso, en_vivo=False).via == "modelo"  # la sombra sí mide


def test_conv_silencio_no_se_envia(espacio, monkeypatch):
    from agente import canal
    monkeypatch.setenv("WHATSAPP_TOKEN", "t")
    config = espacio.config()
    config.update(phone_number_id="1", encendido="sin_cifra")
    espacio.escribir_json("config.json", config)
    s = agente.decidir(espacio, entrante("Ok gracias"))
    assert "calla" in canal.motivo_para_no_enviar(espacio, s)


# --- El banco (pass^k y red team) --------------------------------------------- #
def test_conv_banco_pasa_k_sin_errores_caros(espacio):
    from agente import banco
    r = banco.correr(espacio)
    assert r["errores_caros"] == 0, r["fallan"]
    assert r["pasa_k"] == 1.0, [(f["id"], {v: c["fallas"] for v, c in f["corridas"].items() if c["fallas"]})
                                for f in r["fallan"]]
    assert {"red_team", "callar", "persona", "guardada"} <= set(r["por_flujo"])
    assert not espacio.leer_lineas("salidas.jsonl")  # corre en una copia: no toca el espacio


def test_conv_banco_detecta_un_candado_roto(espacio, monkeypatch):
    from agente import banco, guardia
    monkeypatch.setattr(guardia, "cifras_no_permitidas", lambda *a, **k: [])
    # rt_cifra ya no llega al modelo (es una orden al asistente: va a una persona antes);
    # éste sí llega, y con el candado roto su cifra tiene que verse como error caro.
    r = banco.correr(espacio, [c for c in banco.CASOS if c.id == "rt_otro_asesor"])
    assert r["errores_caros"] == 1


@pytest.mark.parametrize("texto, prohibido", [
    ("Se la dejo en seis mil", True), ("Son dos noches mínimo", True), ("Mil gracias a usted", False),
    ("Con gusto, una persona le confirma", False),
])
def test_conv_la_cifra_con_letra_tambien_es_cifra(texto, prohibido):
    from agente import guardia
    assert bool(guardia.cifras_no_permitidas(texto)) is prohibido


def test_conv_banco_sin_perfil(tmp_path):
    from agente import banco
    from agente.espacio import Espacio
    assert banco.correr(Espacio("vacio", tmp_path))["n"] == 0


@pytest.mark.parametrize("texto", [
    "Sería para el próximo año en el mes de Julio, Bodas de Oro para 100 persona",
    "Es un grupo de  aprox 45 persona", "Por persona o por noche perdón", "Entre 50 a 60 persona",
    "Respecto de la comida ya sería tu mejor costo por / Persona ?", "Es para una persona"])
def test_conv_persona_de_conteo_no_pide_una_persona(texto):
    """Finca Emiliano, 2026-10-27: 11 de 11 disparos de `pide_persona` en su
    historial eran la cuenta de huéspedes; el turno los mandaba a una persona."""
    assert not conversacion.pide_persona(texto)


@pytest.mark.parametrize("texto", ["Quiero hablar con una persona", "Me atiende alguna persona real?",
                                   "Pásame con el encargado", "Quiero hablar con un humano"])
def test_conv_pedir_una_persona_sigue_siendo_pedirla(texto):
    assert conversacion.pide_persona(texto)


def test_conv_el_redactor_sabe_lo_que_revisa_el_candado_de_voz(espacio):
    """Cada rasgo que `voz.hallazgos` castiga se le dice al modelo en el `system`
    (enjambre, 2026-10-27: 9 de 60 borradores se perdían por abrir con ¿)."""
    from agente import modelo, perfil, voz

    activo = dict(perfil.activo(espacio), voz=[{"frase": "Buenas tardes, para que fecha seria"}], trato="usted")
    texto = "".join(b["text"] for b in modelo.system_de(espacio, activo))
    assert "No uses ¿ ni ¡" in texto and "Sin emojis" in texto and "Trato de usted" in texto
    assert voz.hallazgos("¿Para qué fecha?", activo)                     # y el candado lo sigue revisando
    con_signos = dict(activo, voz=[{"frase": "¡Hola! ¿Qué fecha? 😊"}])
    assert "No uses ¿ ni ¡" not in voz.reglas_para_redactar(con_signos)


def test_conv_estoy_pendiente_de_mi_presupuesto_no_se_calla():
    """Finca Emiliano, 2026-10-27: el turno lo leía como "quedo pendiente" y callaba."""
    assert not conversacion.nada_que_contestar("Estoy pendiente de mi presupuesto por favor", con_si=False)
    # Corrida GM, 2026-10-29: "quedo pendiente de SU respuesta" espera algo nuestro (las tres revisiones
    # adversariales lo marcaron como pedido); la dirección segura es contestarle. "Quedo al pendiente" solo sigue
    # siendo acuse.
    assert not conversacion.nada_que_contestar("Quedo pendiente de su respuesta", con_si=False)
    assert conversacion.nada_que_contestar("Quedo al pendiente", con_si=False)


@pytest.mark.parametrize("texto", ["Deja le pregunto a mi marido", "Ok deja le comento a mi esposo entonces",
                                   "Deja les comento entonces"])
def test_conv_el_cliente_lo_consulta_con_su_gente(texto):
    assert conversacion.nada_que_contestar(texto, con_si=False)


def test_conv_banco_con_los_casos_reales_pasa_k(espacio):
    from agente import banco

    r = banco.correr(espacio, banco.CASOS_REALES)
    assert r["errores_caros"] == 0, [f["caros"] for f in r["filas"] if f["caros"]]
    assert r["pasa_k"] == 1.0, [(f["id"], [c["fallas"] for c in f["corridas"].values()]) for f in r["fallan"]]
