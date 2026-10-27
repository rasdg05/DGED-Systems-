"""Las pantallas: abren con la llave, enmascaran teléfonos y escapan lo del cliente."""
from __future__ import annotations

import pytest
from agente import historial
from agente.app import app
from fastapi.testclient import TestClient

LLAVE = {"llave": "secreto-de-prueba"}


@pytest.fixture()
def http(espacio):
    return TestClient(app)


@pytest.mark.parametrize("ruta", ["", "/alta", "/vincular", "/conversaciones", "/revision", "/banco"])
def test_pag_toda_pantalla_pide_llave(http, espacio, ruta):
    base = f"/espacios/{espacio.cliente_id}{ruta}"
    assert http.get(base).status_code == 401
    r = http.get(base, params=LLAVE)
    assert r.status_code == 200 and '<nav class="tabs">' in r.text and "Finca y Quinta de Muestra" in r.text


def test_pag_inicio_es_para_administrar(http, espacio):
    t = http.get(f"/espacios/{espacio.cliente_id}", params=LLAVE).text
    n = len(historial.cargar(espacio))
    assert f"<b>{n}</b>" in t and "Pendiente" in t and "Su asistente" in t and "Aprendiendo" in t


DE_DESARROLLO = ("pass^k", "Banco", "banco", "simbiosis", "jsonl", "sombra", "Taller", "modelo grande", "Autor:")


@pytest.mark.parametrize("ruta", ["", "/conversaciones", "/revision", "/negocio", "/alta"])
def test_pag_lo_de_desarrollo_no_se_ve_en_lo_del_negocio(http, espacio, ruta):
    """El negocio administra; banco, sombra e historial crudo son nuestros y no tienen pestaña (D-021)."""
    import re

    from agente import perfil
    from conftest import leer_muestra
    perfil.proponer(espacio, leer_muestra("perfil_grabado.json"), autor="t", nombre="otra")
    t = http.get(f"/espacios/{espacio.cliente_id}{ruta}", params=LLAVE).text
    visible = re.sub(r"<style>.*?</style>", "", t, flags=re.S)
    for palabra in DE_DESARROLLO:
        assert palabra not in visible, (ruta, palabra)
    # El taller sigue abriendo por su ruta, para nosotros.
    assert "pass^k" in http.get(f"/espacios/{espacio.cliente_id}/banco", params=LLAVE).text


def test_pag_conversaciones_enmascara_y_escapa(http, espacio):
    historial.guardar(espacio, [historial.Mensaje("x1", "5215551234567", False, 9_999_999_999, "text",
                                                  "<script>alert(1)</script>")])
    lista = http.get(f"/espacios/{espacio.cliente_id}/conversaciones", params=LLAVE).text
    assert "•••• 4567" in lista and "5215551234567</b>" not in lista
    assert "<script>alert(1)</script>" not in lista and "&lt;script&gt;" in lista
    hilo = http.get(f"/espacios/{espacio.cliente_id}/conversaciones", params={**LLAVE, "hilo": "5215551234567"}).text
    assert "&lt;script&gt;" in hilo and "cliente ·" in hilo


def test_pag_banco_se_ve(http, espacio):
    t = http.get(f"/espacios/{espacio.cliente_id}/banco", params=LLAVE).text
    assert "pass^k" in t and "listo para sombra" in t and "rt_cifra" in t


def test_pag_aprobar_con_llave_en_la_url(http, espacio):
    from agente import perfil
    from conftest import leer_muestra
    n, _ = perfil.proponer(espacio, leer_muestra("perfil_grabado.json"), autor="t", nombre="otra")
    r = http.post(f"/espacios/{espacio.cliente_id}/versiones/{n}/aprobar", params=LLAVE,
                  json={"aprobador": "Dueña de muestra"})
    assert r.json() == {"activa": n}


