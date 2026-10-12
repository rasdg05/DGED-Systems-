"""El Oráculo, sin red ni clave: un cliente de Anthropic simulado.

Cada test cuida una invariante del oráculo (DECISIONS.md D-010): las cifras
salen de herramientas, no hay megawatts, se listan fuentes y ausentes, el tope
de pasos se respeta y sin clave el endpoint duerme con 503.
"""
import copy
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from atlas import oracle
from fastapi import HTTPException

SCORE = {
    "modelVersion": "atlas-live-0.1.0",
    "composite": 73.6,
    "risk": 26.4,
    "coverage": 1.0,
    "publishable": True,
    "factors": [
        {"key": "drought", "label": "Sequía municipal", "score": 78, "missing": False, "raw": {"observed": "D0", "used": "D0"}},
        {"key": "flood", "label": "Inundación", "score": 84, "missing": False, "raw": {"hit": False}},
        {"key": "land", "label": "Uso de suelo", "score": 70, "missing": False, "raw": {"class": "ASENTAMIENTOS HUMANOS"}},
        {"key": "establishments", "label": "Establecimientos", "score": None, "missing": True, "raw": {"mode": "ausente"}},
        {"key": "logistics", "label": "Ruta", "score": None, "missing": True, "raw": {"reason": "SAKBE_TOKEN ausente"}},
    ],
}
EVIDENCE = {
    "municipalityUrl": "https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/buscar/25.7789/-100.1886",
    "landUrl": "https://gaia.inegi.org.mx/NLB/tunnel/wms/wms61?REQUEST=GetFeatureInfo",
    "droughtUrl": "https://smn.conagua.gob.mx/tools/RESOURCES/Monitor%20de%20Sequia%20en%20Mexico/MunicipiosSequia.xlsx",
}
SITES = [
    {"id": "apodaca-industrial", "name": "Apodaca, corredor industrial", "corridor": "norte"},
    {"id": "silao-puerto", "name": "Silao, puerto interior", "corridor": "bajio"},
]


class FakeAtlas:
    def __init__(self):
        self.scored = {}
        self.calls = []

    def list_sites(self, corridor):
        self.calls.append(("list", corridor))
        return {"sites": [s for s in SITES if not corridor or s["corridor"] == corridor]}

    def score_site(self, site_id, drought_year):
        self.calls.append(("score", site_id, drought_year))
        site = next((s for s in SITES if s["id"] == site_id), None)
        if site is None:
            raise HTTPException(status_code=404, detail="Sitio no encontrado")
        self.scored[site_id] = copy.deepcopy(SCORE)
        return site | {"score": self.scored[site_id], "evidence": EVIDENCE}

    def site_detail(self, site_id):
        site = next((s for s in SITES if s["id"] == site_id), None)
        if site is None:
            raise HTTPException(status_code=404, detail="Sitio no encontrado")
        payload = dict(site)
        if site_id in self.scored:
            payload |= {"score": self.scored[site_id], "evidence": EVIDENCE}
        return payload

    def ontology(self):
        return {"objectTypes": [{"apiName": "Sitio"}, {"apiName": "SubestacionAprox"}]}

    def sources(self):
        return {"conagua_smn": {"ok": True, "url": EVIDENCE["droughtUrl"]}, "inegi_denue": {"ok": False}}

    def api(self):
        return oracle.AtlasApi(
            list_sites=self.list_sites,
            score_site=self.score_site,
            site_detail=self.site_detail,
            ontology=self.ontology,
            sources=self.sources,
        )


def tool_use(name, tool_input, block_id):
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=tool_input)


def text(value):
    return SimpleNamespace(type="text", text=value)


def reply(stop_reason, *content):
    return SimpleNamespace(stop_reason=stop_reason, content=list(content))


