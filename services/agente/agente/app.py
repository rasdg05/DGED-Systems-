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

import contextlib
import json
import os
import threading

from fastapi import Body, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from . import agente, canal, historial, operacion, paginas, perfil
from .espacio import Espacio, EspacioInvalido, llave_valida, raiz_por_defecto


@contextlib.asynccontextmanager
async def _arranque(_app):
    """Cada despliegue corre el backtest de cada espacio, en un hilo aparte: el
    servicio contesta mientras tanto, y si falla no se cae (`backtest.py`)."""
    from . import backtest

    threading.Thread(target=backtest.correr_todos, name="backtest", daemon=True).start()
    threading.Thread(target=_calendarios, name="calendario", daemon=True).start()
    yield


def _calendarios() -> None:
    """Baja los iCal de cada espacio cada media hora (`calendario.refrescar_todos`)."""
    import time

    from . import calendario

    while True:
        calendario.refrescar_todos()
        time.sleep(calendario.REFRESCO_MINUTOS * 60)


app = FastAPI(title="DGED — agente a la medida", lifespan=_arranque)
app.include_router(paginas.router)
app.include_router(operacion.router)


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
    envio = canal.enviar(espacio, salida)
    return {"aprobada": True, "enviada": not envio.get("encolada"), "encolada": bool(envio.get("encolada"))}


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


@app.post("/negocios")
def negocio_nuevo(datos: dict, llave: str | None = None, x_tenant_key: str | None = Header(default=None)) -> dict:
    """Un negocio nuevo, listo para entregar: nace en sombra, con su nombre y su color (solo DGED)."""
    from . import alta
    from .espacio import llave_maestra

    if not llave_maestra(x_tenant_key or llave):
        raise HTTPException(404, "no existe")
    cliente_id = str(datos.get("id", "")).strip()
    nombre = str(datos.get("nombre", "")).strip()
    color = str(datos.get("color", "") or "").strip().lower()
    try:
        espacio = Espacio(cliente_id)
    except EspacioInvalido as error:
        raise HTTPException(422, "identificador inválido: minúsculas, números y guiones (3 a 40)") from error
    if espacio.carpeta.exists():
        raise HTTPException(409, "ya existe un negocio con ese identificador")
    if not nombre:
        raise HTTPException(422, "falta el nombre comercial")
    if color and not paginas.HEX.match(color):
        raise HTTPException(422, "color de marca inválido: debe ser #rrggbb")
    alta.registrar(espacio, {"nombre_comercial": nombre}, parcial=True)  # deja encendido en sombra
    if color:
        config = espacio.config()
        config["marca_color"] = color
        espacio.escribir_json("config.json", config)
    return {"id": cliente_id, **paginas.enlaces_del_negocio(espacio)}


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
    espacio = paginas.espacio_taller(cliente_id, x_tenant_key or llave)
    return "".join(json.dumps(m.a_dict(), ensure_ascii=False) + "\n" for m in historial.cargar(espacio))


