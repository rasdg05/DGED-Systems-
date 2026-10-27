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

import json
import os

from fastapi import Body, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from . import agente, canal, historial, paginas, perfil
from .espacio import Espacio, EspacioInvalido, llave_valida, raiz_por_defecto

app = FastAPI(title="DGED — agente a la medida")
app.include_router(paginas.router)


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
@app.get("/api/health")  # si Railway lee el railway.json de la raíz (el de Atlas), su healthcheck es éste
def health() -> dict:
    return {"ok": True, "service": "dged-agente", "commit": os.environ.get("GIT_COMMIT", "")}


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


@app.post("/espacios/{cliente_id}/versiones/{n}/aprobar")
def aprobar_version(cliente_id: str, n: int, aprobador: str = Body(..., embed=True),
                    x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    espacio = _espacio(cliente_id, x_tenant_key or llave)
    try:
        perfil.aprobar(espacio, n, aprobador=aprobador)
    except perfil.AprobacionInvalida as error:
        raise HTTPException(403, str(error)) from error
    return {"activa": n}


@app.post("/espacios/{cliente_id}/salidas/{salida_id}/aprobar")
def aprobar_salida(cliente_id: str, salida_id: str, aprobador: str = Body(..., embed=True),
                   x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    espacio = _espacio(cliente_id, x_tenant_key or llave)
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
@app.get("/", response_class=HTMLResponse)
def inicio() -> str:
    return paginas._documento(None, "DGED", "<main class='contenido aparece' style='padding-top:22vh'>"
                              "<p class='sobre'>DGED</p><h1 class='titulo-grande'>Servicio privado</h1>"
                              "<p class='lede'>Entre con el enlace de su espacio.</p></main>")


@app.post("/espacios/{cliente_id}/alta")
def alta_guardar(cliente_id: str, datos: dict, x_tenant_key: str | None = Header(default=None),
                 llave: str | None = None) -> dict:
    from . import alta

    espacio = _espacio(cliente_id, x_tenant_key or llave)
    numero = "".join(c for c in str(datos.pop("numero_negocio", "") or "") if c.isdigit())
    color = str(datos.pop("color_marca", "") or "").strip()
    if color and not paginas.HEX.match(color):
        raise HTTPException(422, "color de marca inválido: debe ser #rrggbb")
    try:
        registrada = alta.registrar(espacio, datos, parcial=True)
    except alta.AltaIncompleta as error:
        raise HTTPException(422, str(error)) from error
    if numero or color:
        config = espacio.config()
        if numero:
            config["numero_negocio"] = numero
        if color:
            config["marca_color"] = color.lower()
        espacio.escribir_json("config.json", config)
    return {"alta": sorted(registrada), "faltan": alta.faltan(registrada)}


@app.post("/espacios/{cliente_id}/marca")
def marca_guardar(cliente_id: str, color: str = Body(..., embed=True), x_tenant_key: str | None = Header(default=None),
                  llave: str | None = None) -> dict:
    espacio = _espacio(cliente_id, x_tenant_key or llave)
    if not paginas.HEX.match(color or ""):
        raise HTTPException(422, "color de marca inválido: debe ser #rrggbb")
    config = espacio.config()
    config["marca_color"] = color.lower()
    espacio.escribir_json("config.json", config)
    return {"marca_color": config["marca_color"]}


@app.post("/espacios/{cliente_id}/portada")
async def portada_guardar(cliente_id: str, request: Request, x_tenant_key: str | None = Header(default=None),
                          llave: str | None = None) -> dict:
    """La foto del negocio para su pantalla. Se juzga por sus bytes, no por el Content-Type."""
    espacio = _espacio(cliente_id, x_tenant_key or llave)
    datos = await request.body()
    try:
        ext = paginas.guardar_portada(espacio, datos)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return {"portada": ext, "bytes": len(datos)}


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
