"""Las pantallas del espacio: tablero, alta, vincular, conversaciones, revisión y banco.

HTML hecho en el servidor, sin dependencias ni CDN, pensado primero para el
celular (D-020): fuente del sistema, listas agrupadas, barra de pestañas abajo,
la foto y el color del negocio como protagonistas. Toda pantalla pide la llave
(`?llave=`) y todo texto que viene de un cliente se escapa. Los teléfonos de los
clientes finales se enseñan enmascarados (los últimos 4): la pantalla es para
revisar, no para copiar datos. Sin JS todo se lee; JS solo aprueba, guarda,
copia y actualiza en su lugar lo que cambia.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from . import agente, banco, historial, perfil, sombra, vinculado
from . import alta as alta_mod
from .espacio import Espacio, EspacioInvalido, llave_de_vinculacion, llave_valida, vinculacion_valida

router = APIRouter()

# Morelos y casi todo México están en UTC-6 todo el año desde 2022 (sin horario de verano).
HORA_MX = timezone(timedelta(hours=-6))
MARCA_DEFECTO = "#1d1d1f"
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

CSS = """
:root{--marca:#1d1d1f;--marca-ink:#fff;--accent:var(--marca);--accent-ink:var(--marca-ink);
--bg:#f2f2f7;--hoja:#fff;--card:#fff;--fill:rgba(118,118,128,.12);--sep:rgba(60,60,67,.16);
--text:#1d1d1f;--muted:rgba(60,60,67,.62);--good:#248a3d;--warn:#c25e00;--bad:#d70015;
--glass:rgba(249,249,251,.72);--sombra:0 1px 2px rgba(0,0,0,.04),0 10px 30px -12px rgba(0,0,0,.12);
--font:-apple-system,BlinkMacSystemFont,"SF Pro Text","Inter","Segoe UI",Roboto,"Helvetica Neue",sans-serif;
--display:-apple-system,BlinkMacSystemFont,"SF Pro Display","Inter","Segoe UI",Roboto,"Helvetica Neue",sans-serif;
--mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;--r:20px;--ease:cubic-bezier(.2,.8,.2,1)}
@media (prefers-color-scheme:dark){:root{--bg:#000;--hoja:#000;--card:#1c1c1e;--fill:rgba(118,118,128,.24);
--sep:rgba(84,84,88,.55);--text:#f5f5f7;--muted:rgba(235,235,245,.6);--good:#30d158;--warn:#ff9f0a;--bad:#ff453a;
--glass:rgba(22,22,24,.72);--sombra:none;--accent:color-mix(in oklab,var(--marca) 58%,#fff);--accent-ink:#000}}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;background:var(--bg);color:var(--text);font:17px/1.47 var(--font);letter-spacing:-.022em;
-webkit-text-size-adjust:100%;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:var(--accent);text-decoration:none}
svg.ic{width:22px;height:22px;flex:none;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}
h1,h2,h3{font-family:var(--display);margin:0}
.titulo-grande{font:700 34px/1.12 var(--display);letter-spacing:-.03em;margin:4px 0 6px}
.sobre{font-size:13px;font-weight:600;letter-spacing:.01em;color:var(--muted);margin:0}
.lede{color:var(--muted);margin:0 0 18px;font-size:16px;line-height:1.45}
h2.sec{font:700 22px/1.2 var(--display);letter-spacing:-.025em;margin:34px 0 12px}
h2.sec small{font:500 15px var(--font);color:var(--muted);margin-left:6px}
.nota{font-size:13px;color:var(--muted);margin:8px 16px 0;line-height:1.4}
/* --- barra de navegación y pestañas (vidrio) --- */
.barra-nav{position:sticky;top:0;z-index:20;background:var(--glass);backdrop-filter:saturate(180%) blur(20px);
-webkit-backdrop-filter:saturate(180%) blur(20px);border-bottom:.5px solid var(--sep);padding-top:env(safe-area-inset-top)}
.barra-nav .in{max-width:640px;margin:0 auto;height:46px;display:flex;align-items:center;justify-content:center;
padding:0 16px;font-weight:600;font-size:16px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
nav.tabs{position:fixed;left:0;right:0;bottom:0;z-index:30;background:var(--glass);border-top:.5px solid var(--sep);
backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px);
padding:6px 4px env(safe-area-inset-bottom);display:flex;justify-content:center}
nav.tabs .in{display:flex;width:100%;max-width:560px}
nav.tabs a{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;padding:4px 0 6px;font-size:10.5px;
font-weight:500;letter-spacing:0;color:var(--muted);transition:color .2s}
nav.tabs a svg.ic{width:25px;height:25px}nav.tabs a.on{color:var(--accent)}nav.tabs a.on svg.ic{stroke-width:2.1}
.contenido{max-width:640px;margin:0 auto;padding:14px 16px calc(110px + env(safe-area-inset-bottom))}
body.con-accion .contenido{padding-bottom:calc(190px + env(safe-area-inset-bottom))}
.accion{position:fixed;left:0;right:0;bottom:calc(58px + env(safe-area-inset-bottom));z-index:25;padding:10px 16px;
background:var(--glass);backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px);
border-top:.5px solid var(--sep)}
.accion .in{max-width:640px;margin:0 auto;display:flex;gap:10px;align-items:center}
.accion input{flex:1;min-width:0}
/* --- listas agrupadas --- */
.grupo{background:var(--card);border-radius:var(--r);overflow:hidden;box-shadow:var(--sombra);margin:0 0 12px}
.fila{display:flex;align-items:center;gap:14px;min-height:58px;padding:13px 16px;color:inherit;position:relative}
.fila+.fila::before{content:"";position:absolute;top:0;right:0;left:16px;border-top:.5px solid var(--sep)}
.grupo.ico .fila+.fila::before{left:62px}
.fila .txt{flex:1;min-width:0}.fila .txt>b{display:block;font-weight:600;line-height:1.3}
.fila .txt small{display:block;color:var(--muted);font-size:14.5px;line-height:1.38;margin-top:2px;letter-spacing:-.01em}
.fila .txt .linea{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fila .der{color:var(--muted);font-size:14px;text-align:right;flex:none}
.fila svg.chev{width:16px;height:16px;color:var(--sep);stroke-width:2.4;flex:none}
a.fila:active{background:var(--fill)}
.icono{width:32px;height:32px;border-radius:9px;display:grid;place-items:center;flex:none;background:var(--fill);color:var(--accent)}
.icono svg.ic{width:19px;height:19px}
.icono.ok{background:var(--good);color:#fff}.icono.ya{background:var(--accent);color:var(--accent-ink)}
.icono.n{font:600 15px var(--font);color:var(--muted)}
.bloque{background:var(--card);border-radius:var(--r);padding:18px;box-shadow:var(--sombra);margin:0 0 12px}
.bloque>b:first-child{display:block;font-size:17px;margin-bottom:4px}
/* --- cifras --- */
.tiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:0 0 12px}
.tile{background:var(--card);border-radius:18px;padding:14px 16px;box-shadow:var(--sombra);min-width:0}
.tile b{display:block;font:700 30px/1.1 var(--display);letter-spacing:-.03em;font-variant-numeric:tabular-nums;
overflow-wrap:anywhere}
.tile span{color:var(--muted);font-size:13px;letter-spacing:-.005em}
/* --- estado: punto y texto, sin píldoras --- */
.estado{display:inline-flex;align-items:center;gap:7px;font-size:13px;font-weight:600;color:var(--muted)}
.estado::before{content:"";width:8px;height:8px;border-radius:50%;background:currentColor}
.estado.ok{color:var(--good)}.estado.mid{color:var(--warn)}.estado.bad{color:var(--bad)}
.estado.vivo::before{animation:late 1.6s ease-in-out infinite}
@keyframes late{50%{opacity:.25}}
/* --- botones y campos --- */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:50px;padding:0 20px;
border-radius:14px;border:0;background:var(--accent);color:var(--accent-ink);font:600 17px var(--font);
letter-spacing:-.02em;cursor:pointer;white-space:nowrap;transition:transform .15s var(--ease),opacity .15s}
.btn:active{transform:scale(.97);opacity:.88}.btn:disabled{opacity:.45}
.btn.sec{background:var(--fill);color:var(--accent)}.btn.ancho{width:100%}
.btn svg.ic{width:20px;height:20px}
.acciones{display:flex;gap:10px;margin-top:14px}.acciones .btn{flex:1}
.campo{padding:14px 16px;position:relative}.campo+.campo::before{content:"";position:absolute;top:0;right:0;left:16px;
border-top:.5px solid var(--sep)}
.campo label{display:block;font-size:15px;font-weight:600}.campo label small{display:block;font-weight:400;
color:var(--muted);font-size:13.5px;margin:1px 0 0;line-height:1.35}
input,textarea{width:100%;margin-top:8px;padding:12px 14px;border-radius:12px;border:0;background:var(--fill);
color:var(--text);font:17px/1.4 var(--font);letter-spacing:-.02em;outline:none;transition:box-shadow .15s}
input:focus,textarea:focus{box-shadow:0 0 0 2px var(--accent)}
textarea{min-height:104px;resize:vertical}.accion input{margin-top:0}
input[type=color]{width:52px;height:40px;padding:4px;margin:0}
input[type=file]{font-size:15px;color:var(--muted);padding:10px}
input[type=file]::file-selector-button{font:600 15px var(--font);border:0;border-radius:10px;padding:9px 14px;
margin-right:12px;background:var(--accent);color:var(--accent-ink);cursor:pointer}
.req{color:var(--muted);font-weight:400}.toast{color:var(--muted);font-size:14px;line-height:1.3}
/* --- conversaciones --- */
.avatar{width:42px;height:42px;border-radius:50%;flex:none;display:grid;place-items:center;font:600 15px var(--font);
color:#fff;background:linear-gradient(180deg,#a5a5ad,#86868e)}
.grupo.chats .fila+.fila::before{left:72px}
.chat{display:flex;flex-direction:column;gap:3px;padding:6px 0}
.bur{max-width:80%;padding:9px 14px;border-radius:20px;background:var(--card);overflow-wrap:anywhere;white-space:pre-wrap;
box-shadow:var(--sombra);line-height:1.38}
.bur.n{align-self:flex-end;background:var(--accent);color:var(--accent-ink);box-shadow:none}
.meta{font-size:11.5px;color:var(--muted);margin:2px 8px 10px}.meta.n{align-self:flex-end}
/* --- perfil --- */
.cita{margin:12px 0 0;padding:10px 12px;border-radius:12px;background:var(--fill);font-size:14.5px;color:var(--muted)}
.cita small{display:block;font-size:11.5px;font-weight:600;letter-spacing:.02em;margin-bottom:2px}
.cita q{color:var(--text)}
details.origen summary{list-style:none;cursor:pointer;font-size:13px;color:var(--accent);margin-top:4px}
details.origen summary::-webkit-details-marker{display:none}details.origen .cita{margin-top:8px}
.fila .der b{color:var(--text);font-size:16px;font-variant-numeric:tabular-nums}
.punto{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--accent);margin-top:4px}
.bur.borrador{align-self:flex-end;background:transparent;border:1.5px dashed var(--accent);color:var(--text);box-shadow:none}
svg.ic.mini{width:13px;height:13px;vertical-align:-2px}
h2.sec small a{font-size:15px}
.atras{display:inline-block;font-size:17px;margin:2px 0 0;padding:4px 0}
.tarjeta-negocio{display:flex;gap:14px;align-items:center;margin:4px 0 6px}
.tarjeta-negocio b{display:block;font:700 20px/1.2 var(--display);letter-spacing:-.025em}
.tarjeta-negocio small{color:var(--muted);font-size:14.5px}
.portada-mini{width:72px;height:72px;border-radius:18px;flex:none;background:var(--marca) center/cover;display:grid;
place-items:center;color:#fff;font:600 30px var(--display)}
.portada-mini.sin-foto{background:linear-gradient(165deg,var(--marca),color-mix(in oklab,var(--marca) 55%,#000))}
.grupo.datos .fila small{white-space:pre-line}
.ficha{display:grid;grid-template-columns:auto 1fr;gap:6px 16px;margin:0;font-size:16px}
.ficha dt{color:var(--muted)}.ficha dd{margin:0;font-weight:600;overflow-wrap:anywhere}
/* --- vincular --- */
.pasos-bar{display:flex;gap:6px;margin:4px 0 8px}.pasos-bar i{flex:1;height:4px;border-radius:2px;background:var(--fill);
position:relative;overflow:hidden}
.pasos-bar i.ok{background:var(--good)}.pasos-bar i.ya::after{content:"";position:absolute;inset:0;background:var(--accent);
transform-origin:left;animation:carga 2.4s var(--ease) infinite}
@keyframes carga{0%{transform:scaleX(0)}70%,100%{transform:scaleX(1);opacity:0}}
.pasos-nom{display:flex;font-size:12px;color:var(--muted);margin-bottom:18px}.pasos-nom span{flex:1}
.pasos-nom span.on{color:var(--text);font-weight:600}
.codigo{display:flex;gap:5px;justify-content:center;align-items:center;margin:20px 0 14px}
.codigo span{flex:1 1 0;max-width:46px;aspect-ratio:3/4;display:grid;place-items:center;border-radius:12px;
background:var(--fill);font:600 25px var(--mono);letter-spacing:0;color:var(--text)}
.codigo .guion{flex:0 0 10px;height:3px;aspect-ratio:auto;background:var(--muted);border-radius:2px;max-width:10px}
.qr{background:#fff;border-radius:22px;padding:18px;max-width:300px;margin:20px auto 8px;box-shadow:0 18px 50px -20px rgba(0,0,0,.35)}
.qr svg{width:100%;height:auto;display:block}
.mismo-tel{display:none}
@media (pointer:coarse) and (max-width:700px){.mismo-tel{display:block}}
.listo{display:grid;place-items:center;margin:18px 0 6px}.listo svg{width:84px;height:84px}
.listo circle{fill:var(--good)}.listo path{fill:none;stroke:#fff;stroke-width:3.4;stroke-linecap:round;stroke-linejoin:round;
stroke-dasharray:30;stroke-dashoffset:0}
/* --- la página del negocio --- */
body.negocio{background:var(--hoja)}
.marco{max-width:560px;margin:0 auto}
.portada{position:relative;height:min(46vh,400px);min-height:260px;background:var(--marca) center/cover no-repeat;
display:grid;place-items:center;overflow:hidden}
.portada.sin-foto{background:
radial-gradient(120% 85% at 0% 0%,color-mix(in oklab,var(--marca) 55%,#fff) 0,transparent 62%),
radial-gradient(90% 90% at 100% 15%,color-mix(in oklab,var(--marca) 70%,#000) 0,transparent 60%),
linear-gradient(165deg,var(--marca),color-mix(in oklab,var(--marca) 55%,#000))}
.portada::after{content:"";position:absolute;inset:auto 0 0;height:45%;background:linear-gradient(transparent,rgba(0,0,0,.28))}
.monograma{width:96px;height:96px;border-radius:26px;display:grid;place-items:center;color:#fff;
font:600 46px/1 var(--display);letter-spacing:-.03em;background:rgba(255,255,255,.16);
backdrop-filter:blur(24px) saturate(160%);-webkit-backdrop-filter:blur(24px) saturate(160%);
box-shadow:inset 0 0 0 .5px rgba(255,255,255,.45),0 20px 40px -18px rgba(0,0,0,.45)}
.seguro{position:absolute;top:calc(14px + env(safe-area-inset-top));left:16px;z-index:2;display:flex;align-items:center;
gap:6px;color:#fff;font-size:13px;font-weight:600;text-shadow:0 1px 8px rgba(0,0,0,.35)}
.seguro svg.ic{width:15px;height:15px;stroke-width:2.2}
.hoja{position:relative;z-index:3;margin-top:-30px;background:var(--hoja);border-radius:30px 30px 0 0;
padding:26px 20px calc(40px + env(safe-area-inset-bottom))}
.hoja .grupo,.hoja .bloque{background:var(--bg);box-shadow:none}
@media (prefers-color-scheme:dark){.hoja .grupo,.hoja .bloque{background:var(--card)}}
.firma{text-align:center;color:var(--muted);font-size:12px;margin-top:30px;letter-spacing:.02em}
.firma b{font-weight:700;letter-spacing:.08em}
@media (min-width:700px){body.negocio{background:var(--bg)}.marco{margin:40px auto;border-radius:30px;overflow:hidden;
background:var(--hoja);box-shadow:0 30px 80px -30px rgba(0,0,0,.25)}.portada{height:340px}}
.vacio{color:var(--muted);text-align:center;padding:40px 16px}
/* --- movimiento --- */
@media (prefers-reduced-motion:no-preference){
.aparece>*{animation:sube .55s var(--ease) both}.aparece>*:nth-child(2){animation-delay:.04s}
.aparece>*:nth-child(3){animation-delay:.08s}.aparece>*:nth-child(4){animation-delay:.12s}
.aparece>*:nth-child(n+5){animation-delay:.16s}
@keyframes sube{from{opacity:0;transform:translateY(10px)}}
.listo circle{animation:pop .5s var(--ease) both}.listo path{animation:traza .45s .25s var(--ease) both}
@keyframes pop{from{transform:scale(.6);opacity:0}}@keyframes traza{from{stroke-dashoffset:30}}
::view-transition-old(root),::view-transition-new(root){animation-duration:.3s}}
@media (prefers-reduced-motion:reduce){.pasos-bar i.ya::after{animation:none;transform:none;opacity:.6}
.estado.vivo::before{animation:none}}
"""

_ICONOS = {
    "tablero": '<rect x="3.5" y="3.5" width="7" height="7" rx="2"/><rect x="13.5" y="3.5" width="7" height="7" rx="2"/>'
               '<rect x="3.5" y="13.5" width="7" height="7" rx="2"/><rect x="13.5" y="13.5" width="7" height="7" rx="2"/>',
    "enlace": '<path d="M10 14a4.5 4.5 0 0 0 6.4 0l3.2-3.2a4.5 4.5 0 0 0-6.4-6.4L12 5.6"/>'
              '<path d="M14 10a4.5 4.5 0 0 0-6.4 0l-3.2 3.2a4.5 4.5 0 0 0 6.4 6.4l1.2-1.2"/>',
    "chat": '<path d="M20 11.5c0 4.1-3.6 7.5-8 7.5-1.2 0-2.3-.2-3.3-.6L4 20l1.3-3.6C4.5 15 4 13.3 4 11.5 '
            '4 7.4 7.6 4 12 4s8 3.4 8 7.5z"/>',
    "perfil": '<rect x="4.5" y="3.5" width="15" height="17" rx="3"/><path d="M8.5 8.5h7M8.5 12h7M8.5 15.5h4"/>',
    "escudo": '<path d="M12 3.5l7 2.6v5.6c0 4.3-2.9 7.6-7 8.8-4.1-1.2-7-4.5-7-8.8V6.1z"/><path d="M9 12l2 2 4-4"/>',
    "chev": '<path d="M9 5.5l6.5 6.5L9 18.5"/>',
    "ojo": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
    "callado": '<path d="M4.5 5.5h15v10h-9l-4 3.5v-3.5h-2z"/><path d="M3 3l18 18"/>',
    "apagar": '<path d="M12 3.5v8"/><path d="M6.6 7a7.5 7.5 0 1 0 10.8 0"/>',
    "visto": '<circle cx="12" cy="12" r="8.5"/><path d="M8.5 12.2l2.4 2.4 4.8-5"/>',
    "candado": '<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
    "copiar": '<rect x="8.5" y="8.5" width="11" height="11" rx="2.5"/>'
              '<path d="M15.5 8.5v-2a2 2 0 0 0-2-2h-7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h2"/>',
    "compartir": '<path d="M12 3.5v11"/><path d="M8 7.5l4-4 4 4"/>'
                 '<path d="M7.5 11H6a1.5 1.5 0 0 0-1.5 1.5v6A1.5 1.5 0 0 0 6 20h12a1.5 1.5 0 0 0 1.5-1.5v-6A1.5 1.5 0 0 0 18 11h-1.5"/>',
    "foto": '<rect x="3.5" y="5" width="17" height="14" rx="3"/><circle cx="9" cy="10" r="1.6"/><path d="M20.5 15.5l-5-5-9 8.5"/>',
    "chispa": '<path d="M12 3.5l1.9 5.1 5.1 1.9-5.1 1.9L12 17.5l-1.9-5.1L5 10.5l5.1-1.9z"/><path d="M18.5 16v4M16.5 18h4"/>',
    "casa": '<path d="M4 10.5L12 4l8 6.5V19a1.5 1.5 0 0 1-1.5 1.5H15v-6H9v6H5.5A1.5 1.5 0 0 1 4 19z"/>',
    "tienda": '<path d="M4 9.5l1.5-5h13l1.5 5"/><path d="M4 9.5a2.7 2.7 0 0 0 5.3 0 2.7 2.7 0 0 0 5.4 0 2.7 2.7 0 0 0 5.3 0"/>'
              '<path d="M5.5 11.5v8h13v-8"/>',
    "aviso": '<path d="M12 4l9 16H3z"/><path d="M12 10v4.5M12 17.3v.2"/>',
}


def icono(nombre: str, clase: str = "ic") -> str:
    return f'<svg class="{clase}" viewBox="0 0 24 24" aria-hidden="true">{_ICONOS[nombre]}</svg>'


# Cuatro pestañas para administrar (D-021). Alta y WhatsApp viven dentro de Negocio; el taller
# (banco, sombra, historial crudo) no tiene pestaña: es nuestro, no del negocio.
SECCIONES = (("", "Inicio", "casa"), ("conversaciones", "Chats", "chat"), ("revision", "Asistente", "chispa"),
             ("negocio", "Negocio", "tienda"))
_PESTANA = {"alta": "negocio", "vincular": "negocio"}


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


# --------------------------------------------------------------------------- #
#  Marca del negocio: un color y una foto, y nada más                          #
# --------------------------------------------------------------------------- #
IMAGENES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
PORTADA_MAX = 8 * 1024 * 1024


def tipo_de_imagen(datos: bytes) -> str | None:
    """Por los bytes, no por lo que diga el navegador."""
    if datos.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if datos.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "webp"
    return None


def portada(espacio: Espacio) -> Path | None:
    for ext in IMAGENES:
        ruta = espacio.ruta(f"portada.{ext}")
        if ruta.exists():
            return ruta
    return None


def guardar_portada(espacio: Espacio, datos: bytes) -> str:
    """Deja una sola portada en el espacio. Lanza ValueError si no es imagen o pesa de más."""
    if len(datos) > PORTADA_MAX:
        raise ValueError("la foto pesa más de 8 MB")
    ext = tipo_de_imagen(datos)
    if ext is None:
        raise ValueError("no es JPG, PNG ni WebP")
    for otra in IMAGENES:
        if otra != ext and espacio.ruta(f"portada.{otra}").exists():
            espacio.ruta(f"portada.{otra}").unlink()
    ruta = espacio.ruta(f"portada.{ext}")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(datos)
    return ext


def color_de_marca(espacio: Espacio | None) -> str:
    color = str((espacio.config() if espacio else {}).get("marca_color", ""))
    return color.lower() if HEX.match(color) else MARCA_DEFECTO


def _tinta(color: str) -> str:
    """Texto encima del color: blanco salvo que el color sea claro (luminancia relativa, WCAG)."""
    def canal(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#111111" if 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b) > 0.4 else "#ffffff"


# --------------------------------------------------------------------------- #
#  El documento                                                                #
# --------------------------------------------------------------------------- #
_JS_BASE = (
    "<script>function copiarCodigo(b){const c=document.querySelector('[data-codigo]');if(!c||!navigator.clipboard)return;"
    "navigator.clipboard.writeText(c.dataset.codigo.replace(/-/g,'')).then(()=>{const s=b.querySelector('span');"
    "const t=s.textContent;s.textContent='Copiado';setTimeout(()=>s.textContent=t,1800)})}</script>")


def _vivo_js(segundos: int) -> str:
    """Trae la misma página y cambia solo lo marcado `data-vivo`, sin parpadeo ni perder el scroll.
    Sin JS, la `<meta refresh>` dentro de `<noscript>` hace lo mismo a la antigua."""
    return ("<script>(()=>{const s=" + str(int(segundos) * 1000) + ";async function tic(){try{if(!document.hidden){"
            "const r=await fetch(location.href,{cache:'no-store'});if(r.ok){const d=new DOMParser().parseFromString("
            "await r.text(),'text/html');const n=d.querySelector('[data-vivo]'),v=document.querySelector('[data-vivo]');"
            "if(n&&v&&n.innerHTML!==v.innerHTML){const f=()=>v.replaceWith(n);"
            "document.startViewTransition?document.startViewTransition(f):f()}}}}catch(e){}setTimeout(tic,s)}"
            "setTimeout(tic,s)})()</script>")


def _documento(espacio: Espacio | None, titulo: str, cuerpo: str, refrescar: int | None = None,
               clase: str = "") -> str:
    color = color_de_marca(espacio)
    vivo = f'<noscript><meta http-equiv="refresh" content="{int(refrescar)}"></noscript>' if refrescar else ""
    return (f'<!doctype html><html lang="es" style="--marca:{color};--marca-ink:{_tinta(color)}"><head>'
            '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<meta name="color-scheme" content="light dark"><meta name="theme-color" content="{color}">'
            f'<meta name="robots" content="noindex"><title>{esc(titulo)}</title><style>{CSS}</style>{vivo}</head>'
            f'<body class="{clase}">{cuerpo}{_JS_BASE}{_vivo_js(refrescar) if refrescar else ""}</body></html>')


def pagina(espacio: Espacio | None, llave: str | None, activa: str, titulo: str, cuerpo: str,
           refrescar: int | None = None, barra: str = "", navegacion: bool = True, atras: tuple[str, str] | None = None) -> str:
    """Pantalla interna: barra de vidrio con el nombre del negocio, título grande, pestañas abajo.
    `barra` es la acción principal (guardar, aprobar), fija encima de las pestañas."""
    alta = (espacio.leer_json("alta.json", {}) or {}) if espacio else {}
    nombre = alta.get("nombre_comercial") or (espacio.cliente_id if espacio else "DGED")
    tabs = ""
    if espacio and navegacion:
        pestana = _PESTANA.get(activa, activa)
        tabs = ('<nav class="tabs"><div class="in">' + "".join(
            f'<a class="{"on" if s == pestana else ""}" href="{esc(url(espacio, s, llave))}"'
            f'{" aria-current=page" if s == pestana else ""}>{icono(i)}{t}</a>' for s, t, i in SECCIONES)
            + "</div></nav>")
    if refrescar:
        cuerpo = f"<div data-vivo>{cuerpo}</div>"
    accion = f'<div class="accion"><div class="in">{barra}</div></div>' if barra else ""
    html_cuerpo = (f'<header class="barra-nav"><div class="in">{esc(nombre)}</div></header>'
                   f'<main class="contenido aparece">'
                   + (f'<a class="atras" href="{esc(atras[1])}">‹ {esc(atras[0])}</a>' if atras else "")
                   + f'<h1 class="titulo-grande">{esc(titulo)}</h1>{cuerpo}</main>'
                   f"{accion}{tabs}")
    return _documento(espacio, f"{titulo} · {nombre}", html_cuerpo, refrescar, "con-accion" if barra else "")


def _enmascarar(telefono: str) -> str:
    return "•••• " + telefono[-4:] if len(telefono) > 4 else telefono


def _hora(ts: int) -> str:
    return datetime.fromtimestamp(ts, HORA_MX).strftime("%d/%m/%Y %H:%M") if ts else ""


def _cuando(ts: int) -> str:
    """Como en Mensajes: la hora si fue hoy, la fecha corta si no."""
    if not ts:
        return ""
    momento = datetime.fromtimestamp(ts, HORA_MX)
    return momento.strftime("%H:%M") if momento.date() == datetime.now(HORA_MX).date() else momento.strftime("%d/%m/%y")


def _fila(titulo: str, detalle: str = "", href: str | None = None, ico: str = "", der: str = "",
          extra: str = "") -> str:
    """Un renglón de lista agrupada. `titulo` y `detalle` ya vienen escapados."""
    etiqueta = "a" if href else "div"
    destino = f' href="{esc(href)}"' if href else ""
    chev = icono("chev", "ic chev") if href else ""
    det = f"<small>{detalle}</small>" if detalle else ""
    der_html = f'<span class="der">{der}</span>' if der else ""
    return (f'<{etiqueta} class="fila"{destino}>{ico}<div class="txt"><b>{titulo}</b>{det}{extra}</div>'
            f"{der_html}{chev}</{etiqueta}>")


# --------------------------------------------------------------------------- #
#  Lo que sirve para administrar                                               #
# --------------------------------------------------------------------------- #
MODOS = {
    "sombra": ("mid", "Aprendiendo", "Todavía no le contesta a nadie. Lee sus chats y prepara borradores para que "
               "usted vea cómo respondería."),
    "sin_cifra": ("ok", "Contesta lo sencillo", "Responde lo que no lleva precio. Las cotizaciones esperan su sí."),
}


def _modo(espacio: Espacio) -> tuple[str, str, str]:
    return MODOS.get(espacio.config().get("encendido", "sombra"), MODOS["sombra"])


def _sin_responder(hilos: dict) -> list[str]:
    """Conversaciones cuyo último mensaje es del cliente."""
    return [h for h, ms in hilos.items() if ms and not ms[-1].del_negocio]


def _por_aprobar(espacio: Espacio) -> list:
    return [s for s in agente.salidas(espacio) if s.requiere_aprobacion and not s.aprobada_por]


def _pendiente(espacio: Espacio) -> int | None:
    activa = perfil.version_activa(espacio)
    return next((n for n in reversed(perfil.versiones(espacio)) if activa is None or n > activa), None)


def _saludo() -> str:
    hora = datetime.now(HORA_MX).hour
    return "Buenos días" if hora < 12 else ("Buenas tardes" if hora < 19 else "Buenas noches")


def _filas_chats(espacio: Espacio, llave: str | None, hilos: dict, orden: list) -> str:
    abiertos = set(_sin_responder(hilos))
    return "".join(
        _fila(esc(_enmascarar(h)), f'<span class="linea" style="display:block">{esc((ms[-1].texto or "")[:90])}</span>',
              url(espacio, "conversaciones", llave, hilo=h), f'<span class="avatar">{esc(h[-2:])}</span>',
              f"{esc(_cuando(ms[-1].ts))}<br>" + ('<span class="punto" title="Sin responder"></span>' if h in abiertos
                                                  else str(len(ms))))
        for h, ms in orden)


# --------------------------------------------------------------------------- #
#  Inicio                                                                      #
# --------------------------------------------------------------------------- #
@router.get("/espacios/{cliente_id}", response_class=HTMLResponse)
def tablero(cliente_id: str, llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    alta = espacio.leer_json("alta.json") or {}
    estado = vinculado.leer_estado(espacio)
    hilos = historial.hilos(espacio)
    n_msj = sum(len(v) for v in hilos.values())
    conectado = estado.get("estado") in ("conectado", "vinculado")
    abiertos = _sin_responder(hilos)
    cotizaciones = _por_aprobar(espacio)
    pendiente = _pendiente(espacio)

    tono, titulo, texto = _modo(espacio)
    modo = (f'<div class="bloque"><span class="estado {tono}">{titulo}</span>'
            f'<h2 style="font-size:22px;letter-spacing:-.025em;margin:8px 0 4px">Su asistente</h2>'
            f'<p class="lede" style="margin:0">{texto}</p></div>')

    def ico(nombre: str, clase: str = "") -> str:
        return f'<span class="icono {clase}">{icono(nombre)}</span>'

    tareas = []
    if not alta or alta_mod.faltan(alta):
        tareas.append(_fila("Complete los datos del negocio",
                            ("Falta: " + esc(", ".join(alta_mod.faltan(alta))) + ".") if alta else "Qué ofrece, cómo cobra, quién aprueba.",
                            url(espacio, "alta", llave), ico("tienda", "ya")))
    if not conectado:
        tareas.append(_fila("Conecte su WhatsApp", "Para que su asistente aprenda de cómo atiende usted.",
                            url(espacio, "negocio", llave), ico("enlace", "ya")))
    if pendiente is not None:
        tareas.append(_fila("Revise lo que aprendió su asistente", "Hay una versión nueva lista para su aprobación.",
                            url(espacio, "revision", llave), ico("chispa", "ya")))
    if cotizaciones:
        tareas.append(_fila(f"{len(cotizaciones)} cotización{'es' if len(cotizaciones) > 1 else ''} espera{'n' if len(cotizaciones) > 1 else ''} su sí",
                            "Nada con precio sale sin su aprobación.", url(espacio, "conversaciones", llave),
                            ico("visto", "ya")))
    if abiertos:
        tareas.append(_fila(f"{len(abiertos)} chat{'s' if len(abiertos) > 1 else ''} sin responder",
                            "El último mensaje es del cliente.", url(espacio, "conversaciones", llave), ico("chat", "ya")))
    pendientes = ("".join(tareas) if tareas
                  else _fila("Todo al día", "No hay nada esperando por usted.", ico=ico("visto", "ok")))

    cifras = (f'<div class="tiles"><div class="tile"><b>{len(hilos)}</b><span>conversaciones</span></div>'
              f'<div class="tile"><b>{len(abiertos)}</b><span>sin responder</span></div>'
              f'<div class="tile"><b>{n_msj}</b><span>mensajes leídos</span></div>'
              f'<div class="tile"><b>{len(cotizaciones)}</b><span>cotizaciones por aprobar</span></div></div>')
    recientes = sorted(hilos.items(), key=lambda kv: -kv[1][-1].ts)[:3]
    chats = (f'<h2 class="sec">Últimos chats<small><a href="{esc(url(espacio, "conversaciones", llave))}">Ver todos</a>'
             f'</small></h2><div class="grupo chats">{_filas_chats(espacio, llave, hilos, recientes)}</div>'
             if recientes else "")
    nombre = alta.get("nombre_comercial") or espacio.cliente_id
    cuerpo = (f'<p class="lede" style="margin-top:-2px">{esc(nombre)}</p>{modo}'
              f'<h2 class="sec">Pendiente</h2><div class="grupo ico">{pendientes}</div>'
              f'<h2 class="sec">Sus chats</h2>{cifras}{chats}')
    return pagina(espacio, llave, "", _saludo(), cuerpo)


# --------------------------------------------------------------------------- #
#  Chats                                                                       #
# --------------------------------------------------------------------------- #
VIAS = {"persona": "Se lo pasaría a usted", "cotizador": "Cotización preparada"}


@router.get("/espacios/{cliente_id}/conversaciones", response_class=HTMLResponse)
def conversaciones(cliente_id: str, llave: str | None = None, hilo: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    hilos = historial.hilos(espacio)
    if hilo and hilo in hilos:
        propuestas: dict[str, list] = {}
        for s in agente.salidas(espacio):
            if s.hilo == hilo and s.via != "silencio" and (s.texto or s.borrador):
                propuestas.setdefault(s.responde_a, []).append(s)
        partes = []
        for m in hilos[hilo]:
            partes.append(f'<div class="bur {"n" if m.del_negocio else ""}">{esc(m.texto or "[" + m.tipo + " sin texto]")}</div>'
                          f'<div class="meta {"n" if m.del_negocio else ""}">{"negocio" if m.del_negocio else "cliente"} · '
                          f"{_hora(m.ts)}</div>")
            for s in propuestas.get(m.id, []):
                espera = s.requiere_aprobacion and not s.aprobada_por
                aviso = ("Espera su aprobación" if espera else
                         f"Aprobada por {esc(s.aprobada_por)}" if s.aprobada_por else
                         VIAS.get(s.via, "Su asistente habría contestado"))
                boton = (f'<button class="btn ancho" style="min-height:42px;font-size:15px;margin-top:10px;display:flex" '
                         f'onclick="aprobarSalida(this,{esc(json.dumps(s.id))})">Aprobar</button>' if espera else "")
                partes.append(f'<div class="bur borrador"><div>{esc(s.texto or s.borrador)}</div>{boton}</div>'
                              f'<div class="meta n">{icono("chispa", "ic mini")} {aviso}</div>')
        alta = espacio.leer_json("alta.json", {}) or {}
        script = ("<script>async function aprobarSalida(b,id){b.disabled=true;"
                  f"const r=await fetch({json.dumps(url(espacio, 'salidas/', llave))}.replace('salidas/?','salidas/'+id+'/aprobar?'),"
                  "{method:'POST',headers:{'Content-Type':'application/json'},"
                  f"body:JSON.stringify({{aprobador:{json.dumps(alta.get('aprobador', ''))}}})}});"
                  "const d=await r.json().catch(()=>({}));b.textContent=r.ok?(d.enviada?'Enviada ✓':'Aprobada ✓'):"
                  "(d.detail||'No se pudo');if(!r.ok)b.disabled=false}</script>")
        n = len(hilos[hilo])
        cuerpo = (f'<p class="lede">{n} mensaje{"" if n == 1 else "s"}</p><div class="chat">{"".join(partes)}</div>{script}')
        return pagina(espacio, llave, "conversaciones", _enmascarar(hilo), cuerpo,
                      atras=("Chats", url(espacio, "conversaciones", llave)))
    orden = sorted(hilos.items(), key=lambda kv: -kv[1][-1].ts)
    n_abiertos = len(_sin_responder(hilos))
    cuerpo = (f'<p class="lede">{len(hilos)} conversaciones'
              + (f', {n_abiertos} sin responder' if n_abiertos else "") + '. Los teléfonos van enmascarados.</p>'
              + (f'<div class="grupo chats">{_filas_chats(espacio, llave, hilos, orden)}</div>' if orden
                 else '<div class="grupo vacio">Todavía no hay mensajes. Conecte su WhatsApp en Negocio.</div>'))
    return pagina(espacio, llave, "conversaciones", "Chats", cuerpo)


# --------------------------------------------------------------------------- #
#  Asistente: lo que sabe, en palabras del negocio                             #
# --------------------------------------------------------------------------- #
NOMBRES_SECCION = {"datos": "Sus propiedades", "temporadas": "Temporadas", "voz": "Así contesta",
                   "reglas": "Precios", "faq": "Respuestas", "escala": "Se lo pasa a usted"}
_DIAS = {"entre_semana": "entre semana", "fin_de_semana": "fin de semana"}


def _origen_html(renglon: dict, mensajes: dict) -> str:
    """Cada dato con el mensaje de donde salió (invariante), plegado para no estorbar."""
    o = renglon.get("origen", {}) or {}
    cita = esc(o.get("cita", ""))
    if o.get("tipo") == "mensaje" and (m := mensajes.get(o.get("id"))):
        fuente = f'mensaje del {"negocio" if m.del_negocio else "cliente"}: {esc(m.texto or "")}'
    else:
        fuente = f'{esc(o.get("tipo", "?"))} {esc(o.get("campo") or o.get("nombre") or "")}'
    return (f'<details class="origen"><summary>De dónde salió</summary><div class="cita"><q>{cita}</q><br>'
            f"{fuente}</div></details>")


def _nombre_propiedad(pid: str, alta: dict) -> str:
    for nombre in alta.get("propiedades", []) or []:
        if str(pid).casefold() in str(nombre).casefold():
            return str(nombre)[:1].upper() + str(nombre)[1:]
    return str(pid).replace("_", " ").capitalize()


def _regla(r: dict) -> tuple[str, str]:
    """(qué, cuánto) para la lista de precios."""
    from .cotizador import pesos
    monto = pesos(r["monto_centavos"]) if r.get("monto_centavos") is not None else ""
    tipo = r.get("tipo", "")
    if tipo == "noche":
        que = "Noche" + (f" {_DIAS.get(r['dias'], r['dias'])}" if r.get("dias") else "")
        que += f" · temporada {r['temporada']}" if r.get("temporada") else ""
        return que, monto
    if tipo == "persona_extra":
        return (f"Persona extra (arriba de {r['personas']})" if r.get("personas") else "Persona extra"), monto
    if tipo == "capacidad":
        return "Capacidad", f"{r.get('personas', '')} personas"
    if tipo == "minimo_noches":
        return "Estancia mínima", f"{r.get('noches', '')} noches"
    if tipo == "anticipo":
        return "Anticipo", f"{r.get('pct', '')} %" if r.get("pct") is not None else monto
    nombres = {"evento": "Evento", "deposito": "Depósito"}
    resto = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in r.items()
                      if k not in ("origen", "tipo", "propiedad", "monto_centavos"))
    return nombres.get(tipo, tipo.replace("_", " ").capitalize()) + (f" · {resto}" if resto else ""), monto


def _seccion_html(seccion: str, filas: list[dict], mensajes: dict, alta: dict) -> str:
    def fila(titulo: str, detalle: str, r: dict, der: str = "") -> str:
        return _fila(titulo, detalle, der=der, extra=_origen_html(r, mensajes))

    if seccion == "reglas":
        grupos: dict[str, list] = {}
        for r in filas:
            grupos.setdefault(str(r.get("propiedad", "")), []).append(r)
        salida = ""
        for pid, rs in grupos.items():
            renglones = "".join(fila(esc(q), "", r, f"<b>{esc(c)}</b>") for r in rs for q, c in [_regla(r)])
            salida += f'<p class="sobre" style="margin:14px 4px 6px">{esc(_nombre_propiedad(pid, alta))}</p><div class="grupo">{renglones}</div>'
        return salida
    if seccion == "datos":
        renglones = "".join(fila(esc(f'{_nombre_propiedad(r.get("id", ""), alta) if r.get("objeto") == "Propiedad" else str(r.get("id", "")).capitalize()}'
                                     f' · {str(r.get("campo", "")).replace("_", " ")}'), esc(r.get("valor")), r) for r in filas)
    elif seccion == "temporadas":
        def fecha(t: str) -> str:
            mes, dia = (t or "-").split("-", 1) if "-" in (t or "") else ("", t)
            return f"{dia}/{mes}" if mes else esc(t)
        renglones = "".join(fila(esc(f"Temporada {r.get('nombre', '')}"),
                                 esc(f"del {fecha(r.get('desde', ''))} al {fecha(r.get('hasta', ''))}"), r) for r in filas)
    elif seccion == "voz":
        renglones = "".join(fila(f"«{esc(r.get('frase'))}»", "", r) for r in filas)
    elif seccion == "faq":
        renglones = "".join(fila(esc(r.get("pregunta")), esc(r.get("respuesta")), r) for r in filas)
    elif seccion == "escala":
        renglones = "".join(fila(esc(str(r.get("caso", "")).capitalize()), "", r) for r in filas)
    else:
        renglones = "".join(fila(esc(", ".join(f"{k}: {v}" for k, v in r.items() if k != "origen")), "", r) for r in filas)
    return f'<div class="grupo">{renglones}</div>'


@router.get("/espacios/{cliente_id}/revision", response_class=HTMLResponse)
def revision(cliente_id: str, x_tenant_key: str | None = Header(default=None), llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, x_tenant_key or llave)
    llave = llave or x_tenant_key
    activa = perfil.version_activa(espacio)
    pendiente = _pendiente(espacio)
    tono, titulo, texto = _modo(espacio)
    modo = (f'<div class="bloque"><span class="estado {tono}">{titulo}</span>'
            f'<p class="lede" style="margin:8px 0 0">{texto}</p></div>')
    mostrar = pendiente if pendiente is not None else activa
    if mostrar is None:
        cuerpo = (modo + '<div class="grupo vacio">Sin propuestas todavía. Cuando su WhatsApp esté conectado, '
                  'armamos con sus propias conversaciones lo que su asistente debe saber, y usted lo aprueba.</div>')
        return pagina(espacio, llave, "revision", "Asistente", cuerpo)
    v = perfil.leer_version(espacio, mostrar)
    mensajes = historial.por_id(espacio)
    alta = espacio.leer_json("alta.json", {}) or {}
    orden = ("reglas", "datos", "temporadas", "faq", "escala", "voz")
    bloques = "".join(
        f'<h2 class="sec">{NOMBRES_SECCION[s]}<small>{len(v["perfil"][s])}</small></h2>'
        + _seccion_html(s, v["perfil"][s], mensajes, alta)
        for s in orden if s in perfil.SECCIONES and v["perfil"].get(s))
    barra = ""
    if pendiente is not None:
        aviso = ('<div class="bloque"><span class="estado mid vivo">Por revisar</span><h2 style="font-size:22px;'
                 'letter-spacing:-.025em;margin:8px 0 4px">Lo que aprendió de sus chats</h2>'
                 '<p class="lede" style="margin:0">Revise precios y respuestas. Cada dato dice de qué mensaje salió. '
                 'Nada de esto se usa hasta que usted lo apruebe.</p></div>')
        tirados = "".join(_fila(esc(NOMBRES_SECCION.get(d["seccion"], d["seccion"])), esc(d["motivo"]))
                          for d in v["descartados"])
        fuera = (f'<details class="origen" style="margin-top:22px"><summary>No entraron ({len(v["descartados"])}): '
                 f'sin un mensaje que los pruebe</summary><div class="grupo" style="margin-top:8px">{tirados}</div></details>'
                 if v["descartados"] else "")
        script = ("<script>async function aprobar(b){const a=document.getElementById('apr').value.trim();"
                  "const t=document.getElementById('t');if(!a){t.textContent='Escriba quién aprueba.';return}b.disabled=true;"
                  f"const r=await fetch({json.dumps(url(espacio, f'versiones/{pendiente}/aprobar', llave))},"
                  "{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({aprobador:a})});"
                  "const d=await r.json().catch(()=>({}));t.textContent=r.ok?'Aprobado ✓':"
                  "(d.detail||'No se pudo');if(r.ok)setTimeout(()=>location.reload(),900);b.disabled=false}</script>")
        cuerpo = aviso + bloques + fuera + script + '<p class="toast" id="t" style="margin-top:12px"></p>'
        barra = (f'<input id="apr" value="{esc(alta.get("aprobador", ""))}" placeholder="Quién aprueba" '
                 'aria-label="Nombre de quien aprueba, como está en el alta">'
                 '<button class="btn" onclick="aprobar(this)">Aprobar</button>')
    else:
        cuerpo = modo + '<p class="nota" style="margin:0 4px 4px">Sin propuestas nuevas. Esto es lo que usa hoy.</p>' + bloques
    return pagina(espacio, llave, "revision", "Asistente", cuerpo, barra=barra)


# --------------------------------------------------------------------------- #
#  Negocio: WhatsApp, marca y datos                                            #
# --------------------------------------------------------------------------- #
_JS_FOTO = (
    # La foto se achica en el teléfono (2000 px, JPG) antes de subir: menos datos, misma portada.
    "<script>document.getElementById('c-foto').onchange=async e=>{const a=e.target.files[0];if(!a)return;"
    "const tf=document.getElementById('tf');tf.textContent='Subiendo…';let cuerpo=a,tipo=a.type;"
    "try{const b=await createImageBitmap(a);const k=Math.min(1,2000/Math.max(b.width,b.height));"
    "const c=document.createElement('canvas');c.width=Math.round(b.width*k);c.height=Math.round(b.height*k);"
    "c.getContext('2d').drawImage(b,0,0,c.width,c.height);"
    "cuerpo=await new Promise(r=>c.toBlob(r,'image/jpeg',.84));tipo='image/jpeg'}catch(_){}"
    "const r=await fetch(document.getElementById('c-foto').dataset.u,{method:'POST',"
    "headers:{'Content-Type':tipo},body:cuerpo});const j=await r.json().catch(()=>({}));"
    "if(r.ok){const p=document.getElementById('pv');p.style.backgroundImage='url('+URL.createObjectURL(cuerpo)+')';"
    "tf.textContent='Portada lista ✓'}else{tf.textContent='No se subió: '+(j.detail||'intente con otra foto')}};"
    "document.getElementById('c-color').onchange=async e=>{const tf=document.getElementById('tc');"
    "const r=await fetch(e.target.dataset.u,{method:'POST',headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify({color:e.target.value})});tf.textContent=r.ok?'Guardado ✓':'No se guardó';"
    "if(r.ok)document.documentElement.style.setProperty('--marca',e.target.value)}</script>")


@router.get("/espacios/{cliente_id}/negocio", response_class=HTMLResponse)
def negocio(cliente_id: str, llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    alta = espacio.leer_json("alta.json", {}) or {}
    nombre = alta.get("nombre_comercial") or espacio.cliente_id
    estado = vinculado.leer_estado(espacio)
    clave = estado.get("estado", "sin_lector")
    tono, titulo_wa, _ = ESTADOS.get(clave, ("mid", clave, ""))
    if clave in ("sin_lector", "arrancando", "error"):
        tono, titulo_wa = "mid", "Sin conectar"
    foto = portada(espacio)
    fondo = (f'background-image:url(&quot;{esc(url(espacio, "portada", llave, v=int(foto.stat().st_mtime)))}&quot;)'
             if foto else "")
    tarjeta = (f'<div class="tarjeta-negocio"><div class="portada-mini{"" if foto else " sin-foto"}" id="pv" style="{fondo}">'
               f'{"" if foto else esc(nombre.strip()[:1].upper())}</div><div><b>{esc(nombre)}</b>'
               f'<small>{esc(alta.get("giro", ""))}</small></div></div>')
    enlace = f"/v/{espacio.cliente_id}?t={llave_de_vinculacion(espacio.cliente_id)}"
    telefono = "".join(c for c in str(alta.get("aprobador_telefono", "")) if c.isdigit())
    whatsapp = (
        '<h2 class="sec">WhatsApp</h2><div class="grupo ico">'
        + _fila("WhatsApp Business", f'<span class="estado {tono}">{esc(titulo_wa)}</span>', url(espacio, "vincular", llave),
                f'<span class="icono">{icono("enlace")}</span>')
        + '</div><div class="bloque"><b>Enlace para conectar</b><p class="lede" style="margin-bottom:0">Ábralo en otra '
        'pantalla o mándeselo a quien tenga el teléfono del negocio. Solo sirve para conectar.</p>'
        f'<input readonly id="enl" value="{esc(enlace)}" data-ruta="{esc(enlace)}" aria-label="Enlace para conectar">'
        f'<div class="acciones"><button class="btn sec" onclick="compartir()">{icono("compartir")}Compartir</button>'
        f'<a class="btn" id="wa" data-tel="{esc(telefono)}" href="#">{icono("chat")}WhatsApp</a></div></div>'
        "<script>const e=document.getElementById('enl');e.value=location.origin+e.dataset.ruta;"
        "const w=document.getElementById('wa');w.href='https://wa.me/'+w.dataset.tel+'?text='+encodeURIComponent("
        "'Para conectar el WhatsApp del negocio, abra este enlace y siga los pasos: '+e.value);"
        "function compartir(){if(navigator.share){navigator.share({url:e.value}).catch(()=>{})}"
        "else if(navigator.clipboard){navigator.clipboard.writeText(e.value).then(()=>e.select())}}</script>")
    marca = (
        '<h2 class="sec">Su marca</h2><div class="grupo">'
        '<div class="campo"><label for="c-color">Color <small>El de su logo o su volante.</small></label>'
        '<div style="display:flex;gap:12px;align-items:center;margin-top:8px">'
        f'<input type="color" id="c-color" value="{color_de_marca(espacio)}" data-u="{esc(url(espacio, "marca", llave))}">'
        '<span class="toast" id="tc"></span></div></div>'
        '<div class="campo"><label for="c-foto">Foto de portada <small>Una foto real del lugar. JPG, PNG o WebP.'
        '</small></label><input type="file" id="c-foto" accept="image/jpeg,image/png,image/webp" '
        f'data-u="{esc(url(espacio, "portada", llave))}"><p class="toast" id="tf"></p></div></div>')
    datos = "".join(
        _fila(t, esc("\n".join(alta[c]) if isinstance(alta.get(c), list) else alta.get(c, "")) or
              '<span style="color:var(--warn)">Falta</span>')
        for _, campos in CAMPOS_ALTA for c, t, _, _ in campos if c not in ("nombre_comercial", "numero_negocio"))
    cuerpo = (tarjeta + whatsapp + marca
              + f'<h2 class="sec">Datos del negocio<small><a href="{esc(url(espacio, "alta", llave))}">Editar</a></small></h2>'
              f'<div class="grupo datos">{datos}</div>' + _JS_FOTO)
    return pagina(espacio, llave, "negocio", "Negocio", cuerpo)


# --------------------------------------------------------------------------- #
#  Alta (se edita desde Negocio)                                               #
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
            control = (f'<textarea name="{c}" id="c-{c}">{valor}</textarea>' if largo
                       else f'<input name="{c}" id="c-{c}" value="{valor}" autocomplete="off">')
            filas += f'<div class="campo"><label for="c-{c}">{t}{req} <small>{esc(ayuda)}</small></label>{control}</div>'
        bloques += f'<h2 class="sec">{titulo}</h2><div class="grupo">{filas}</div>'
    script = ("<script>const f=document.querySelector('form');f.onsubmit=async e=>{e.preventDefault();"
              "const d=Object.fromEntries(new FormData(f));const t=document.getElementById('t');t.textContent='Guardando…';"
              "const r=await fetch(location.pathname+location.search,{method:'POST',headers:{'Content-Type':'application/json'},"
              "body:JSON.stringify(d)});const j=await r.json().catch(()=>({}));"
              "t.textContent=r.ok?(j.faltan&&j.faltan.length?'Guardado ✓ Falta: '+j.faltan.join(', '):'Guardado ✓'):"
              "('No se guardó: '+(j.detail||'revise los campos'))}</script>")
    cuerpo = ('<p class="lede">Su asistente aprende de aquí y de sus chats. Escríbalo como se lo diría a un cliente.</p>'
              f'<form id="alta">{bloques}</form>{script}')
    barra = '<button class="btn" form="alta">Guardar</button><span class="toast" id="t"></span>'
    return pagina(espacio, llave, "alta", "Datos del negocio", cuerpo, barra=barra,
                  atras=("Negocio", url(espacio, "negocio", llave)))


@router.get("/espacios/{cliente_id}/portada")
def portada_interna(cliente_id: str, llave: str | None = None):
    espacio = _espacio(cliente_id, llave)
    return _servir_portada(espacio)


def _servir_portada(espacio: Espacio):
    ruta = portada(espacio)
    if ruta is None:
        raise HTTPException(404, "sin portada")
    return FileResponse(ruta, media_type=IMAGENES[ruta.suffix[1:]],
                        headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"})


# --------------------------------------------------------------------------- #
#  Vincular (desde Negocio)                                                    #
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


def _codigo_html(codigo: str) -> str:
    """El código de 8 en casillas, como el que pide WhatsApp; el texto entero queda para lectores y copiar."""
    celdas = "".join('<span class="guion"></span>' if c == "-" else f"<span>{esc(c)}</span>" for c in codigo)
    return (f'<div class="codigo" role="img" aria-label="Código {esc(codigo)}" data-codigo="{esc(codigo)}">{celdas}</div>'
            f'<button class="btn sec ancho" type="button" onclick="copiarCodigo(this)">{icono("copiar")}'
            "<span>Copiar código</span></button>")


def _listo_svg() -> str:
    return ('<div class="listo"><svg viewBox="0 0 84 84" aria-hidden="true"><circle cx="42" cy="42" r="42"/>'
            '<path d="M27 43l10 10 20-21"/></svg></div>')


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
        centro = _codigo_html(estado["codigo"])
    elif clave == "esperando_qr" and estado.get("qr"):
        centro = f'<div class="qr">{_qr_svg(estado["qr"])}</div>'
    detalle = f'<p class="nota" style="margin:8px 0 0">{esc(estado.get("detalle", ""))}</p>' if estado.get("detalle") else ""
    vivo = " vivo" if clave in ("arrancando", "esperando_qr", "esperando_codigo", "vinculado", "conectado") else ""
    cuerpo = (f'<div class="bloque"><span class="estado {tono}{vivo}">WhatsApp</span>'
              f'<h2 style="font-size:22px;letter-spacing:-.025em;margin:8px 0 4px">{esc(titulo)}</h2>'
              f'<p class="lede" style="margin:0">{esc(ayuda)}</p>{detalle}{centro}</div>'
              f'<div class="tiles"><div class="tile"><b>{n}</b><span>mensajes guardados</span></div>'
              f'<div class="tile"><b>{len(hilos)}</b><span>conversaciones</span></div></div>'
              '<div class="grupo ico">'
              + _fila("Este servicio solo LEE.", "No envía mensajes, no marca como leído y no aparece en línea. "
                      "Al terminar, puede desvincularlo desde el teléfono.", ico=f'<span class="icono">{icono("ojo")}</span>')
              + "</div>")
    return pagina(espacio, llave, "vincular", "WhatsApp", cuerpo, refrescar=5,
                  atras=("Negocio", url(espacio, "negocio", llave)))


# --------------------------------------------------------------------------- #
#  Taller: lo nuestro. Sin pestaña; el negocio no lo ve ni lo necesita         #
# --------------------------------------------------------------------------- #
_JS_POST = ("<script>async function correr(b,u){b.disabled=true;const t=document.getElementById('t');"
            "t.textContent='Trabajando… puede tardar un par de minutos.';"
            "const r=await fetch(u,{method:'POST'});const d=await r.json().catch(()=>({}));"
            "t.textContent=r.ok?'Listo. Abra Asistente para revisar.':(d.detail||'No se pudo.');b.disabled=false}</script>")


@router.get("/espacios/{cliente_id}/banco", response_class=HTMLResponse)
def banco_pagina(cliente_id: str, llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    herramientas = (
        '<div class="bloque"><b>Proponer perfil</b><p class="lede">Una pasada del modelo grande sobre el historial. '
        'Deja una propuesta; la aprueba el dueño en Asistente.</p><button class="btn ancho" onclick="correr(this,'
        f'\'{esc(url(espacio, "simbiosis", llave))}\')">{icono("chispa")}Proponer perfil</button>'
        '<p class="toast" id="t"></p></div>' + _JS_POST
        + '<div class="grupo ico">'
        + _fila("Descargar historial", "Un mensaje por renglón (JSONL).", url(espacio, "historial.jsonl", llave),
                f'<span class="icono">{icono("compartir")}</span>') + "</div>")
    r = banco.correr(espacio)
    if not r.get("n"):
        cuerpo = herramientas + f'<div class="grupo vacio">{esc(r.get("error", "Sin casos."))}</div>'
        return pagina(espacio, llave, "banco", "Taller", cuerpo)
    tono = "ok" if r["errores_caros"] == 0 and r["pasa_k"] == 1 else ("bad" if r["errores_caros"] else "mid")
    filas = "".join(
        _fila(esc(f["id"]), esc(f["flujo"]) + (f' · <span style="color:var(--bad)">{esc(", ".join(f["caros"]))}</span>'
                                                if f["caros"] else ""),
              ico=(f'<span class="icono ok">{icono("visto")}</span>' if f["pasa_k"]
                   else f'<span class="icono" style="color:var(--bad)">{icono("aviso")}</span>'),
              der=f'{f["buenas"]}/{f["k"]}')
        for f in r["filas"])
    s = sombra.medir(espacio)["desarrollo"]
    cuerpo = (herramientas
              + f'<h2 class="sec">Banco</h2><div class="bloque"><span class="estado {tono}">'
              f'{"listo para sombra" if tono == "ok" else "no se enciende"}</span><p class="lede" style="margin:8px 0 0">'
              'El mismo cliente escrito de cinco formas y un adversario que intenta colar cifras o decir que es '
              'persona. Corre sobre una copia: no gasta API ni toca el historial.</p></div>'
              f'<div class="tiles"><div class="tile"><b>{r["pasa_k"]:.0%}</b><span>pass^k ({len(r["variantes"])} variantes)</span></div>'
              f'<div class="tile"><b>{r["errores_caros"]}</b><span>errores caros</span></div>'
              f'<div class="tile"><b>{r["n"]}</b><span>casos</span></div></div>'
              f'<div class="grupo ico">{filas}</div>'
              f'<h2 class="sec">Sombra</h2><div class="tiles"><div class="tile"><b>{s["n"]}</b><span>borradores medidos</span></div>'
              f'<div class="tile"><b>{_pct(s.get("cobertura"))}</b><span>cobertura</span></div>'
              f'<div class="tile"><b>{_pct(s.get("habria_enviado_sin_editar"))}</b><span>se habría enviado tal cual</span></div>'
              f'<div class="tile"><b>{"sí" if s.get("concluye") else "no"}</b><span>concluye (n ≥ 30)</span></div></div>')
    return pagina(espacio, llave, "banco", "Taller", cuerpo)


def _pct(x) -> str:
    return "—" if x is None else f"{x:.0%}"


# --------------------------------------------------------------------------- #
#  El enlace del negocio: solo conectar WhatsApp (remoto)                      #
# --------------------------------------------------------------------------- #
def _espacio_negocio(cliente_id: str, t: str | None) -> Espacio:
    try:
        espacio = Espacio(cliente_id)
    except EspacioInvalido as error:
        raise HTTPException(404, "no existe") from error
    if not vinculacion_valida(cliente_id, t):
        raise HTTPException(401, "enlace inválido")
    return espacio


PASOS_NEGOCIO = ("Preparar", "Vincular", "Copiar")
_ETAPA = {"sin_lector": 0, "arrancando": 0, "error": 0, "esperando_qr": 1, "esperando_codigo": 1,
          "vinculado": 2, "conectado": 3}


def _vivo_negocio(clave: str, estado: dict) -> str:
    """Lo que cambia mientras el negocio tiene la página abierta. Sin conteos ni detalle técnico (test)."""
    if clave in ("numero_ajeno", "desconectado"):
        _, titulo, ayuda = ESTADOS[clave]
        return (f'<div class="bloque" style="text-align:center"><span class="estado bad">{esc(titulo)}</span>'
                f'<p class="lede" style="margin:10px 0 0">{esc(ayuda)} Escríbanos y le mandamos un código nuevo.</p></div>')
    etapa = _ETAPA.get(clave, 0)
    barras = "".join(f'<i class="{"ok" if i < etapa else ("ya" if i == etapa else "")}"></i>'
                     for i in range(len(PASOS_NEGOCIO)))
    nombres = "".join(f'<span class="{"on" if i == min(etapa, 2) else ""}">{p}</span>'
                      for i, p in enumerate(PASOS_NEGOCIO))
    progreso = f'<div class="pasos-bar" aria-hidden="true">{barras}</div><div class="pasos-nom">{nombres}</div>'
    if clave == "conectado" or clave == "vinculado":
        listo = clave == "conectado"
        return (progreso + '<div class="bloque" style="text-align:center">' + _listo_svg()
                + f'<h2 style="font-size:24px;letter-spacing:-.03em;margin:4px 0 6px">'
                f'{"Listo, ya quedó conectado" if listo else "Vinculado"}</h2>'
                '<p class="lede" style="margin:0">Sus conversaciones se están copiando. Deje el teléfono con internet '
                'unos minutos; puede cerrar esta página.</p></div>'
                '<div class="grupo ico">'
                + _fila("Lo que sigue", "Con lo que usted ya contesta en sus chats preparamos la propuesta de su "
                        "asistente. Usted la revisa y nada se enciende sin su aprobación.",
                        ico=f'<span class="icono">{icono("chispa")}</span>')
                + "</div>")
    if clave == "esperando_codigo" and estado.get("codigo"):
        titulo, centro = "Teclee este código", _codigo_html(estado["codigo"])
        ultimo = "Elija <b>Vincular con número de teléfono</b> y teclee el código de arriba."
    elif clave == "esperando_qr" and estado.get("qr"):
        titulo = "Escanee este código"
        centro = (f'<div class="qr">{_qr_svg(estado["qr"])}</div>'
                  '<p class="nota mismo-tel" style="text-align:center">¿Abrió este enlace en el mismo teléfono? '
                  'El QR se escanea desde otra pantalla: ábralo en una computadora o pídanos el código de 8 letras.</p>')
        ultimo = "Apunte la cámara al código de arriba."
    else:
        return (progreso + '<div class="bloque" style="text-align:center;padding:30px 18px">'
                '<span class="estado mid vivo">Preparando</span><p class="lede" style="margin:10px 0 0">En unos '
                'segundos aparece su código. Esta página se actualiza sola.</p></div>')
    pasos = "".join(_fila(f"<span style='font-weight:400'>{texto}</span>", ico=f'<span class="icono n">{i}</span>')
                    for i, texto in enumerate((
                        "Abra <b>WhatsApp Business</b> en el teléfono del negocio.",
                        "Vaya a <b>Dispositivos vinculados</b>: en iPhone, Configuración; en Android, el menú ⋮.",
                        "Toque <b>Vincular un dispositivo</b>. " + ultimo,
                        "Deje el teléfono con internet unos minutos mientras se copian sus conversaciones."), 1))
    return (progreso + f'<div class="bloque"><h2 style="font-size:22px;letter-spacing:-.025em;text-align:center">{titulo}'
            f"</h2>{centro}</div><h2 class=\"sec\">Cómo</h2><div class=\"grupo ico\">{pasos}</div>")


@router.get("/v/{cliente_id}", response_class=HTMLResponse)
def vincular_negocio(cliente_id: str, t: str | None = None) -> str:
    """Lo único que ve el negocio: su foto, su color, el código o el QR, y si ya quedó."""
    espacio = _espacio_negocio(cliente_id, t)
    estado = vinculado.leer_estado(espacio)
    clave = estado.get("estado", "sin_lector")
    alta = espacio.leer_json("alta.json", {}) or {}
    nombre = alta.get("nombre_comercial") or "Su negocio"
    foto = portada(espacio)
    if foto:
        fuente = f"/v/{quote(cliente_id)}/portada?t={quote(t or '')}&v={int(foto.stat().st_mtime)}"
        cabeza = f'<div class="portada" style="background-image:url(&quot;{esc(fuente)}&quot;)" role="img" aria-label="{esc(nombre)}">'
    else:
        cabeza = f'<div class="portada sin-foto"><div class="monograma" aria-hidden="true">{esc(nombre.strip()[:1].upper())}</div>'
    cabeza += f'<span class="seguro">{icono("candado")}Conexión privada</span></div>'
    garantias = "".join(_fila(t_, d, ico=f'<span class="icono">{icono(i)}</span>') for i, t_, d in (
        ("ojo", "Solo lee", "Lee sus conversaciones para aprender cómo atiende usted."),
        ("callado", "No envía nada", "Su WhatsApp sigue igual: no envía mensajes, no marca nada como leído y no "
         "aparece en línea."),
        ("apagar", "Usted lo desconecta", "Cuando quiera, desde Dispositivos vinculados en su teléfono."),
        ("visto", "Nada se enciende sin usted", "Antes de contestarle a un cliente, usted revisa y aprueba su asistente."),
    ))
    hoja = (f'<main class="hoja aparece"><p class="sobre">Su asistente de WhatsApp</p>'
            f'<h1 class="titulo-grande">{esc(nombre)}</h1>'
            '<p class="lede">Conecte su WhatsApp Business. Toma un par de minutos.</p>'
            f'<section data-vivo aria-live="polite">{_vivo_negocio(clave, estado)}</section>'
            f'<h2 class="sec">Su WhatsApp sigue igual</h2><div class="grupo ico">{garantias}</div>'
            '<p class="firma">Hecho por <b>DGED</b></p></main>')
    return _documento(espacio, f"Conectar WhatsApp · {nombre}", f'<div class="marco">{cabeza}{hoja}</div>',
                      refrescar=5, clase="negocio")


@router.get("/v/{cliente_id}/portada")
def portada_negocio(cliente_id: str, t: str | None = None):
    return _servir_portada(_espacio_negocio(cliente_id, t))
