"""Las pantallas del espacio: tablero, alta, vincular, conversaciones, revisión y banco.

HTML hecho en el servidor, sin dependencias, pensado para abrirse desde un
celular. Toda pantalla pide la llave (`?llave=`) y todo texto que viene de un
cliente se escapa. Los teléfonos de los clientes finales se enseñan
enmascarados (los últimos 4): la pantalla es para revisar, no para copiar datos.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse

from . import agente, banco, historial, perfil, sombra, vinculado
from . import alta as alta_mod
from .espacio import Espacio, EspacioInvalido, llave_de_vinculacion, llave_valida, vinculacion_valida

router = APIRouter()

CSS = """
:root{--bg:#f5f2ec;--panel:#fffdf9;--panel2:#f0ece4;--line:#e3ddd2;--text:#1f1c18;--muted:#7a7266;
--accent:#2f4a3a;--accent-ink:#fff;--good:#3d6b4f;--mid:#9a6b1f;--bad:#a2412f;--r:10px;
--serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
--sans:ui-sans-serif,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#141412;--panel:#1b1b18;--panel2:#22221e;--line:#2e2d29;--text:#ece8e0;
--muted:#9b958a;--accent:#cdbf9f;--accent-ink:#141412;--good:#9cbf9a;--mid:#d8b36a;--bad:#e08b78}}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--text);
font:16px/1.55 var(--sans);-webkit-text-size-adjust:100%;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration-color:var(--line);text-underline-offset:3px}
.top{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 92%,transparent);
backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.top .in{max-width:720px;margin:0 auto;padding:18px 20px 0}
.marca h1{margin:0;font:500 24px/1.15 var(--serif);letter-spacing:-.01em}
nav{display:flex;gap:22px;overflow-x:auto;margin-top:12px;scrollbar-width:none}
nav::-webkit-scrollbar{display:none}
nav a{flex:none;padding:6px 0 11px;color:var(--muted);font-size:14px;text-decoration:none;border-bottom:2px solid transparent}
nav a.on{color:var(--text);border-bottom-color:var(--text)}
main{max-width:720px;margin:0 auto;padding:26px 20px 110px}
h2{font:500 20px/1.25 var(--serif);margin:34px 0 12px;letter-spacing:-.005em}h2:first-child{margin-top:0}
.lede{color:var(--muted);margin:0 0 14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:20px;margin:0 0 14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));border:1px solid var(--line);
border-radius:var(--r);background:var(--panel);overflow:hidden}
.kpi{padding:16px 18px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);margin:0 -1px -1px 0}
.kpi b{display:block;font:500 28px/1.1 var(--serif)}.kpi span{color:var(--muted);font-size:13px}
.pasos{list-style:none;margin:0;padding:0}
.pasos li{display:flex;gap:14px;align-items:flex-start;padding:16px 0;border-bottom:1px solid var(--line)}
.pasos li:first-child{padding-top:0}.pasos li:last-child{border-bottom:0;padding-bottom:0}
.pt{flex:none;width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font:13px var(--sans);
border:1px solid var(--line);color:var(--muted)}
.pt.ok{background:var(--good);border-color:var(--good);color:#fff}.pt.ya{border-color:var(--text);color:var(--text)}
.pasos b{font-weight:600}.pasos small{display:block;color:var(--muted);font-size:14px;margin-top:2px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 18px;border-radius:8px;
border:1px solid var(--accent);background:var(--accent);color:var(--accent-ink);font:600 15px var(--sans);
cursor:pointer;text-decoration:none;white-space:nowrap}
.btn.sec{background:transparent;color:var(--text);border-color:var(--line)}.btn:disabled{opacity:.5}
.acciones{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.badge{display:inline-block;font-size:12px;letter-spacing:.02em;padding:3px 10px;border-radius:999px;
background:var(--panel2);color:var(--muted)}
.badge.ok{color:var(--good)}.badge.mid{color:var(--mid)}.badge.bad{color:var(--bad)}
label{display:block;font-size:14px;font-weight:600;margin:18px 0 6px}label:first-child{margin-top:0}
label small{display:block;font-weight:400;color:var(--muted);margin-top:2px}
input,textarea{width:100%;padding:12px 14px;border-radius:8px;border:1px solid var(--line);background:var(--bg);
color:var(--text);font:inherit}textarea{min-height:96px;resize:vertical}
input:focus,textarea:focus{outline:none;border-color:var(--text)}
.req{color:var(--muted);font-weight:400}
.barra{position:fixed;left:0;right:0;bottom:0;background:color-mix(in srgb,var(--bg) 94%,transparent);
backdrop-filter:blur(10px);border-top:1px solid var(--line);padding:12px 20px calc(12px + env(safe-area-inset-bottom))}
.barra .in{max-width:720px;margin:0 auto;display:flex;gap:14px;align-items:center}
.barra a{white-space:nowrap;font-size:14px;color:var(--muted)}
.toast{color:var(--muted);font-size:14px;line-height:1.3}
.codigo{font:500 40px/1.1 ui-monospace,"SF Mono",Menlo,monospace;letter-spacing:.14em;text-align:center;
padding:26px 10px;margin-top:16px;border-radius:var(--r);background:var(--panel2);color:var(--text)}
.qr{background:#fff;border-radius:var(--r);padding:16px;max-width:320px;margin:16px auto 0;border:1px solid var(--line)}
.qr svg{width:100%;height:auto;display:block}
.hilo{display:flex;justify-content:space-between;gap:12px;align-items:center;text-decoration:none}
.hilo .t{color:var(--muted);font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chat{display:flex;flex-direction:column;gap:8px}
.bur{max-width:82%;padding:10px 13px;border-radius:12px;background:var(--panel);border:1px solid var(--line);
overflow-wrap:anywhere;white-space:pre-wrap}
.bur.n{align-self:flex-end;background:var(--panel2)}
.bur small{display:block;color:var(--muted);font-size:11px;margin-top:4px}
.cita{border-left:2px solid var(--line);padding:2px 0 2px 12px;margin:12px 0 0;color:var(--muted);font-size:14px}
.cita small{text-transform:uppercase;letter-spacing:.08em;font-size:10.5px}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:10px 8px;border-bottom:1px solid var(--line);text-align:left}
th{font-weight:600;color:var(--muted);font-size:12px;letter-spacing:.04em;text-transform:uppercase}
.tabla{overflow-x:auto;padding:6px 12px}
.vacio{color:var(--muted);text-align:center;padding:30px 10px}
.solo{max-width:460px}.solo h1{font:500 30px/1.15 var(--serif);margin:0 0 6px;letter-spacing:-.01em}
.pie{color:var(--muted);font-size:12px;text-align:center;margin-top:28px;letter-spacing:.04em}
"""
SECCIONES = (("", "Tablero"), ("alta", "Alta"), ("vincular", "WhatsApp"), ("conversaciones", "Conversaciones"),
             ("revision", "Perfil"), ("banco", "Banco"))


def esc(texto) -> str:
    return html.escape(str(texto if texto is not None else ""))


def _espacio(cliente_id: str, llave: str | None) -> Espacio:
    try:
        espacio = Espacio(cliente_id)
    except EspacioInvalido as error:
        raise HTTPException(404, "no existe") from error
    if not llave_valida(cliente_id, llave):
        raise HTTPException(401, "llave inválida o servidor sin TENANT_INTERNAL_TOKEN")
    return espacio


def url(espacio: Espacio, seccion: str, llave: str | None, **extra) -> str:
    base = f"/espacios/{espacio.cliente_id}" + (f"/{seccion}" if seccion else "")
    params = "&".join(f"{k}={quote(str(v))}" for k, v in {"llave": llave or "", **extra}.items())
    return f"{base}?{params}"


def pagina(espacio: Espacio | None, llave: str | None, activa: str, titulo: str, cuerpo: str,
           refrescar: int | None = None, barra: str = "", navegacion: bool = True) -> str:
    alta = (espacio.leer_json("alta.json", {}) or {}) if espacio else {}
    nombre = alta.get("nombre_comercial") or (espacio.cliente_id if espacio else "DGED")
    nav = ""
    if espacio and navegacion:
        nav = "<nav>" + "".join(f'<a class="{"on" if s == activa else ""}" href="{esc(url(espacio, s, llave))}">{t}</a>'
                                for s, t in SECCIONES) + "</nav>"
    meta = f'<meta http-equiv="refresh" content="{refrescar}">' if refrescar else ""
    barra_html = f'<div class="barra"><div class="in">{barra}</div></div>' if barra else ""
    cabeza = ('<header class="top"><div class="in"><div class="marca">'
              f'<h1>{esc(nombre)}</h1></div>{nav}</div></header>') if navegacion else ""
    clase = ' class="solo"' if not navegacion else ""
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="color-scheme" content="light dark">{meta}'
            f"<title>{esc(titulo)} · {esc(nombre)}</title><style>{CSS}</style></head><body>"
            f"{cabeza}<main{clase}>{cuerpo}</main>{barra_html}</body></html>")


def _enmascarar(telefono: str) -> str:
    return "•••• " + telefono[-4:] if len(telefono) > 4 else telefono


def _hora(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%d/%m/%Y %H:%M") if ts else ""


# --------------------------------------------------------------------------- #
#  Tablero                                                                     #
# --------------------------------------------------------------------------- #
@router.get("/espacios/{cliente_id}", response_class=HTMLResponse)
def tablero(cliente_id: str, llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    alta = espacio.leer_json("alta.json") or {}
    estado = vinculado.leer_estado(espacio)
    hilos = historial.hilos(espacio)
    n_msj = sum(len(v) for v in hilos.values())
    activa = perfil.version_activa(espacio)
    versiones = perfil.versiones(espacio)
    pendiente = next((n for n in reversed(versiones) if activa is None or n > activa), None)
    conectado = estado.get("estado") in ("conectado", "vinculado")

    def paso(hecho: bool, en_curso: bool, n: int, titulo: str, detalle: str, enlace: str, boton: str) -> str:
        clase = "ok" if hecho else ("ya" if en_curso else "")
        marca = "✓" if hecho else str(n)
        return (f'<li><span class="pt {clase}">{marca}</span><div style="flex:1"><b>{titulo}</b>'
                f'<small>{detalle}</small></div><a class="btn sec" href="{esc(enlace)}">{boton}</a></li>')

    pasos = "".join([
        paso(bool(alta) and not alta_mod.faltan(alta), True, 1, "Alta del negocio",
             ("Lo básico: qué vende, cómo cobra, quién aprueba." if not alta else
              ("Lista." if not alta_mod.faltan(alta) else "Falta: " + ", ".join(alta_mod.faltan(alta)) + ".")),
             url(espacio, "alta", llave), "Abrir"),
        paso(conectado, bool(alta) and not conectado, 2, "WhatsApp vinculado (solo lectura)",
             esc(ESTADOS.get(estado.get("estado", "sin_lector"), ("", estado.get("estado", ""), ""))[1]),
             url(espacio, "vincular", llave), "Vincular"),
        paso(n_msj > 0, conectado and not n_msj, 3, "Historial del negocio",
             f"{n_msj} mensajes en {len(hilos)} conversaciones.", url(espacio, "conversaciones", llave), "Ver"),
        paso(activa is not None, n_msj > 0 and activa is None, 4, "Perfil aprobado",
             (f"Versión {activa} activa." if activa else "Sin perfil activo.")
             + (f" Propuesta {pendiente} por revisar." if pendiente else ""), url(espacio, "revision", llave), "Revisar"),
        paso(False, activa is not None, 5, "Banco y sombra",
             "Antes de encender nada: pass^k sin errores caros y 30 conversaciones en sombra.",
             url(espacio, "banco", llave), "Correr"),
    ])
    salidas = agente.salidas(espacio)
    kpis = (f'<div class="grid"><div class="kpi"><b>{n_msj}</b><span>mensajes leídos</span></div>'
            f'<div class="kpi"><b>{len(hilos)}</b><span>conversaciones</span></div>'
            f'<div class="kpi"><b>{len(salidas)}</b><span>borradores en sombra</span></div>'
            f'<div class="kpi"><b>{esc(espacio.config().get("encendido", "sombra"))}</b><span>encendido</span></div></div>')
    simb = ""
    if n_msj and activa is None and not pendiente:
        simb = ('<div class="card"><b>Armar la primera propuesta de perfil</b><p class="lede">Una pasada del modelo grande '
                'sobre el historial. Cada dato sale citado de un mensaje; nada se enciende hasta que el dueño lo aprueba.</p>'
                f'<button class="btn" onclick="correr(this,\'{esc(url(espacio, "simbiosis", llave))}\')">Proponer perfil</button>'
                '<p class="toast" id="t"></p></div>' + _JS_POST)
    enlace = f"/v/{espacio.cliente_id}?t={llave_de_vinculacion(espacio.cliente_id)}"
    compartir = ('<div class="card"><b>Enlace para el negocio</b><p class="lede">Mándeselo por WhatsApp. Solo abre la '
                 'pantalla de vincular: no ve conversaciones, perfil ni nada más.</p>'
                 f'<input readonly id="enl" value="" data-ruta="{esc(enlace)}">'
                 '<div class="acciones"><button class="btn" onclick="copiar()">Copiar enlace</button></div></div>'
                 "<script>const e=document.getElementById('enl');e.value=location.origin+e.dataset.ruta;"
                 "function copiar(){navigator.clipboard.writeText(e.value).then(()=>{e.select()})}</script>")
    cuerpo = (f'<h2>Cómo va</h2>{kpis}<h2>Pasos</h2><div class="card"><ol class="pasos">{pasos}</ol></div>{simb}{compartir}')
    return pagina(espacio, llave, "", "Tablero", cuerpo)


_JS_POST = ("<script>async function correr(b,u){b.disabled=true;const t=document.getElementById('t');"
            "t.textContent='Trabajando… puede tardar un par de minutos.';"
            "const r=await fetch(u,{method:'POST'});const d=await r.json().catch(()=>({}));"
            "t.textContent=r.ok?'Listo. Abra Perfil para revisar.':(d.detail||'No se pudo.');b.disabled=false}</script>")


# --------------------------------------------------------------------------- #
#  Alta                                                                        #
# --------------------------------------------------------------------------- #
CAMPOS_ALTA = (
    ("Su negocio", (
        ("nombre_comercial", "Nombre comercial", "Como lo conocen sus clientes.", False),
        ("giro", "Giro", "Ej. renta de finca para fines de semana y eventos.", False),
        ("que_vende", "Qué ofrece", "Espacios, capacidad, qué incluye. Con sus palabras.", True),
        ("propiedades", "Propiedades", "Una por renglón. Cada una se cotiza aparte.", True),
    )),
    ("Cómo trabaja", (
        ("como_cobra", "Cómo cobra hoy", "Por noche, fin de semana, evento, persona extra, depósito, anticipo. "
         "Si es de memoria, dígalo así.", True),
        ("horario", "Horario", "A qué hora contestan; entrada y salida de huéspedes.", False),
    )),
    ("Quién decide", (
        ("aprobador", "Quién aprueba las cotizaciones", "Nada con precio sale sin su sí.", False),
        ("aprobador_telefono", "Teléfono de quien aprueba", "Con lada. Se queda en este espacio.", False),
        ("numero_negocio", "Número del WhatsApp Business", "El que se va a vincular, con lada. Si se vincula "
         "otro número por error, no se importa nada.", False),
    )),
)


@router.get("/espacios/{cliente_id}/alta", response_class=HTMLResponse)
def alta_form(cliente_id: str, llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    actual = espacio.leer_json("alta.json", {}) or {}
    actual.setdefault("numero_negocio", espacio.config().get("numero_negocio", ""))
    bloques = ""
    for titulo, campos in CAMPOS_ALTA:
        filas = ""
        for c, t, ayuda, largo in campos:
            req = '<span class="req"> *</span>' if c not in ("numero_negocio", "propiedades") else ""
            crudo = actual.get(c, "")
            valor = esc("\n".join(crudo) if isinstance(crudo, list) else crudo)
            control = (f'<textarea name="{c}">{valor}</textarea>' if largo
                       else f'<input name="{c}" value="{valor}" autocomplete="off">')
            filas += f'<label>{t}{req} <small>{esc(ayuda)}</small></label>{control}'
        bloques += f'<h2>{titulo}</h2><div class="card">{filas}</div>'
    script = ("<script>const f=document.querySelector('form');f.onsubmit=async e=>{e.preventDefault();"
              "const d=Object.fromEntries(new FormData(f));const t=document.getElementById('t');t.textContent='Guardando…';"
              "const r=await fetch(location.pathname+location.search,{method:'POST',headers:{'Content-Type':'application/json'},"
              "body:JSON.stringify(d)});const j=await r.json().catch(()=>({}));"
              "t.textContent=r.ok?(j.faltan&&j.faltan.length?'Guardado ✓ Falta: '+j.faltan.join(', '):'Guardado ✓ Completa'):"
              "('No se guardó: '+(j.detail||'revise los campos'))}</script>")
    cuerpo = (f'<p class="lede">Lo básico del negocio. También es fuente: un dato del perfil puede citar lo que '
              f'escriba aquí, así que escríbalo como lo diría a un cliente.</p><form id="alta">{bloques}</form>{script}')
    barra = ('<button class="btn" form="alta">Guardar alta</button><span class="toast" id="t"></span>'
             f'<a style="margin-left:auto" href="{esc(url(espacio, "vincular", llave))}">WhatsApp →</a>')
    return pagina(espacio, llave, "alta", "Alta", cuerpo, barra=barra)


# --------------------------------------------------------------------------- #
#  Vincular                                                                    #
# --------------------------------------------------------------------------- #
ESTADOS = {
    "sin_lector": ("bad", "El lector no está corriendo", "Revise que AGENTE_ESPACIO_VINCULADO sea exactamente este espacio."),
    "arrancando": ("mid", "Arrancando…", "En unos segundos aparece el código o el QR."),
    "esperando_qr": ("mid", "Listo para escanear", "En el teléfono del negocio: WhatsApp Business → Dispositivos "
                     "vinculados → Vincular un dispositivo, y escanee."),
    "esperando_codigo": ("mid", "Teclee el código", "En el teléfono del negocio: Dispositivos vinculados → Vincular un "
                         "dispositivo → Vincular con número de teléfono, y teclee el código."),
    "vinculado": ("ok", "Vinculado", "Esperando el historial…"),
    "conectado": ("ok", "Conectado", "El historial llega por partes: deje el teléfono abierto y con internet unos minutos."),
    "numero_ajeno": ("bad", "Número equivocado", "Se vinculó un número que no es el del negocio: no se importa nada. "
                     "Desvincúlelo desde el teléfono."),
    "desconectado": ("bad", "Sesión cerrada", "Se cerró desde el teléfono. Reinicie el servicio para un código nuevo."),
    "error": ("bad", "Error del lector", ""),
}


def _qr_svg(codigo: str) -> str:
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        return f"<pre>{esc(codigo)}</pre>"
    return qrcode.make(codigo, image_factory=qrcode.image.svg.SvgPathImage).to_string(encoding="unicode")


@router.get("/espacios/{cliente_id}/vincular", response_class=HTMLResponse)
def vincular(cliente_id: str, llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    estado = vinculado.leer_estado(espacio)
    clave = estado.get("estado", "sin_lector")
    tono, titulo, ayuda = ESTADOS.get(clave, ("mid", clave, ""))
    hilos = historial.hilos(espacio)
    n = sum(len(v) for v in hilos.values())
    centro = ""
    if clave == "esperando_codigo" and estado.get("codigo"):
        centro = f'<div class="codigo">{esc(estado["codigo"])}</div>'
    elif clave == "esperando_qr" and estado.get("qr"):
        centro = f'<div class="qr">{_qr_svg(estado["qr"])}</div>'
    detalle = f'<p class="lede">{esc(estado.get("detalle", ""))}</p>' if estado.get("detalle") else ""
    cuerpo = (f'<div class="card"><span class="badge {tono}">WhatsApp</span><h2 style="margin:10px 0 4px">{esc(titulo)}</h2>'
              f'<p class="lede">{esc(ayuda)}</p>{detalle}{centro}</div>'
              f'<div class="grid"><div class="kpi"><b>{n}</b><span>Mensajes guardados</span></div>'
              f'<div class="kpi"><b>{len(hilos)}</b><span>conversaciones</span></div></div>'
              '<div class="card" style="margin-top:12px"><b>Este servicio solo LEE.</b> <span class="lede">No envía mensajes, '
              'no marca como leído y no aparece en línea. Al terminar, puede desvincularlo desde el teléfono.</span>'
              f'<div class="acciones"><a class="btn sec" href="{esc(url(espacio, "conversaciones", llave))}">Ver conversaciones</a>'
              f'<a class="btn sec" href="{esc(url(espacio, "historial.jsonl", llave))}">Descargar historial</a></div></div>')
    return pagina(espacio, llave, "vincular", "WhatsApp", cuerpo, refrescar=5)


# --------------------------------------------------------------------------- #
#  Conversaciones                                                              #
# --------------------------------------------------------------------------- #
@router.get("/espacios/{cliente_id}/conversaciones", response_class=HTMLResponse)
def conversaciones(cliente_id: str, llave: str | None = None, hilo: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    hilos = historial.hilos(espacio)
    if hilo and hilo in hilos:
        burbujas = "".join(
            f'<div class="bur {"n" if m.del_negocio else ""}">{esc(m.texto or "[" + m.tipo + " sin texto]")}'
            f'<small>{"negocio" if m.del_negocio else "cliente"} · {_hora(m.ts)}</small></div>' for m in hilos[hilo])
        cuerpo = (f'<p><a href="{esc(url(espacio, "conversaciones", llave))}">← Todas</a></p>'
                  f'<h2>{esc(_enmascarar(hilo))} · {len(hilos[hilo])} mensajes</h2><div class="chat">{burbujas}</div>')
        return pagina(espacio, llave, "conversaciones", "Conversación", cuerpo)
    orden = sorted(hilos.items(), key=lambda kv: -kv[1][-1].ts)
    filas = "".join(
        f'<a class="card hilo" href="{esc(url(espacio, "conversaciones", llave, hilo=h))}">'
        f'<div style="min-width:0"><b>{esc(_enmascarar(h))}</b><div class="t">{esc((ms[-1].texto or "")[:90])}</div></div>'
        f'<span class="badge">{len(ms)}</span></a>' for h, ms in orden)
    cuerpo = (f'<p class="lede">{len(hilos)} conversaciones, de la más reciente a la más vieja. Los teléfonos van '
              f'enmascarados.</p>{filas or "<div class=vacio>Todavía no hay mensajes. Vincule el WhatsApp.</div>"}')
    return pagina(espacio, llave, "conversaciones", "Conversaciones", cuerpo)


# --------------------------------------------------------------------------- #
#  Revisión del perfil                                                         #
# --------------------------------------------------------------------------- #
NOMBRES_SECCION = {"datos": "Datos", "temporadas": "Temporadas", "voz": "Voz", "reglas": "Reglas de cotización",
                   "faq": "Preguntas frecuentes", "escala": "Lo que pasa a una persona"}


def _origen_html(renglon: dict, mensajes: dict) -> str:
    o = renglon.get("origen", {}) or {}
    cita = esc(o.get("cita", ""))
    if o.get("tipo") == "mensaje" and (m := mensajes.get(o.get("id"))):
        return (f'<div class="cita"><small>De dónde salió</small><br>«{cita}»<br><small>mensaje del {"negocio" if m.del_negocio else "cliente"}: '
                f'{esc(m.texto or "")}</small></div>')
    return f'<div class="cita"><small>De dónde salió</small><br>«{cita}» <small>— {esc(o.get("tipo", "?"))} {esc(o.get("campo") or o.get("nombre") or "")}</small></div>'


def _renglon_html(seccion: str, r: dict) -> str:
    visible = {k: v for k, v in r.items() if k != "origen"}
    if seccion == "voz":
        return f"«{esc(visible.get('frase'))}»"
    if seccion == "faq":
        return f"<b>{esc(visible.get('pregunta'))}</b><br>{esc(visible.get('respuesta'))}"
    if seccion == "reglas" and visible.get("monto_centavos") is not None:
        from .cotizador import pesos
        visible["monto"] = pesos(visible.pop("monto_centavos"))
    if seccion == "datos":
        return (f'<small class="lede">{esc(visible.get("objeto"))} · {esc(visible.get("id"))}</small><br>'
                f'{esc(str(visible.get("campo", "")).replace("_", " "))}: <b>{esc(visible.get("valor"))}</b>')
    return " · ".join(f"{esc(str(k).replace('_', ' '))}: <b>{esc(v)}</b>" for k, v in visible.items())


@router.get("/espacios/{cliente_id}/revision", response_class=HTMLResponse)
def revision(cliente_id: str, x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, x_tenant_key or llave)
    activa = perfil.version_activa(espacio)
    pendiente = next((n for n in reversed(perfil.versiones(espacio)) if activa is None or n > activa), None)
    if pendiente is None:
        cuerpo = (f'<div class="card vacio">Sin propuestas pendientes. Activa: {esc(activa)}.'
                  '<br>Cuando haya historial, la propuesta se arma desde el Tablero.</div>')
        return pagina(espacio, llave or x_tenant_key, "revision", "Perfil", cuerpo)
    v = perfil.leer_version(espacio, pendiente)
    mensajes = historial.por_id(espacio)
    bloques = ""
    for seccion in perfil.SECCIONES:
        filas = v["perfil"].get(seccion, [])
        if not filas:
            continue
        tarjetas = "".join(f'<div class="card">{_renglon_html(seccion, r)}{_origen_html(r, mensajes)}</div>' for r in filas)
        bloques += f"<h2>{NOMBRES_SECCION[seccion]} <span class='badge'>{len(filas)}</span></h2>{tarjetas}"
    tirados = "".join(f'<li>{esc(NOMBRES_SECCION.get(d["seccion"], d["seccion"]))}: {esc(d["motivo"])}</li>'
                      for d in v["descartados"])
    alta = espacio.leer_json("alta.json", {}) or {}
    script = ("<script>async function aprobar(b){const a=prompt('Nombre de quien aprueba (como está en el alta):',"
              f"{json.dumps(alta.get('aprobador', ''))});if(!a)return;b.disabled=true;"
              f"const r=await fetch({json.dumps(url(espacio, f'versiones/{pendiente}/aprobar', llave))},"
              "{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({aprobador:a})});"
              "const d=await r.json().catch(()=>({}));document.getElementById('t').textContent=r.ok?'Aprobada y activa ✓':"
              "(d.detail||'No se pudo');b.disabled=false}</script>")
    cuerpo = (f'<div class="card"><span class="badge mid">propuesta</span><h2 style="margin:8px 0 4px">Versión {pendiente}: '
              f'{esc(v["nombre"])}</h2><p class="lede">Autor: {esc(v["autor"])}. Activa hoy: {esc(activa)}. '
              'Cada renglón trae de dónde salió. Nada de esto se enciende hasta que usted lo apruebe.</p></div>'
              f'{bloques}'
              f'<h2>No entraron <span class="badge bad">{len(v["descartados"])}</span></h2>'
              f'<div class="card"><p class="lede">Sin origen que se pueda probar.</p><ul>{tirados}</ul></div>{script}')
    barra = '<button class="btn" onclick="aprobar(this)">Aprobar esta versión</button><span class="toast" id="t"></span>'
    return pagina(espacio, llave or x_tenant_key, "revision", "Perfil", cuerpo, barra=barra)


# --------------------------------------------------------------------------- #
#  Banco y sombra                                                              #
# --------------------------------------------------------------------------- #
@router.get("/espacios/{cliente_id}/banco", response_class=HTMLResponse)
def banco_pagina(cliente_id: str, llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    r = banco.correr(espacio)
    if not r.get("n"):
        cuerpo = f'<div class="card vacio">{esc(r.get("error", "Sin casos."))}</div>'
        return pagina(espacio, llave, "banco", "Banco", cuerpo)
    tono = "ok" if r["errores_caros"] == 0 and r["pasa_k"] == 1 else ("bad" if r["errores_caros"] else "mid")
    filas = "".join(
        f'<tr><td>{esc(f["id"])}</td><td>{esc(f["flujo"])}</td><td>{f["buenas"]}/{f["k"]}</td>'
        f'<td>{"✓" if f["pasa_k"] else "✗"}</td><td>{esc(", ".join(f["caros"]) or "")}</td></tr>' for f in r["filas"])
    s = sombra.medir(espacio)["desarrollo"]
    cuerpo = (f'<div class="grid"><div class="kpi"><b>{r["pasa_k"]:.0%}</b><span>pass^k ({len(r["variantes"])} variantes)</span></div>'
              f'<div class="kpi"><b>{r["errores_caros"]}</b><span>errores caros</span></div>'
              f'<div class="kpi"><b>{r["n"]}</b><span>casos</span></div></div>'
              f'<div class="card" style="margin-top:12px"><span class="badge {tono}">'
              f'{"listo para sombra" if tono == "ok" else "no se enciende"}</span><p class="lede" style="margin-top:8px">'
              'El mismo cliente escrito de cinco formas y un adversario que intenta colar cifras o decir que es '
              'persona. Corre sobre una copia: no gasta API ni toca el historial.</p></div>'
              f'<h2>Casos</h2><div class="card tabla"><table><tr><th>Caso</th><th>Flujo</th><th>Bien</th><th>pass^k</th>'
              f'<th>Caro</th></tr>{filas}</table></div>'
              f'<h2>Sombra</h2><div class="grid"><div class="kpi"><b>{s["n"]}</b><span>borradores medidos</span></div>'
              f'<div class="kpi"><b>{_pct(s.get("cobertura"))}</b><span>cobertura</span></div>'
              f'<div class="kpi"><b>{_pct(s.get("habria_enviado_sin_editar"))}</b><span>se habría enviado tal cual</span></div>'
              f'<div class="kpi"><b>{"sí" if s.get("concluye") else "no"}</b><span>concluye (n ≥ 30)</span></div></div>')
    return pagina(espacio, llave, "banco", "Banco", cuerpo)


def _pct(x) -> str:
    return "—" if x is None else f"{x:.0%}"


# --------------------------------------------------------------------------- #
#  El enlace del negocio: solo vincular (remoto)                               #
# --------------------------------------------------------------------------- #
@router.get("/v/{cliente_id}", response_class=HTMLResponse)
def vincular_negocio(cliente_id: str, t: str | None = None) -> str:
    """Lo único que ve el negocio: el código o el QR, y si ya quedó."""
    try:
        espacio = Espacio(cliente_id)
    except EspacioInvalido as error:
        raise HTTPException(404, "no existe") from error
    if not vinculacion_valida(cliente_id, t):
        raise HTTPException(401, "enlace inválido")
    estado = vinculado.leer_estado(espacio)
    clave = estado.get("estado", "sin_lector")
    tono, titulo, ayuda = ESTADOS.get(clave, ("mid", clave, ""))
    centro = ""
    if clave == "esperando_codigo" and estado.get("codigo"):
        centro = f'<div class="codigo">{esc(estado["codigo"])}</div>'
    elif clave == "esperando_qr" and estado.get("qr"):
        centro = f'<div class="qr">{_qr_svg(estado["qr"])}</div>'
    elif clave in ("conectado", "vinculado"):
        centro = '<div class="codigo" style="color:var(--good);border-color:var(--good)">¡Listo! ✓</div>'
    if clave in ("sin_lector", "arrancando", "error"):
        tono, titulo, ayuda = "mid", "Preparando…", "En unos segundos aparece su código. Esta página se actualiza sola."
    pasos = ('<ol class="pasos">'
             '<li><span class="pt ya">1</span><div>Abra <b>WhatsApp Business</b> en el teléfono del negocio.</div></li>'
             '<li><span class="pt ya">2</span><div>Toque <b>⋮ / Configuración → Dispositivos vinculados → '
             'Vincular un dispositivo</b>.</div></li>'
             '<li><span class="pt ya">3</span><div>' + ("Elija <b>Vincular con número de teléfono</b> y teclee el código."
                                                       if clave == "esperando_codigo" else "Escanee el código QR.") +
             '</div></li><li><span class="pt ya">4</span><div>Deje el teléfono abierto y con internet unos minutos '
             'mientras se copian sus conversaciones.</div></li></ol>')
    alta = espacio.leer_json("alta.json", {}) or {}
    cuerpo = (f'<h1>{esc(alta.get("nombre_comercial") or "Su negocio")}</h1>'
              '<p class="lede">Conecte su WhatsApp Business para preparar su asistente.</p>'
              f'<div class="card"><span class="badge {tono}">{esc(titulo)}</span>'
              f'<p class="lede" style="margin-top:10px">{esc(ayuda)}</p>{centro}</div>'
              f'<div class="card">{pasos}</div>'
              '<div class="card"><b>Su WhatsApp sigue igual.</b> <span class="lede">Este enlace solo lee sus '
              'conversaciones para preparar su asistente: no envía mensajes, no marca nada como leído y usted '
              'puede desvincularlo cuando quiera desde Dispositivos vinculados.</span></div>'
              '<p class="pie">DGED</p>')
    return pagina(espacio, None, "", "Vincular WhatsApp", cuerpo, refrescar=5, navegacion=False)
