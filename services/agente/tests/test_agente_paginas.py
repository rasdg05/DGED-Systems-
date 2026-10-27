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


def test_pag_tablero_cuenta_y_guia(http, espacio):
    t = http.get(f"/espacios/{espacio.cliente_id}", params=LLAVE).text
    n = len(historial.cargar(espacio))
    assert f"<b>{n}</b>" in t and "Perfil aprobado" in t and "Banco y sombra" in t


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
    # El tablero lo ofrece para copiar.
    assert f"/v/{espacio.cliente_id}?t={t}" in http.get(f"/espacios/{espacio.cliente_id}", params=LLAVE).text


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
