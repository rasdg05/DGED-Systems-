"""Fixtures del agente: espacios con la muestra ficticia y un modelo falso sin red."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from agente import alta, historial, perfil
from agente.espacio import Espacio

MUESTRA = Path(__file__).resolve().parent.parent / "muestra"


def leer_muestra(nombre: str):
    return json.loads((MUESTRA / nombre).read_text(encoding="utf-8"))


class ModeloFalso:
    """Contesta con los textos que se le dan, en orden, y cuenta las llamadas."""

    def __init__(self, *textos: str, stop_reason: str = "end_turn"):
        self.textos = list(textos)
        self.stop_reason = stop_reason
        self.llamadas: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.llamadas.append(kwargs)
        texto = self.textos.pop(0) if self.textos else ""
        uso = SimpleNamespace(input_tokens=1200, output_tokens=80, cache_read_input_tokens=3000,
                              cache_creation_input_tokens=0)
        return SimpleNamespace(stop_reason=self.stop_reason, usage=uso,
                               content=[SimpleNamespace(type="text", text=texto)])


def montar(raiz: Path, cliente_id: str = "muestra-vacacional", tope: float | None = 5.0) -> Espacio:
    espacio = Espacio(cliente_id, raiz)
    alta.registrar(espacio, leer_muestra("alta.json"))
    historial.guardar(espacio, historial.de_webhook(leer_muestra("historial_webhook.json")))
    if tope is not None:
        config = espacio.config()
        config["tope_usd_mes"] = tope
        espacio.escribir_json("config.json", config)
    n, _ = perfil.proponer(espacio, leer_muestra("perfil_grabado.json"), autor="muestra", nombre="muestra")
    perfil.aprobar(espacio, n, aprobador="Dueña de muestra")
    return espacio


@pytest.fixture()
def espacio(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("TENANT_INTERNAL_TOKEN", "secreto-de-prueba")
    monkeypatch.setenv("AGENTE_DATOS", str(tmp_path))
    return montar(tmp_path)


def entrante(texto: str, hilo: str = "5210000009999", ts: int = 1790000000, ident: str = "wamid.PRUEBA1"):
    return historial.Mensaje(id=ident, hilo=hilo, del_negocio=False, ts=ts, tipo="text", texto=texto)
