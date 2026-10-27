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
from .espacio import Espacio, EspacioInvalido, llave_de_vinculacion, llave_valida, vinculacion_valida

router = APIRouter()

CSS = """
:root{--bg:#101210;--panel:#181b18;--panel2:#20241f;--line:#31382f;--text:#f3efe4;--muted:#a39c8d;
--accent:#e2a85a;--good:#9cbf86;--mid:#e0c36a;--bad:#e07a68;--r:14px}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--text);
font:16px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-text-size-adjust:100%}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.top{position:sticky;top:0;z-index:5;background:#141714ee;backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.top .in{max-width:760px;margin:0 auto;padding:14px 16px 0}
.marca{display:flex;align-items:center;gap:10px}
.marca svg{width:26px;height:26px;fill:none;stroke:var(--accent);stroke-width:1.5}
.kicker{font-size:11px;letter-spacing:.18em;color:var(--accent);text-transform:uppercase}
.marca h1{margin:0;font-size:20px;line-height:1.15}
nav{display:flex;gap:6px;overflow-x:auto;padding:12px 0 10px;scrollbar-width:none}
nav::-webkit-scrollbar{display:none}
nav a{flex:none;padding:7px 13px;border:1px solid var(--line);border-radius:999px;color:var(--text);font-size:14px}
nav a.on{background:var(--accent);border-color:var(--accent);color:#1a1408;font-weight:600}
main{max-width:760px;margin:0 auto;padding:18px 16px 96px}
h2{font-size:18px;margin:26px 0 10px}h2:first-child{margin-top:4px}
.lede{color:var(--muted);margin:0 0 14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:16px;margin:0 0 12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:14px}
.kpi b{display:block;font-size:26px;line-height:1.1}.kpi span{color:var(--muted);font-size:13px}
.pasos{list-style:none;margin:0;padding:0}
.pasos li{display:flex;gap:12px;align-items:flex-start;padding:12px 0;border-bottom:1px solid var(--line)}
.pasos li:last-child{border-bottom:0}
.pt{flex:none;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font-size:14px;font-weight:700;
border:1.5px solid var(--line);color:var(--muted)}
.pt.ok{background:var(--good);border-color:var(--good);color:#0e1a0a}.pt.ya{border-color:var(--accent);color:var(--accent)}
.pasos small{display:block;color:var(--muted)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 16px;border-radius:12px;
border:1px solid var(--accent);background:var(--accent);color:#1a1408;font-weight:600;font-size:15px;cursor:pointer}
.btn.sec{background:transparent;color:var(--accent)}.btn:disabled{opacity:.5}
.acciones{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.badge{display:inline-block;font-size:12px;padding:2px 9px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
.badge.ok{color:var(--good);border-color:#4f6a43}.badge.mid{color:var(--mid);border-color:#6a5d2f}.badge.bad{color:var(--bad);border-color:#6d3a30}
label{display:block;font-size:14px;font-weight:600;margin:14px 0 4px}label small{font-weight:400;color:var(--muted)}
input,textarea{width:100%;padding:12px;border-radius:10px;border:1px solid var(--line);background:var(--panel2);
color:var(--text);font:inherit}textarea{min-height:84px;resize:vertical}
input:focus,textarea:focus{outline:2px solid var(--accent);outline-offset:1px}
.req{color:var(--accent)}
.barra{position:fixed;left:0;right:0;bottom:0;background:#141714ee;backdrop-filter:blur(8px);border-top:1px solid var(--line);padding:12px 16px}
.barra .in{max-width:760px;margin:0 auto;display:flex;gap:10px;align-items:center}
.toast{color:var(--muted);font-size:14px}
.codigo{font:700 38px/1.1 ui-monospace,Menlo,monospace;letter-spacing:.12em;text-align:center;padding:18px;
border:1px dashed var(--accent);border-radius:var(--r);color:var(--accent);background:#1d1a12}
.qr{background:#fff;border-radius:var(--r);padding:14px;max-width:340px;margin:0 auto}.qr svg{width:100%;height:auto;display:block}
.hilo{display:flex;justify-content:space-between;gap:10px;align-items:center}
.hilo .t{color:var(--muted);font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chat{display:flex;flex-direction:column;gap:8px}
.bur{max-width:82%;padding:9px 12px;border-radius:14px;background:var(--panel2);overflow-wrap:anywhere;white-space:pre-wrap}
.bur.n{align-self:flex-end;background:#2c2615;border:1px solid #4b3f20}
.bur small{display:block;color:var(--muted);font-size:11px;margin-top:3px}
.cita{border-left:3px solid var(--accent);padding:2px 0 2px 10px;margin:8px 0 0;color:var(--muted);font-size:14px}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:8px 6px;border-bottom:1px solid var(--line);text-align:left}
.tabla{overflow-x:auto}
.vacío,.vacio{color:var(--muted);text-align:center;padding:26px 10px}
"""
MARCA = ('<svg viewBox="0 0 24 24"><path d="M12 2 21 7v10l-9 5-9-5V7z"/><path d="M12 2v20M3 7l18 10M21 7 3 17"/></svg>')
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
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">{meta}'
            f"<title>{esc(titulo)} · {esc(nombre)}</title><style>{CSS}</style></head><body>"
            f'<header class="top"><div class="in"><div class="marca">{MARCA}<div>'
            f'<div class="kicker">DGED · agente a la medida</div><h1>{esc(nombre)}</h1></div></div>{nav}</div></header>'
            f"<main>{cuerpo}</main>{barra_html}</body></html>")


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
        paso(bool(alta), not alta, 1, "Alta del negocio",
             "Lo básico: qué vende, cómo cobra, quién aprueba." if not alta else "Lista.",
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
            req = '<span class="req"> *</span>' if c != "numero_negocio" else ""
            valor = esc(actual.get(c, ""))
            control = (f'<textarea name="{c}">{valor}</textarea>' if largo
                       else f'<input name="{c}" value="{valor}" autocomplete="off">')
            filas += f'<label>{t}{req} <small>{esc(ayuda)}</small></label>{control}'
        bloques += f'<h2>{titulo}</h2><div class="card">{filas}</div>'
    script = ("<script>const f=document.querySelector('form');f.onsubmit=async e=>{e.preventDefault();"
              "const d=Object.fromEntries(new FormData(f));const t=document.getElementById('t');t.textContent='Guardando…';"
              "const r=await fetch(location.pathname+location.search,{method:'POST',headers:{'Content-Type':'application/json'},"
              "body:JSON.stringify(d)});const j=await r.json().catch(()=>({}));"
              "t.textContent=r.ok?'Guardado ✓ Siga con WhatsApp.':('Falta: '+(j.detail||'revise los campos'))}</script>")
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
    cuerpo = (f'<div class="card"><span class="badge {tono}">{esc(clave)}</span><h2 style="margin:8px 0 4px">{esc(titulo)}</h2>'
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
    cuerpo = (f'<div class="card"><span class="badge {tono}">{esc(titulo)}</span>'
              f'<p class="lede" style="margin-top:8px">{esc(ayuda)}</p>{centro}</div>'
              f'<div class="card">{pasos}</div>'
              '<div class="card"><b>Su WhatsApp sigue igual.</b> <span class="lede">Este enlace solo lee sus '
              'conversaciones para preparar su asistente: no envía mensajes, no marca nada como leído y usted '
              'puede desvincularlo cuando quiera desde Dispositivos vinculados.</span></div>')
    return pagina(espacio, None, "", "Vincular WhatsApp", cuerpo, refrescar=5, navegacion=False)
