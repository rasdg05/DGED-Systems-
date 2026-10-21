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
def revision(cliente_id: str, x_tenant_key: str | None = Header(default=None)) -> str:
    espacio = _espacio(cliente_id, x_tenant_key)
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