@app.post("/espacios/{cliente_id}/simbiosis")
def correr_simbiosis(cliente_id: str, x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    """La pasada grande del perfil (Opus, una vez). Deja una PROPUESTA: la enciende el dueño."""
    from . import gasto, modelo, simbiosis

    espacio = paginas.espacio_taller(cliente_id, x_tenant_key or llave)
    try:
        n, descartados = simbiosis.construir_perfil(espacio)
    except (modelo.Dormido, gasto.TopeAlcanzado) as error:
        raise HTTPException(503, str(error)) from error
    except Exception as error:
        # Un 500 mudo no se puede arreglar sin los logs de Railway: se dice qué
        # contestó la API (o en qué paró la pasada). La llave nunca viaja aquí.
        estado = getattr(error, "status_code", None)
        raise HTTPException(502, f"la pasada del perfil falló: {type(error).__name__}"
                                 f"{f' {estado}' if estado else ''}: {str(error)[:500]}") from error
    return {"version": n, "descartados": len(descartados), "revision": f"/espacios/{cliente_id}/revision"}


@app.get("/espacios/{cliente_id}/calendario.json")
def ver_calendario(cliente_id: str, desde: str | None = None, dias: int = 30,
                   x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    """Noches libres, ocupadas y sin saber por propiedad, y el estado de cada iCal.
    Las URLs no salen: abren el calendario a quien las tenga."""
    from datetime import date, datetime

    from . import calendario

    espacio = _espacio(cliente_id, x_tenant_key or llave)
    oc = calendario.Ocupacion.de(espacio)
    inicio = date.fromisoformat(desde) if desde else datetime.now(calendario.ZONA).date()
    return {"fuentes": oc.por_propiedad, "noches": oc.noches(inicio, max(1, min(dias, 400)))}


@app.post("/espacios/{cliente_id}/calendario/fuentes")
def agregar_fuente_calendario(cliente_id: str, propiedad: str = Body(..., embed=True),
                              plataforma: str = Body(..., embed=True), url: str = Body(..., embed=True),
                              x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    """`{"propiedad": "finca", "plataforma": "airbnb", "url": "https://..."}` y la baja de una vez."""
    from . import calendario

    espacio = _espacio(cliente_id, x_tenant_key or llave)
    try:
        calendario.agregar_fuente(espacio, propiedad, plataforma, url)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return {"estado": calendario.bajar(espacio)}


# --------------------------------------------------------------------------- #
#  Taller local (D-027): se trabaja en local, producción solo recibe y revisa  #
# --------------------------------------------------------------------------- #
@app.get("/espacios/{cliente_id}/espejo.json")
def espejo(cliente_id: str, x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    """Lo que hace falta para trabajar en local sin la API: alta, perfiles y salidas.
    El historial va aparte (`historial.jsonl`). Solo con la llave maestra."""
    espacio = paginas.espacio_taller(cliente_id, x_tenant_key or llave)
    return {"cliente_id": cliente_id, "alta": espacio.leer_json("alta.json", {}) or {},
            "activa": perfil.version_activa(espacio),
            "versiones": {n: perfil.leer_version(espacio, n) for n in perfil.versiones(espacio)},
            "salidas": [s.a_dict() for s in agente.salidas(espacio)],
            "aprobaciones_salida": espacio.leer_lineas("aprobaciones_salida.jsonl")}


@app.get("/espacios/{cliente_id}/pendientes.json")
def ver_pendientes(cliente_id: str, x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    from . import pendientes

    espacio = paginas.espacio_taller(cliente_id, x_tenant_key or llave)
    lista = pendientes.leer(historial.hilos(espacio))
    return {"resumen": pendientes.resumen(lista), "pendientes": [p.a_dict() for p in lista]}


@app.post("/espacios/{cliente_id}/rondas")
def subir_ronda(cliente_id: str, ronda: dict, probar: bool = True,
                x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    """Una ronda del enjambre local. `probar=true` (el de fábrica) solo valida contra
    el historial de producción; con `probar=false` las aceptadas quedan esperando el
    sí de una persona. Nada se envía desde aquí."""
    from . import rondas

    espacio = paginas.espacio_taller(cliente_id, x_tenant_key or llave)
    try:
        if probar:
            aceptadas, descartadas = rondas.validar(espacio, ronda)
            return {"probada": True, "aceptadas": len(aceptadas), "descartadas": descartadas}
        salidas, descartadas = rondas.cargar(espacio, ronda)
    except rondas.RondaInvalida as error:
        raise HTTPException(422, str(error)) from error
    return {"probada": False, "esperan_aprobacion": [s.id for s in salidas], "descartadas": descartadas}


@app.post("/espacios/{cliente_id}/canal")
def cambiar_canal(cliente_id: str, canal_: str = Body(..., embed=True, alias="canal"),
                  encendido: str = Body(..., embed=True),
                  x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    """Por dónde sale (`oficial` o `vinculado`, D-037) y qué sale (`sombra` o
    `sin_cifra`). Solo con la llave maestra; queda escrito en `cambios_canal.jsonl`.
    El enviador del vinculado arranca con el lector: tras cambiar a `vinculado`, se
    redespliega una vez."""
    from datetime import datetime, timezone

    espacio = paginas.espacio_taller(cliente_id, x_tenant_key or llave)
    if canal_ not in ("oficial", "vinculado") or encendido not in canal.ENCENDIDOS:
        raise HTTPException(422, f"canal: oficial|vinculado; encendido: {'|'.join(canal.ENCENDIDOS)}")
    config = espacio.config()
    antes = {"canal": config.get("canal", "oficial"), "encendido": config.get("encendido", "sombra")}
    config.update(canal=canal_, encendido=encendido)
    espacio.escribir_json("config.json", config)
    espacio.agregar_linea("cambios_canal.jsonl", {"antes": antes, "ahora": {"canal": canal_, "encendido": encendido},
                                                 "en": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return {"antes": antes, "ahora": {"canal": canal_, "encendido": encendido}, "listo": canal.configurado(espacio)}


@app.post("/espacios/{cliente_id}/rondas/{nombre}/aprobar")
def aprobar_ronda(cliente_id: str, nombre: str, aprobador: str = Body(..., embed=True),
                  x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    """El sí de una persona del alta a toda una ronda ya revisada (D-037, como Gestor):
    cada salida queda aprobada a su nombre y, si su canal y sus candados la dejan,
    en la cola de envío. Solo con la llave maestra."""
    from . import rondas

    espacio = paginas.espacio_taller(cliente_id, x_tenant_key or llave)
    cargada = espacio.leer_json(f"rondas/{nombre}.json", None) if rondas.NOMBRE_VALIDO.match(nombre) else None
    if not cargada:
        raise HTTPException(404, "no existe esa ronda")
    resultado = {"encoladas": [], "no_salen": []}
    for salida_id in cargada.get("salidas", []):
        try:
            salida = agente.aprobar_salida(espacio, salida_id, aprobador)
        except perfil.AprobacionInvalida as error:
            raise HTTPException(403, str(error)) from error
        except KeyError:
            resultado["no_salen"].append({"salida": salida_id, "motivo": "no existe"})
            continue
        if (motivo := canal.motivo_para_no_enviar(espacio, salida)):
            resultado["no_salen"].append({"salida": salida_id, "motivo": motivo})
            continue
        canal.enviar(espacio, salida)
        resultado["encoladas"].append(salida_id)
    return resultado


@app.post("/espacios/{cliente_id}/documentos")
def subir_documento(cliente_id: str, nombre: str = Body(..., embed=True), texto: str = Body(..., embed=True),
                    x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    """Un documento del negocio (respuestas del dueño, lista escrita) como texto, para que un
    renglón del perfil pueda citarlo (`origen.tipo = documento`). Solo con la llave maestra;
    no se pisa uno que ya existe: otra versión, otro nombre."""
    import re

    espacio = paginas.espacio_taller(cliente_id, x_tenant_key or llave)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,60}\.(?:md|txt)", nombre) or not texto.strip():
        raise HTTPException(422, "nombre: minúsculas, números y guiones, .md o .txt; y un texto")
    ruta = espacio.ruta(f"documentos/{nombre}")
    if ruta.exists():
        raise HTTPException(409, "ya existe un documento con ese nombre")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    return {"documento": nombre, "caracteres": len(texto)}


@app.post("/espacios/{cliente_id}/propuestas")
def subir_propuesta(cliente_id: str, cuerpo: dict,
                    x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    """Un perfil armado en local (enjambre, sin API). Pasa por la misma validación
    que la pasada de Opus: renglón sin cita literal, fuera. Queda como propuesta."""
    espacio = paginas.espacio_taller(cliente_id, x_tenant_key or llave)
    nombre = str(cuerpo.get("nombre", "")).strip()
    if not nombre or not isinstance(cuerpo.get("perfil"), dict):
        raise HTTPException(422, "lleva `nombre` y `perfil`")
    alta = espacio.leer_json("alta.json", {}) or {}
    propuesta = dict(cuerpo["perfil"], giro=alta.get("giro"), nombre_comercial=alta.get("nombre_comercial"))
    n, descartados = perfil.proponer(espacio, propuesta, autor="enjambre local (Claude Code)", nombre=nombre)
    return {"version": n, "descartados": descartados, "revision": f"/espacios/{cliente_id}/revision"}


@app.get("/espacios/{cliente_id}/backtest.json")
def ver_backtest(cliente_id: str, x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    """El último backtest (el agente de hoy contra los últimos 14 días) y su historial."""
    from . import backtest

    return backtest.leer(paginas.espacio_taller(cliente_id, x_tenant_key or llave))


@app.post("/espacios/{cliente_id}/backtest")
def correr_backtest(cliente_id: str, x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> dict:
    from . import backtest

    return backtest.correr(paginas.espacio_taller(cliente_id, x_tenant_key or llave), "a mano")