def test_pag_enlace_del_negocio_solo_abre_vincular(http, espacio):
    from agente import vinculado
    from agente.espacio import llave_de_vinculacion
    t = llave_de_vinculacion(espacio.cliente_id)
    assert http.get(f"/v/{espacio.cliente_id}").status_code == 401
    assert http.get(f"/v/{espacio.cliente_id}", params={"t": "otra"}).status_code == 401
    vinculado.publicar(espacio, "esperando_codigo", codigo="AB12-CD34")
    p = http.get(f"/v/{espacio.cliente_id}", params={"t": t}).text
    assert "AB12-CD34" in p and "número de teléfono" in p and "<nav" not in p
    assert "mensajes" not in p.lower() or "envía mensajes" in p  # no enseña cuántos ni cuáles
    # Con la llave del enlace no se abre nada más.
    for ruta in ("", "/conversaciones", "/revision", "/historial.jsonl"):
        assert http.get(f"/espacios/{espacio.cliente_id}{ruta}", params={"llave": t}).status_code == 401
    # Negocio lo ofrece para compartir.
    assert f"/v/{espacio.cliente_id}?t={t}" in http.get(f"/espacios/{espacio.cliente_id}/negocio", params=LLAVE).text


def test_pag_alta_se_guarda_a_medias_y_dice_que_falta(http, tmp_path, monkeypatch):
    from agente.espacio import Espacio
    e = Espacio("finca-nueva", tmp_path)
    r = http.post(f"/espacios/{e.cliente_id}/alta", params=LLAVE,
                  json={"nombre_comercial": "Finca Emiliano", "propiedades": "Finca Emiliano\nQuinta Emiliano",
                        "como_cobra": ""})
    assert r.status_code == 200
    assert "cómo cobra" in r.json()["faltan"] and "quién aprueba" in r.json()["faltan"]
    assert e.leer_json("alta.json")["propiedades"] == ["Finca Emiliano", "Quinta Emiliano"]
    t = http.get(f"/espacios/{e.cliente_id}", params=LLAVE).text
    assert "Falta: giro" in t
    assert http.post(f"/espacios/{e.cliente_id}/alta", params=LLAVE, json={"giro": "x"}).status_code == 422


def test_pag_enlace_del_negocio_no_filtra_nada_en_ningun_estado(http, espacio):
    """En cualquier estado del lector, /v/ no enseña conteos, detalle técnico, número vinculado ni menú."""
    from agente import vinculado
    from agente.espacio import llave_de_vinculacion
    t = llave_de_vinculacion(espacio.cliente_id)
    n = len(historial.cargar(espacio))
    for clave, extra in (("sin_lector", {}), ("arrancando", {}), ("error", {"detalle": "neonize: RuntimeError('x')"}),
                         ("esperando_qr", {"qr": "2@qr-de-prueba"}), ("esperando_codigo", {"codigo": "WXYZ-1234"}),
                         ("vinculado", {"numero": "5215550001111"}), ("conectado", {}),
                         ("numero_ajeno", {"numero": "5215550001111"}), ("desconectado", {})):
        vinculado.publicar(espacio, clave, **extra)
        p = http.get(f"/v/{espacio.cliente_id}", params={"t": t}).text
        assert "<nav" not in p and "neonize" not in p and "5215550001111" not in p, clave
        assert f"<b>{n}</b>" not in p and "mensajes en" not in p and "guardados" not in p, clave
        assert "/espacios/" not in p and "llave=" not in p, clave  # ni un enlace a lo interno
        assert 'http-equiv="refresh"' in p and "data-vivo" in p  # se actualiza sola, con y sin JS