class FakeClient:
    """Imita client.beta.messages.create con un guion de respuestas."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(copy.copy(kwargs) | {"messages": list(kwargs["messages"])})
        if callable(self.script[0]):
            return self.script[0](len(self.requests))
        return self.script.pop(0)


def scored_conversation(final_text):
    return [
        reply("tool_use", tool_use("listar_sitios", {"corredor": "norte"}, "t1")),
        reply("tool_use", tool_use("calificar_sitio", {"site_id": "apodaca-industrial", "anio_seco": False}, "t2")),
        reply("end_turn", text(final_text)),
    ]


def test_el_ciclo_llama_al_atlas_y_devuelve_pasos_fuentes_y_ausentes():
    atlas = FakeAtlas()
    client = FakeClient(scored_conversation("Apodaca califica 73.6, publicable; sequía D0 con 78."))
    result = oracle.ask("¿Cómo sale Apodaca?", atlas.api(), client, model="claude-opus-5-5")

    assert [step["tool"] for step in result["steps"]] == ["listar_sitios", "calificar_sitio"]
    assert result["steps"][1]["input"] == {"site_id": "apodaca-industrial", "anio_seco": False}
    assert "73.6" in result["steps"][1]["summary"]
    assert ("score", "apodaca-industrial", False) in atlas.calls
    assert result["unverified"] == []
    assert "73.6" in result["answer"] and "78" in result["answer"]
    assert set(EVIDENCE.values()) <= set(result["sources"])
    for url in EVIDENCE.values():
        assert url in result["answer"]
    assert "Apodaca, corredor industrial: Establecimientos" in result["missing"]
    assert "Apodaca, corredor industrial: Ruta" in result["missing"]
    assert "Factores que no respondieron" in result["answer"]
    # El resultado de la herramienta regresa al modelo, ligado a su tool_use.
    last = client.requests[-1]["messages"]
    assert last[-1]["role"] == "user" and last[-1]["content"][0]["tool_use_id"] == "t2"


def test_una_cifra_que_no_salio_de_una_herramienta_se_retira():
    client = FakeClient(scored_conversation("Apodaca sale 73.6 y le faltan 12.5 puntos para el mejor; ronda 99."))
    result = oracle.ask("¿Cómo sale Apodaca?", FakeAtlas().api(), client)
    assert result["unverified"] == ["12.5", "99"]
    assert "12.5" not in result["answer"].split("Fuentes:")[0]
    assert oracle.AVISO_CIFRA in result["answer"]
    assert "73.6" in result["answer"]


def test_sin_herramientas_ninguna_cifra_pasa():
    client = FakeClient([reply("end_turn", text("De memoria: Apodaca saca 80 y Silao 75."))])
    result = oracle.ask("¿Cuál es mejor?", FakeAtlas().api(), client)
    assert result["steps"] == []
    assert result["unverified"] == ["80", "75"]
    assert result["sources"] == []
    assert "no se consultó el score de ningún sitio" in result["answer"]


def test_codigos_con_letra_y_miles_no_se_confunden_con_cifras():
    answer, unverified = oracle.verify_numbers("Sequía D2, capa c463, radio de 1,500 m.", '{"radiusM": 1500}')
    assert unverified == []
    assert "D2" in answer and "1,500" in answer


def test_nunca_afirma_megawatts():
    client = FakeClient(scored_conversation("Apodaca sale 73.6. La subestación tiene 50 MW disponibles. Sequía D0."))
    result = oracle.ask("¿Cuánta energía hay?", FakeAtlas().api(), client)
    assert not oracle.AFIRMACION_MW.search(result["answer"])
    assert oracle.AVISO_MW in result["answer"]
    assert "73.6" in result["answer"]
    # La cifra eléctrica no se cuenta como "sin verificar": la oración entera ya salió.
    assert "50" not in result["unverified"]


def test_el_tope_de_pasos_se_respeta():
    def always_tool(n):
        return reply("tool_use", tool_use("ver_ontologia", {}, f"t{n}"))

    client = FakeClient([always_tool])
    result = oracle.ask("Explora todo", FakeAtlas().api(), client, max_steps=oracle.MAX_STEPS)
    assert len(result["steps"]) == oracle.MAX_STEPS
    assert result["stop"] == "tope"
    assert oracle.AVISO_TOPE in result["answer"]
    assert client.requests[-1]["tool_choice"] == {"type": "none"}
    assert all(r["tool_choice"] == {"type": "auto"} for r in client.requests[:-1])
    assert len(client.requests) == oracle.MAX_STEPS + 1


def test_al_tope_el_modelo_contesta_con_lo_que_tiene():
    script = [reply("tool_use", tool_use("estado_fuentes", {}, "t1")), reply("end_turn", text("Una fuente no responde."))]
    result = oracle.ask("¿Qué fuentes hay?", FakeAtlas().api(), FakeClient(script), max_steps=1)
    assert result["stop"] == "tope"
    assert result["answer"].startswith("Una fuente no responde.")


def test_un_error_del_atlas_regresa_como_error_de_herramienta():
    script = [
        reply("tool_use", tool_use("calificar_sitio", {"site_id": "no-existe", "anio_seco": False}, "t1")),
        reply("end_turn", text("Ese sitio no existe en Atlas.")),
    ]
    client = FakeClient(script)
    result = oracle.ask("Califica no-existe", FakeAtlas().api(), client)
    assert result["steps"][0]["summary"] == "error: Sitio no encontrado"
    sent = client.requests[-1]["messages"][-1]["content"][0]
    assert sent["is_error"] is True


def test_comparar_marca_lo_no_calificado():
    atlas = FakeAtlas()
    atlas.score_site("apodaca-industrial", False)
    out = oracle.execute(atlas.api(), "comparar_sitios", {"site_ids": ["apodaca-industrial", "silao-puerto"]})
    rows = {row["id"]: row for row in out["sitios"]}
    assert rows["apodaca-industrial"]["composite"] == 73.6
    assert rows["silao-puerto"]["calificado"] is False
    with pytest.raises(oracle.ToolError):
        oracle.execute(atlas.api(), "comparar_sitios", {"site_ids": ["apodaca-industrial"]})


def test_listar_trae_el_total_escrito():
    out = oracle.execute(FakeAtlas().api(), "listar_sitios", {"corredor": "todos"})
    assert out["total"] == 2


def test_un_rechazo_no_se_rellena():
    result = oracle.ask("…", FakeAtlas().api(), FakeClient([reply("refusal")]))
    assert result["stop"] == "refusal"
    assert result["answer"].startswith(oracle.AVISO_RECHAZO)


def test_la_peticion_usa_el_modelo_vigente_y_herramientas_estrictas(monkeypatch):
    monkeypatch.delenv("ATLAS_ORACLE_MODEL", raising=False)
    assert oracle.model_name() == "claude-opus-5-5"
    monkeypatch.setenv("ATLAS_ORACLE_MODEL", "claude-sonnet-5-5")
    assert oracle.model_name() == "claude-sonnet-5-5"
    client = FakeClient([reply("end_turn", text("Hola."))])
    oracle.ask("Hola", FakeAtlas().api(), client)
    request = client.requests[0]
    assert request["model"] == "claude-sonnet-5-5"
    assert "thinking" not in request and "budget_tokens" not in str(request)
    assert {tool["name"] for tool in request["tools"]} == {
        "listar_sitios", "calificar_sitio", "ficha_sitio", "ver_ontologia", "estado_fuentes", "comparar_sitios",
    }
    assert all(tool["strict"] and tool["input_schema"]["additionalProperties"] is False for tool in request["tools"])


def test_sin_clave_el_endpoint_duerme_con_503(monkeypatch):
    from atlas import main

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(oracle, "make_client", lambda: pytest.fail("sin clave no se crea cliente"))
    with pytest.raises(HTTPException) as caught:
        main.ask_oracle(main.OracleQuestion(question="¿Qué sitio es mejor?"))
    assert caught.value.status_code == 503
    assert "ANTHROPIC_API_KEY" in caught.value.detail


def test_con_clave_el_endpoint_devuelve_el_contrato(monkeypatch):
    from atlas import main

    atlas = FakeAtlas()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-prueba")
    monkeypatch.setattr(oracle, "make_client", lambda: FakeClient(scored_conversation("Apodaca sale 73.6.")))
    monkeypatch.setattr(main, "oracle_api", atlas.api)
    out = main.ask_oracle(main.OracleQuestion(question="¿Cómo sale Apodaca?"))
    assert set(out) >= {"answer", "steps", "sources", "unverified"}
    assert out["unverified"] == [] and out["sources"]


def test_la_ui_muestra_el_503():
    static = Path(__file__).resolve().parent / "static"
    js = (static / "app.js").read_text(encoding="utf-8")
    assert 'fetch("/api/oracle"' in js and "payload.detail" in js
    assert 'id="oracle"' in (static / "index.html").read_text(encoding="utf-8")


def test_env_example_declara_las_variables_del_oraculo():
    lineas = (Path(__file__).resolve().parents[2] / ".env.example").read_text(encoding="utf-8").splitlines()
    assert "ANTHROPIC_API_KEY=" in lineas and "ATLAS_ORACLE_MODEL=" in lineas
