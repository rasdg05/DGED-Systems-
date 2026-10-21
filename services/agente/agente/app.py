"""Servidor del agente: webhook de Meta, pantalla de revisión y aprobaciones.

    uvicorn agente.app:app --port 8090   (desde services/agente)

- `GET/POST /webhook`: verificación (`WHATSAPP_VERIFY_TOKEN`) y entrega firmada
  (`WHATSAPP_APP_SECRET`). Sin firma válida no entra nada.
- `/espacios/{id}/...`: con la llave del cliente (`X-Tenant-Key`). La pantalla
  de revisión enseña cada renglón propuesto con el mensaje de donde salió.
  Se empieza por los datos, no por la pantalla: esta es la mínima que hace
  falta para que el dueño apruebe.
"""
from __future__ import annotations

import html
import json
import os

from fastapi import Body, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from . import agente, canal, historial, perfil
from .espacio import Espacio, EspacioInvalido, llave_valida, raiz_por_defecto

app = FastAPI(title="DGED — agente a la medida")


def _espacio(cliente_id: str, llave: str | None) -> Espacio:
    try:
        espacio = Espacio(cliente_id)
    except EspacioInvalido as error:
        raise HTTPException(404, "no existe") from error
    if not llave_valida(cliente_id, llave):
        raise HTTPException(401, "llave inválida o servidor sin TENANT_INTERNAL_TOKEN")
    return espacio


def _por_numero(phone_number_id: str) -> Espacio | None:
    raiz = raiz_por_defecto()
    if not raiz.exists():
        return None
    for carpeta in sorted(p for p in raiz.iterdir() if p.is_dir()):
        try:
            espacio = Espacio(carpeta.name, raiz)
        except EspacioInvalido:
            continue
        if phone_number_id and espacio.config().get("phone_number_id") == phone_number_id:
            return espacio
    return None


@app.get("/health")
def health() -> dict:
    return {"ok": True, "commit": os.environ.get("GIT_COMMIT", "")}


@app.get("/webhook", response_class=PlainTextResponse)
def verificar(request: Request) -> str:
    q = request.query_params
    esperado = os.environ.get("WHATSAPP_VERIFY_TOKEN", "").strip()
    if not esperado or q.get("hub.mode") != "subscribe" or q.get("hub.verify_token") != esperado:
        raise HTTPException(403, "verificación rechazada")
    return q.get("hub.challenge", "")


@app.post("/webhook")
async def recibir(request: Request, x_hub_signature_256: str | None = Header(default=None)) -> dict:
    cuerpo = await request.body()
    if not canal.firma_valida(cuerpo, x_hub_signature_256):
        raise HTTPException(401, "firma inválida")
    carga = json.loads(cuerpo or b"{}")
    resumen = {"guardados": 0, "salidas": 0}
    for entrada in carga.get("entry", []) or []:
        for cambio in entrada.get("changes", []) or []:
            numero = ((cambio.get("value") or {}).get("metadata") or {}).get("phone_number_id", "")
            espacio = _por_numero(numero)
            if espacio is None:
                continue
            parcial = {"object": carga.get("object"), "entry": [{"id": entrada.get("id"), "changes": [cambio]}]}
            mensajes = historial.de_webhook(parcial)
            if cambio.get("field") != "messages":
                resumen["guardados"] += historial.guardar(espacio, mensajes)
                continue
            for m in mensajes:
                if m.del_negocio:
                    continue
                salida = agente.atender(espacio, m)
                resumen["salidas"] += 1
                if not canal.motivo_para_no_enviar(espacio, salida):
                    try:
                        canal.enviar(espacio, salida)
                    except OSError as error:  # Meta caída: la salida queda escrita y la ve la persona; no se pide reintento
                        espacio.agregar_linea("envios_fallidos.jsonl", {"salida": salida.id, "error": type(error).__name__})
    return resumen


def _origen_html(espacio: Espacio, renglon: dict, mensajes: dict) -> str:
    o = renglon.get("origen", {}) or {}
    cita = html.escape(o.get("cita", ""))
    if o.get("tipo") == "mensaje" and (m := mensajes.get(o.get("id"))):
        return f"«{cita}» — mensaje del {'negocio' if m.del_negocio else 'cliente'}: {html.escape(m.texto or '')}"
    return f"«{cita}» — {html.escape(o.get('tipo', '?'))} {html.escape(str(o.get('campo') or o.get('nombre') or ''))}"


