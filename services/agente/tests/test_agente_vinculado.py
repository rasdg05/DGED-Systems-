"""El lector vinculado (D-018): lee, nunca envía. Sin neonize ni red."""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace as NS

from agente import historial, vinculado
from agente.espacio import llave_de

FUENTE = Path(vinculado.__file__)
PROHIBIDAS = ("send", "mark_read", "presence", "reply", "edit_message", "revoke")


def test_vinc_el_lector_no_llama_nada_que_escriba_a_whatsapp():
    llamadas = {n.func.attr for n in ast.walk(ast.parse(FUENTE.read_text(encoding="utf-8")))
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not {c for c in llamadas if any(p in c.lower() for p in PROHIBIDAS)}


def _wmi(ident, de_mi, ts, **mensaje):
    return NS(message=NS(key=NS(ID=ident, fromMe=de_mi), messageTimestamp=ts, message=NS(**mensaje)))


def test_vinc_historial_sin_grupos_con_lid_y_pies_de_foto():
    data = NS(
        phoneNumberToLidMappings=[NS(pnJID="5215550001111@s.whatsapp.net", lidJID="987654@lid")],
        conversations=[
            NS(ID="987654@lid", messages=[
                _wmi("a1", False, 100, conversation="Hola, ¿tienen fecha?"),
                _wmi("a2", True, 110, conversation="", extendedTextMessage=NS(text="Sí, con gusto")),
                _wmi("a3", False, 120, conversation="", imageMessage=NS(caption="así es la fiesta")),
                _wmi("a4", False, 130, conversation="", ephemeralMessage=NS(message=NS(conversation="envuelto"))),
            ]),
            NS(ID="1203630@g.us", messages=[_wmi("g1", False, 1, conversation="grupo")]),
            NS(ID="status@broadcast", messages=[_wmi("s1", False, 1, conversation="estado")]),
        ])
    m = {x.id: x for x in vinculado.mensajes_del_historial(data)}
    assert set(m) == {"a1", "a2", "a3", "a4"}
    assert all(x.hilo == "5215550001111" for x in m.values())
    assert m["a2"].del_negocio and m["a2"].texto == "Sí, con gusto"
    assert (m["a3"].tipo, m["a3"].texto) == ("imagen", "así es la fiesta")
    assert m["a4"].texto == "envuelto"


def test_vinc_mensaje_vivo_entrante_y_de_la_casa():
    jid = NS(User="5215550002222", Server="s.whatsapp.net")
    entra = NS(Info=NS(ID="v1", Timestamp=1_790_000_000_000,
                       MessageSource=NS(IsGroup=False, IsFromMe=False, Sender=jid, SenderAlt=None)),
               Message=NS(conversation="¿Precio?"))
    m = vinculado.mensaje_vivo(entra)
    assert (m.hilo, m.del_negocio, m.ts, m.texto) == ("5215550002222", False, 1_790_000_000, "¿Precio?")
    lid = NS(User="123", Server="lid")
    sale = NS(Info=NS(ID="v2", Timestamp=5, MessageSource=NS(IsGroup=False, IsFromMe=True, Chat=lid,
                                                             RecipientAlt=jid)),
              Message=NS(conversation="Le confirmo"))
    assert vinculado.mensaje_vivo(sale).hilo == "5215550002222"
    grupo = NS(Info=NS(ID="v3", Timestamp=5, MessageSource=NS(IsGroup=True)), Message=None)
    assert vinculado.mensaje_vivo(grupo) is None
    resolver = lambda _jid: NS(User="5215550003333")  # noqa: E731
    sin_alt = NS(Info=NS(ID="v4", Timestamp=5, MessageSource=NS(IsGroup=False, IsFromMe=False, Sender=lid,
                                                                SenderAlt=None)), Message=NS(conversation="x"))
    assert vinculado.mensaje_vivo(sin_alt, resolver).hilo == "5215550003333"


def test_vinc_numero_ajeno_no_importa(espacio):
    config = espacio.config()
    config["numero_negocio"] = "52 1 555 000 0000"
    espacio.escribir_json("config.json", config)
    antes = len(historial.cargar(espacio))
    nuevo = [historial.Mensaje("z1", "529", False, 1, "text", "hola")]
    vinculado.publicar(espacio, "conectado", numero="5219999999999")
    assert vinculado.importar(espacio, nuevo) == 0 and len(historial.cargar(espacio)) == antes
    vinculado.publicar(espacio, "conectado", numero="5215550000000")
    assert vinculado.importar(espacio, nuevo) == 1
    assert vinculado.leer_estado(espacio)["mensajes"] == antes + 1


def test_vinc_el_qr_no_queda_guardado_al_conectar(espacio):
    vinculado.publicar(espacio, "esperando_qr", qr="2@codigo")
    assert vinculado.leer_estado(espacio)["qr"] == "2@codigo"
    vinculado.publicar(espacio, "conectado")
    assert "qr" not in vinculado.leer_estado(espacio)


def test_vinc_paginas_de_alta_vincular_y_descarga(espacio, monkeypatch):
    from agente.app import app
    from fastapi.testclient import TestClient
    http = TestClient(app)
    base = f"/espacios/{espacio.cliente_id}"
    assert http.get(f"{base}/vincular").status_code == 401
    maestra = {"llave": "secreto-de-prueba"}  # TENANT_INTERNAL_TOKEN del dueño de DGED abre todos
    assert "El lector no está corriendo" in http.get(f"{base}/vincular", params=maestra).text
    vinculado.publicar(espacio, "esperando_qr", qr="2@codigo-de-prueba")
    pagina = http.get(f"{base}/vincular", params={"llave": llave_de(espacio.cliente_id)}).text
    assert "<svg" in pagina and "solo LEE" in pagina
    assert "Nombre comercial" in http.get(f"{base}/alta", params=maestra).text
    r = http.post(f"{base}/alta", params=maestra, json={"giro": "renta", "numero_negocio": "+52 1 555"})
    assert r.status_code == 422 and "nombre comercial" in r.text
    datos = {c: "x" for c in ("giro", "nombre_comercial", "que_vende", "como_cobra", "horario", "aprobador",
                               "aprobador_telefono")}
    assert http.post(f"{base}/alta", params=maestra, json=dict(datos, numero_negocio="+52 1 555")).status_code == 200
    assert espacio.config()["numero_negocio"] == "521555"
    descarga = http.get(f"{base}/historial.jsonl", params=maestra).text
    assert descarga.count("\n") == len(historial.cargar(espacio))
    assert http.post(f"{base}/simbiosis", params=maestra).status_code == 503  # sin ANTHROPIC_API_KEY
    assert http.get("/").status_code == 200


def test_vinc_simbiosis_por_http_deja_propuesta(espacio, monkeypatch):
    from agente import simbiosis
    from agente.app import app
    from fastapi.testclient import TestClient
    llamado = {}
    monkeypatch.setattr(simbiosis, "construir_perfil", lambda e: llamado.setdefault("n", (7, [])))
    r = TestClient(app).post(f"/espacios/{espacio.cliente_id}/simbiosis", params={"llave": "secreto-de-prueba"})
    assert r.json()["version"] == 7 and llamado


def test_vinc_lineas_a_medias_no_tumban_la_lectura(espacio):
    with espacio.ruta(historial.ARCHIVO).open("a", encoding="utf-8") as f:
        f.write('{"id": "medio')
    assert len(historial.cargar(espacio)) > 0


def test_vinc_codigo_de_vinculacion_se_ve_y_se_limpia(espacio):
    from agente.app import app
    from fastapi.testclient import TestClient
    vinculado.publicar(espacio, "esperando_codigo", codigo="ABCD-EFGH")
    pagina = TestClient(app).get(f"/espacios/{espacio.cliente_id}/vincular", params={"llave": "secreto-de-prueba"}).text
    assert "ABCD-EFGH" in pagina and "número de teléfono" in pagina
    vinculado.publicar(espacio, "conectado")
    assert "codigo" not in vinculado.leer_estado(espacio)
