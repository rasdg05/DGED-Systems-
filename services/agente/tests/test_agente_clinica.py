"""El giro de servicios (clínica estética de muestra): precio por tratamiento, salud a la especialista, demo sembrada."""
from __future__ import annotations

import json

import pytest
from agente import agente, alta, guardia, historial, muestra, perfil, servicios
from agente.espacio import Espacio
from conftest import MUESTRA, entrante

CLINICA = MUESTRA / "clinica"


def _leer(nombre: str):
    return json.loads((CLINICA / nombre).read_text(encoding="utf-8"))


@pytest.fixture()
def clinica(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("TENANT_INTERNAL_TOKEN", "secreto-de-prueba")
    monkeypatch.setenv("AGENTE_DATOS", str(tmp_path))
    espacio = Espacio("clinica-muestra", tmp_path)
    alta.registrar(espacio, _leer("alta.json"))
    historial.guardar(espacio, historial.de_webhook(_leer("historial_webhook.json")))
    n, descartados = perfil.proponer(espacio, _leer("perfil_grabado.json"), autor="muestra", nombre="muestra")
    perfil.aprobar(espacio, n, aprobador="Doctora de muestra")
    espacio.descartados = descartados
    return espacio


def _decide(espacio, texto, hilo="5210000009998", ident="wamid.CLIPRUEBA"):
    return agente.decidir(espacio, entrante(texto, hilo=hilo, ident=ident))


def test_los_renglones_malos_de_la_muestra_caen(clinica):
    motivos = {d["motivo"] for d in clinica.descartados}
    assert len(clinica.descartados) == 2
    assert any("cifra que no está en la cita" in m for m in motivos)       # el peeling inventado
    assert any("del cliente final" in m for m in motivos)                  # "Perfecto" no es voz de la casa
    assert not any(r.get("servicio") == "peeling" for r in perfil.activo(clinica)["reglas"])


def test_precio_de_un_tratamiento_lo_pone_el_cotizador_y_espera_aprobacion(clinica):
    s = _decide(clinica, "Hola cuánto cuesta la limpieza facial?")
    assert s.via == "cotizador" and s.requiere_aprobacion
    assert "Limpieza facial profunda por sesión: $850." in s.texto
    assert "paquete de 4 sesiones: $3,000." in s.texto
    assert "anticipo de $200" in s.texto
    assert "valoración" not in s.texto  # la valoración es de los inyectables


def test_botox_trae_zona_paquete_y_valoracion(clinica):
    s = _decide(clinica, "Precio del botox de frente?")
    assert s.via == "cotizador"
    assert "Botox por zona: $3,500." in s.texto and "Botox, 3 zonas: $8,500." in s.texto
    assert "valoración con la especialista ($300, se abona a su tratamiento)" in s.texto


def test_cada_cifra_del_texto_salio_de_una_regla_aprobada(clinica):
    activo = perfil.activo(clinica)
    permitidas = {str(r["monto_centavos"] // 100) for r in activo["reglas"] if r.get("monto_centavos")}
    permitidas |= {str(r[k]) for r in activo["reglas"] for k in ("sesiones", "zonas") if r.get(k)}
    for texto in ("cuanto la limpieza facial", "precio botox", "costo de axila", "cuanto piernas completas",
                  "precio del hidrofacial"):
        s = _decide(clinica, texto)
        assert s.via == "cotizador", texto
        assert not guardia.cifras_no_permitidas(s.texto, permitidas), (texto, s.texto)


def test_alias_largo_gana_al_corto():
    activo = {"reglas": _leer("perfil_grabado.json")["reglas"]}
    assert servicios.servicios_en(activo, "laser de piernas completas") == ["laser_piernas"]
    assert servicios.servicios_en(activo, "limpieza facial y botox") == ["limpieza_facial", "botox"]
    assert servicios.servicios_en(activo, "hola buenas") == []


def test_sin_decir_cual_se_pregunta_sin_cifra(clinica):
    s = _decide(clinica, "Me pasa sus precios?")
    assert s.via == "cotizador" and s.texto == agente.PIDE_SERVICIO
    assert not s.requiere_aprobacion and not guardia.cifras_no_permitidas(s.texto)


def test_el_tratamiento_dicho_antes_en_la_platica_cuenta(clinica):
    hilo = "5210000009997"
    historial.guardar(clinica, [historial.Mensaje(id="wamid.CLIA", hilo=hilo, del_negocio=False, ts=1789999000,
                                                  tipo="text", texto="Me interesa el hidrofacial")])
    s = _decide(clinica, "y cuánto cuesta?", hilo=hilo)
    assert s.via == "cotizador" and "Hidrofacial por sesión: $1,200." in s.texto


@pytest.mark.parametrize("texto", [
    "Estoy embarazada, puedo hacerme el facial?",
    "tomo anticoagulantes, me puedo aplicar botox?",
    "Me quedó la cara roja después del peeling",
    "Soy alérgica a la lidocaína",
    "Estoy lactando, cuánto cuesta el botox?",   # aunque pida precio: primero la especialista
    "es seguro el laser si tengo diabetes?",
])
def test_una_pregunta_de_salud_va_a_la_especialista(clinica, texto):
    s = _decide(clinica, texto)
    assert s.via == "persona" and "salud" in s.motivo and not s.cotizacion


def test_agendar_lo_confirma_una_persona(clinica):
    s = _decide(clinica, "Quiero agendar una cita para el sábado")
    assert s.via == "persona" and "agendar" in s.motivo


def test_dos_precios_distintos_no_se_promedian(clinica):
    activo = perfil.activo(clinica)
    otra = dict(next(r for r in activo["reglas"] if r.get("servicio") == "hidrofacial"), monto_centavos=99000)
    cot = servicios.cotizar({**activo, "reglas": activo["reglas"] + [otra]}, ["hidrofacial"])
    assert not cot.completa and "dos precios distintos" in cot.texto() and "$" not in cot.texto()


def test_la_finca_no_cambia_de_giro(espacio):
    """El perfil de renta no tiene reglas `servicio`: sigue por su camino."""
    assert not servicios.es_giro_de_servicios(perfil.activo(espacio))
    s = agente.decidir(espacio, entrante("Estoy embarazada, la quinta tiene escaleras?"))
    assert "salud" not in s.motivo


def test_la_demo_se_siembra_una_vez_en_sombra(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("TENANT_INTERNAL_TOKEN", "secreto-de-prueba")
    monkeypatch.setenv("AGENTE_DATOS", str(tmp_path))
    monkeypatch.setenv(muestra.VARIABLE, "clinica")
    monkeypatch.setenv(muestra.VARIABLE_ESPACIO, "clinica-demo")
    r = muestra.sembrar_si_toca()
    assert r["sembrado"] and r["descartados"] == 2 and r["salidas"] == 4
    espacio = Espacio("clinica-demo", tmp_path)
    assert espacio.config()["encendido"] == "sombra"
    vias = sorted(s.via for s in agente.salidas(espacio))
    assert vias == ["cotizador", "cotizador", "cotizador", "persona"]
    assert all(s.requiere_aprobacion for s in agente.salidas(espacio) if "$" in s.texto)
    # el segundo arranque no pisa lo que la demo ya movió
    assert muestra.sembrar_si_toca() == {"sembrado": False, "motivo": "el espacio ya existe"}
    assert len(agente.salidas(espacio)) == 4


def test_sin_variables_no_siembra_y_una_muestra_que_no_existe_no_tumba(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTE_DATOS", str(tmp_path))
    monkeypatch.delenv(muestra.VARIABLE, raising=False)
    assert muestra.sembrar_si_toca() is None
    monkeypatch.setenv(muestra.VARIABLE, "../muestra")
    monkeypatch.setenv(muestra.VARIABLE_ESPACIO, "clinica-demo")
    assert muestra.sembrar_si_toca()["sembrado"] is False


def test_la_muestra_en_git_es_la_que_genera_el_script():
    import importlib.util

    spec = importlib.util.spec_from_file_location("gen_clinica", CLINICA / "generar_muestra.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    assert _leer("historial_webhook.json") == gen.historial()
    assert _leer("alta.json") == gen.ALTA
    assert _leer("perfil_grabado.json") == gen.PERFIL