@app.get("/espacios/{cliente_id}/revision", response_class=HTMLResponse)
def revision(cliente_id: str, x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, x_tenant_key or llave)
    versiones = perfil.versiones(espacio)
    activa = perfil.version_activa(espacio)
    pendiente = next((n for n in reversed(versiones) if activa is None or n > activa), None)
    if pendiente is None:
        return f"<p>Sin propuestas pendientes. Activa: {activa}</p>"
    v = perfil.leer_version(espacio, pendiente)
    mensajes = historial.por_id(espacio)
    filas = []
    for seccion in perfil.SECCIONES:
        for r in v["perfil"].get(seccion, []):
            visible = {k: val for k, val in r.items() if k != "origen"}
            filas.append(f"<tr><td>{seccion}</td><td>{html.escape(json.dumps(visible, ensure_ascii=False))}</td>"
                         f"<td>{_origen_html(espacio, r, mensajes)}</td></tr>")
    tirados = "".join(f"<li>{html.escape(d['seccion'])}: {html.escape(d['motivo'])}</li>" for d in v["descartados"])
    return (f"<!doctype html><meta charset=utf-8><title>Revisión del perfil</title>"
            f"<h1>Versión {pendiente}: {html.escape(v['nombre'])}</h1><p>Autor: {html.escape(v['autor'])}. "
            f"Activa hoy: {activa}. Nada de esto se enciende hasta que usted lo apruebe.</p>"
            f"<table border=1 cellpadding=4><tr><th>Sección</th><th>Renglón</th><th>De dónde salió</th></tr>"
            f"{''.join(filas)}</table><h2>No entraron (sin origen que se pueda probar)</h2><ul>{tirados}</ul>")


@app.post("/espacios/{cliente_id}/versiones/{n}/aprobar")
def aprobar_version(cliente_id: str, n: int, aprobador: str = Body(..., embed=True),
                    x_tenant_key: str | None = Header(default=None)) -> dict:
    espacio = _espacio(cliente_id, x_tenant_key)
    try:
        perfil.aprobar(espacio, n, aprobador=aprobador)
    except perfil.AprobacionInvalida as error:
        raise HTTPException(403, str(error)) from error
    return {"activa": n}


@app.post("/espacios/{cliente_id}/salidas/{salida_id}/aprobar")
def aprobar_salida(cliente_id: str, salida_id: str, aprobador: str = Body(..., embed=True),
                   x_tenant_key: str | None = Header(default=None)) -> dict:
    espacio = _espacio(cliente_id, x_tenant_key)
    try:
        salida = agente.aprobar_salida(espacio, salida_id, aprobador)
    except perfil.AprobacionInvalida as error:
        raise HTTPException(403, str(error)) from error
    except KeyError as error:
        raise HTTPException(404, "no existe esa salida") from error
    motivo = canal.motivo_para_no_enviar(espacio, salida)
    if motivo:
        return {"aprobada": True, "enviada": False, "motivo": motivo}
    canal.enviar(espacio, salida)
    return {"aprobada": True, "enviada": True}


# --------------------------------------------------------------------------- #
#  Alta, QR del lector vinculado e historial (D-018)                           #
# --------------------------------------------------------------------------- #
PAGINA = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
          "<title>{titulo}</title><style>body{{font-family:system-ui,sans-serif;max-width:640px;margin:24px auto;"
          "padding:0 16px;background:#fff;color:#111}}input,textarea{{width:100%;padding:8px;margin:4px 0 12px;"
          "box-sizing:border-box}}button{{padding:10px 16px}}.qr svg{{width:100%;max-width:360px;height:auto}}"
          "</style>{cuerpo}")
CAMPOS_ALTA = (("giro", "Giro"), ("nombre_comercial", "Nombre comercial"), ("que_vende", "Qué vende"),
               ("como_cobra", "Cómo cobra hoy"), ("horario", "Horario"), ("aprobador", "Quién aprueba las cotizaciones"),
               ("aprobador_telefono", "Teléfono de quien aprueba"), ("numero_negocio", "Número del WhatsApp Business"))


@app.get("/", response_class=HTMLResponse)
def inicio() -> str:
    return PAGINA.format(titulo="DGED agente", cuerpo="<h1>DGED — agente a la medida</h1><p>Servicio privado.</p>")


