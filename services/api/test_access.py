"""La puerta del Oráculo y el tope por IP (atlas/access.py)."""
from types import SimpleNamespace

import pytest
from atlas import access
from fastapi import HTTPException


def request(key=None, host="10.0.0.1"):
    headers = {access.HEADER: key} if key is not None else {}
    return SimpleNamespace(headers=headers, client=SimpleNamespace(host=host))


@pytest.fixture(autouse=True)
def limpio():
    access.reset()
    yield
    access.reset()


def test_sin_token_no_hay_puerta_aunque_haya_clave_de_anthropic(monkeypatch):
    monkeypatch.delenv("ATLAS_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-prueba")
    with pytest.raises(HTTPException) as caught:
        access.guard_oracle(request("cualquiera"))
    assert caught.value.status_code == 503
    assert "ATLAS_ACCESS_TOKEN" in caught.value.detail


@pytest.mark.parametrize("key", [None, "", "otra"])
def test_llave_ausente_o_equivocada_es_401(monkeypatch, key):
    monkeypatch.setenv("ATLAS_ACCESS_TOKEN", "buena")
    with pytest.raises(HTTPException) as caught:
        access.guard_oracle(request(key))
    assert caught.value.status_code == 401


def test_llave_correcta_pasa(monkeypatch):
    monkeypatch.setenv("ATLAS_ACCESS_TOKEN", "buena")
    access.guard_oracle(request("buena"))


def test_el_tope_por_ip_corta_con_429_y_retry_after(monkeypatch):
    monkeypatch.setenv("ATLAS_SCORE_LIMIT", "2")
    access.check_rate("score", "1.1.1.1", now=0)
    access.check_rate("score", "1.1.1.1", now=1)
    with pytest.raises(HTTPException) as caught:
        access.check_rate("score", "1.1.1.1", now=2)
    assert caught.value.status_code == 429
    assert int(caught.value.headers["Retry-After"]) > 0
    access.check_rate("score", "2.2.2.2", now=2)


def test_la_ventana_se_libera(monkeypatch):
    monkeypatch.setenv("ATLAS_SCORE_LIMIT", "1")
    access.check_rate("score", "1.1.1.1", now=0)
    access.check_rate("score", "1.1.1.1", now=600)


def test_un_tope_mal_escrito_usa_el_de_fabrica(monkeypatch):
    monkeypatch.setenv("ATLAS_ORACLE_LIMIT", "muchos")
    assert access.limit_for("oracle") == (20, 3600)


def test_las_rutas_que_gastan_tienen_su_guardia():
    from atlas import main

    guardias = {}
    for route in main.app.routes:
        deps = [d.call for d in getattr(getattr(route, "dependant", None), "dependencies", [])]
        guardias[getattr(route, "path", "")] = deps
    assert access.guard_oracle in guardias["/api/oracle"]
    assert access.guard_score in guardias["/api/sites/{site_id}/score"]


def test_la_ui_manda_la_llave():
    from pathlib import Path

    js = (Path(__file__).resolve().parent / "static" / "app.js").read_text(encoding="utf-8")
    assert '"X-Atlas-Key"' in js


def test_health_dice_el_commit(monkeypatch):
    from atlas import main

    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "abcdef1234567890")
    assert main.health()["commit"] == "abcdef123456"