def test_pag_marca_color_y_portada(http, espacio, tmp_path):
    from agente.espacio import llave_de_vinculacion
    base = f"/espacios/{espacio.cliente_id}"
    t = llave_de_vinculacion(espacio.cliente_id)
    # Color: solo #rrggbb; nada más llega al style.
    alta = espacio.leer_json("alta.json")
    assert http.post(f"{base}/alta", params=LLAVE, json={**alta, "color_marca": "red;}body{x"}).status_code == 422
    assert http.post(f"{base}/alta", params=LLAVE, json={**alta, "color_marca": "#2F4A3A"}).status_code == 200
    assert espacio.config()["marca_color"] == "#2f4a3a"
    assert "--marca:#2f4a3a" in http.get(f"/v/{espacio.cliente_id}", params={"t": t}).text
    # Portada: pide llave, se juzga por los bytes y la del negocio solo abre con su enlace.
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    assert http.post(f"{base}/portada", content=png).status_code == 401
    assert http.post(f"{base}/portada", params=LLAVE, content=b"<svg onload=alert(1)>",
                     headers={"Content-Type": "image/png"}).status_code == 422
    assert http.get(f"/v/{espacio.cliente_id}/portada", params={"t": t}).status_code == 404
    assert http.post(f"{base}/portada", params=LLAVE, content=png).json()["portada"] == "png"
    assert http.get(f"/v/{espacio.cliente_id}/portada").status_code == 401
    assert http.get(f"/v/{espacio.cliente_id}/portada", params={"t": "otra"}).status_code == 401
    r = http.get(f"/v/{espacio.cliente_id}/portada", params={"t": t})
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content == png
    assert f"/v/{espacio.cliente_id}/portada?t=" in http.get(f"/v/{espacio.cliente_id}", params={"t": t}).text
    jpg = b"\xff\xd8\xff" + b"0" * 64
    assert http.post(f"{base}/portada", params=LLAVE, content=jpg).json()["portada"] == "jpg"
    assert not espacio.ruta("portada.png").exists()  # una sola portada


def test_pag_chat_ensena_lo_que_contestaria_y_se_aprueba_ahi(http, espacio):
    from agente import agente
    from conftest import ModeloFalso
    entrante = historial.Mensaje("in-cot", "5215559990000", False, 9_999_999_999, "text", "Precio de la quinta")
    historial.guardar(espacio, [entrante])
    s = agente.atender(espacio, entrante, ModeloFalso(
        "Con gusto. [[META cotizar=si propiedad=quinta llegada=2026-11-09 salida=2026-11-11 personas=4 evento=no]]"))
    assert s.requiere_aprobacion
    hilo = http.get(f"/espacios/{espacio.cliente_id}/conversaciones", params={**LLAVE, "hilo": "5215559990000"}).text
    assert "Espera su aprobación" in hilo and "bur borrador" in hilo
    assert "cotización espera su sí" in http.get(f"/espacios/{espacio.cliente_id}", params=LLAVE).text
    r = http.post(f"/espacios/{espacio.cliente_id}/salidas/{s.id}/aprobar", params=LLAVE,
                  json={"aprobador": "Dueña de muestra"})
    assert r.status_code == 200 and r.json()["aprobada"] and not r.json()["enviada"]  # en sombra no sale


def test_pag_marca_se_guarda_aparte(http, espacio):
    base = f"/espacios/{espacio.cliente_id}/marca"
    assert http.post(base, json={"color": "#123456"}).status_code == 401
    assert http.post(base, params=LLAVE, json={"color": "url(x)"}).status_code == 422
    assert http.post(base, params=LLAVE, json={"color": "#ABCDEF"}).json() == {"marca_color": "#abcdef"}


@pytest.mark.parametrize("ruta", ["/banco", "/historial.jsonl"])
def test_pag_el_taller_no_existe_para_el_cliente(http, espacio, ruta):
    """Banco, sombra e historial crudo son de DGED: con la llave del cliente, 404, aunque sepa la URL (D-022)."""
    from agente.espacio import llave_de
    cliente = {"llave": llave_de(espacio.cliente_id)}
    assert http.get(f"/espacios/{espacio.cliente_id}", params=cliente).status_code == 200
    assert http.get(f"/espacios/{espacio.cliente_id}{ruta}", params=cliente).status_code == 404
    assert http.post(f"/espacios/{espacio.cliente_id}/simbiosis", params=cliente).status_code == 404
    assert http.get(f"/espacios/{espacio.cliente_id}{ruta}", params=LLAVE).status_code == 200