@app.get("/espacios/{cliente_id}/alta", response_class=HTMLResponse)
def alta_form(cliente_id: str, llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    actual = espacio.leer_json("alta.json", {}) or {}
    actual.setdefault("numero_negocio", espacio.config().get("numero_negocio", ""))
    campos = "".join(f"<label>{html.escape(t)}<input name='{c}' value='{html.escape(str(actual.get(c, '')))}'></label>"
                     for c, t in CAMPOS_ALTA)
    script = ("<script>document.querySelector('form').onsubmit=async e=>{e.preventDefault();"
              "const d=Object.fromEntries(new FormData(e.target));"
              "const r=await fetch(location.pathname+location.search,{method:'POST',"
              "headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});"
              "document.querySelector('#r').textContent=r.ok?'Guardado. Ahora abra Vincular.':await r.text()}</script>")
    cuerpo = (f"<h1>Alta: {html.escape(cliente_id)}</h1><form>{campos}<button>Guardar</button></form>"
              f"<p id=r></p><p><a href='vincular?llave={html.escape(llave or '')}'>Vincular WhatsApp →</a></p>{script}")
    return PAGINA.format(titulo="Alta", cuerpo=cuerpo)


@app.post("/espacios/{cliente_id}/alta")
def alta_guardar(cliente_id: str, datos: dict, x_tenant_key: str | None = Header(default=None),
                 llave: str | None = None) -> dict:
    from . import alta

    espacio = _espacio(cliente_id, x_tenant_key or llave)
    numero = "".join(c for c in str(datos.pop("numero_negocio", "") or "") if c.isdigit())
    try:
        registrada = alta.registrar(espacio, datos)
    except alta.AltaIncompleta as error:
        raise HTTPException(422, str(error)) from error
    if numero:
        config = espacio.config()
        config["numero_negocio"] = numero
        espacio.escribir_json("config.json", config)
    return {"alta": sorted(registrada)}


def _qr_svg(codigo: str) -> str:
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        return f"<pre>{html.escape(codigo)}</pre>"
    return qrcode.make(codigo, image_factory=qrcode.image.svg.SvgPathImage).to_string(encoding="unicode")


@app.get("/espacios/{cliente_id}/vincular", response_class=HTMLResponse)
def vincular(cliente_id: str, llave: str | None = None) -> str:
    from . import vinculado

    espacio = _espacio(cliente_id, llave)
    estado = vinculado.leer_estado(espacio)
    hilos = historial.hilos(espacio)
    lineas = {
        "sin_lector": "El lector no está corriendo para este espacio (revise AGENTE_ESPACIO_VINCULADO).",
        "arrancando": "Arrancando…",
        "esperando_qr": "En el teléfono del negocio: WhatsApp Business → Dispositivos vinculados → Vincular un dispositivo.",
        "vinculado": "Vinculado. Esperando el historial…",
        "conectado": "Conectado. El historial llega por partes: deje el teléfono abierto y con internet unos minutos.",
        "numero_ajeno": "Se vinculó un número que no es el del negocio: no se importa nada. Desvincúlelo desde el teléfono.",
        "desconectado": "La sesión se cerró desde el teléfono. Reinicie el servicio para un QR nuevo.",
    }
    qr = f"<div class=qr>{_qr_svg(estado['qr'])}</div>" if estado.get("estado") == "esperando_qr" and estado.get("qr") else ""
    cuerpo = (f"<meta http-equiv=refresh content=5><h1>Vincular WhatsApp: {html.escape(cliente_id)}</h1>"
              f"<p><b>{html.escape(estado.get('estado', ''))}</b> — {html.escape(lineas.get(estado.get('estado'), ''))}</p>"
              f"{qr}<p>Mensajes guardados: {sum(len(v) for v in hilos.values())} en {len(hilos)} conversaciones.</p>"
              f"<p>Este servicio solo LEE: no envía mensajes, ni acuses de lectura, ni aparece en línea.</p>"
              f"<p><a href='historial.jsonl?llave={html.escape(llave or '')}'>Descargar historial</a></p>")
    return PAGINA.format(titulo="Vincular", cuerpo=cuerpo)


@app.get("/espacios/{cliente_id}/historial.jsonl", response_class=PlainTextResponse)
def descargar_historial(cliente_id: str, x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, x_tenant_key or llave)
    return "".join(json.dumps(m.a_dict(), ensure_ascii=False) + "\n" for m in historial.cargar(espacio))


@app.post("/espacios/{cliente_id}/simbiosis")
def correr_simbiosis(cliente_id: str, x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    """La pasada grande del perfil (Opus, una vez). Deja una PROPUESTA: la enciende el dueño."""
    from . import gasto, modelo, simbiosis

    espacio = _espacio(cliente_id, x_tenant_key or llave)
    try:
        n, descartados = simbiosis.construir_perfil(espacio)
    except (modelo.Dormido, gasto.TopeAlcanzado) as error:
        raise HTTPException(503, str(error)) from error
    return {"version": n, "descartados": len(descartados), "revision": f"/espacios/{cliente_id}/revision"}
