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
    assert r.status_code == 200 and "<nav>" in r.text and "Finca y Quinta de Muestra" in r.text


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