def test_pag_se_instala_como_app_del_negocio(http, espacio):
    base = f"/espacios/{espacio.cliente_id}"
    assert http.get(f"{base}/app.webmanifest").status_code == 401
    m = http.get(f"{base}/app.webmanifest", params=LLAVE).json()
    assert m["name"] == "Finca y Quinta de Muestra" and m["display"] == "standalone"
    assert m["start_url"].startswith(base) and m["icons"][0]["type"] == "image/svg+xml"
    svg = http.get(f"{base}/icono.svg", params=LLAVE)
    assert svg.headers["content-type"].startswith("image/svg+xml") and ">F</text>" in svg.text
    assert 'rel="manifest"' in http.get(base, params=LLAVE).text


def test_pag_negocio_nuevo_de_punta_a_punta(http, tmp_path, monkeypatch):
    """Plug and play: DGED crea el negocio y entrega dos enlaces que funcionan; el cliente no ve /negocios."""
    from agente.espacio import VARIABLE_RAIZ, llave_de
    monkeypatch.setenv(VARIABLE_RAIZ, str(tmp_path))
    assert http.get("/negocios").status_code == 404
    nuevo = {"id": "taller-ruiz", "nombre": "Taller Ruiz", "color": "#C0392B"}
    assert http.post("/negocios", json=nuevo, params={"llave": llave_de("taller-ruiz")}).status_code == 404
    r = http.post("/negocios", json=nuevo, params=LLAVE)
    assert r.status_code == 200
    enl = r.json()
    assert http.post("/negocios", json=nuevo, params=LLAVE).status_code == 409
    assert http.post("/negocios", json={**nuevo, "id": "Mal Id"}, params=LLAVE).status_code == 422
    assert http.post("/negocios", json={**nuevo, "id": "otro-x", "color": "rojo"}, params=LLAVE).status_code == 422
    panel = http.get(enl["panel"]).text
    assert "Taller Ruiz" in panel and "Complete los datos del negocio" in panel and "Aprendiendo" in panel
    assert "--marca:#c0392b" in panel
    assert "Taller Ruiz" in http.get(enl["conectar"]).text
    assert http.get("/negocios", params={"llave": llave_de("taller-ruiz")}).status_code == 404
    lista = http.get("/negocios", params=LLAVE).text
    assert "Taller Ruiz" in lista and enl["conectar"].replace("&", "&amp;") in lista


def test_pag_reglas_de_safari_en_iphone(http, espacio):
    """Lo que Safari hace distinto: números como enlaces, ícono PNG, teclado de teléfono, zonas seguras."""
    base = f"/espacios/{espacio.cliente_id}"
    for ruta in ("", "/alta", "/negocio"):
        t = http.get(base + ruta, params=LLAVE).text
        assert 'format-detection" content="telephone=no' in t and "viewport-fit=cover" in t
        assert 'rel="apple-touch-icon"' in t and "apple-mobile-web-app-capable" in t
    png = http.get(f"{base}/icono-180.png", params=LLAVE)
    assert png.content.startswith(b"\x89PNG") and png.headers["content-type"] == "image/png"
    alta = http.get(f"{base}/alta", params=LLAVE).text
    assert 'name="aprobador_telefono" id="c-aprobador_telefono" value="5210000000000" type="tel" inputmode="tel"' in alta
    v = http.get(f"/v/{espacio.cliente_id}", params={"t": __import__("agente.espacio").espacio.llave_de_vinculacion(espacio.cliente_id)}).text
    assert 'format-detection" content="telephone=no' in v and "safe-area-inset-bottom" in v
