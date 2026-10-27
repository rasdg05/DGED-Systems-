"""Las pantallas de la operación diaria, como las de Gestor Morelos: el semáforo de
pendientes, la cola de envío y el calendario de ocupación.

- `/espacios/<id>/pendientes`: el semáforo (`semaforo.py`), la más urgente primero.
- `/espacios/<id>/cola`: lo que espera su sí, lo que está en cola, lo que salió hoy
  y lo que no salió con su porqué (`enviador.py`).
- `/espacios/<id>/calendario`: conectar Google Calendar, Airbnb o Booking por su
  iCal y ver las noches libres, ocupadas y sin saber (`calendario.py`).

Con la llave del cliente, como Inicio y Chats. Los teléfonos van enmascarados y
las URLs de los calendarios nunca se enseñan.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from . import agente, calendario, canal, enviador, historial, semaforo
from .espacio import Espacio
from .paginas import HORA_MX, _cuando, _enmascarar, _espacio, _fila, esc, icono, pagina, url

router = APIRouter()

COLOR_TXT = {"rojo": "Urgente", "ambar": "Hoy", "verde": "Al día", "gris": "Sin pendiente"}
PLATAFORMAS = (("google", "Google Calendar"), ("airbnb", "Airbnb"), ("booking", "Booking.com"))


def _horas_txt(horas: float) -> str:
    if horas < 1:
        return f"{max(1, round(horas * 60))} min"
    if horas < 48:
        return f"{round(horas)} h"
    return f"{round(horas / 24)} días"


def punto(color: str) -> str:
    return f'<span class="sem sem-{color}" title="{esc(COLOR_TXT.get(color, color))}"></span>'


def fila_semaforo(espacio: Espacio, llave: str | None, f: semaforo.Fila) -> str:
    detalle = (f'<span class="linea" style="display:block">{esc(f.que_hacer)}</span>'
               f'<span class="linea cita" style="display:block">“{esc(f.dicho[:110])}”</span>' if f.dicho
               else f'<span class="linea" style="display:block">{esc(f.que_hacer)}</span>')
    return _fila(f"{esc(f.etiqueta)} · {esc(_enmascarar(f.hilo))}", detalle,
                 url(espacio, "conversaciones", llave, hilo=f.hilo), punto(f.color), esc(_horas_txt(f.horas)))


def semaforo_mosaico(espacio: Espacio, llave: str | None, res: dict) -> str:
    destino = esc(url(espacio, "pendientes", llave))
    return ('<div class="tiles sem-tiles">' + "".join(
        f'<a class="tile" href="{destino}#{c}">{punto(c)}<b>{res[c]}</b><span>{COLOR_TXT[c]}</span></a>'
        for c in semaforo.COLORES) + "</div>")


# --------------------------------------------------------------------------- #
#  Pendientes                                                                  #
# --------------------------------------------------------------------------- #
@router.get("/espacios/{cliente_id}/pendientes", response_class=HTMLResponse)
def pendientes(cliente_id: str, llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    filas = semaforo.leer(historial.hilos(espacio))
    res = semaforo.resumen(filas)
    partes = [f'<p class="lede">La más urgente primero, por cuánto lleva esperando. '
              f'{res["seguimiento"]} para dar seguimiento hoy.</p>', semaforo_mosaico(espacio, llave, res)]
    for color in semaforo.COLORES:
        del_color = [f for f in filas if f.color == color]
        if not del_color:
            continue
        muestra = del_color if color != "gris" else del_color[:30]
        partes.append(f'<h2 class="sec" id="{color}">{punto(color)} {COLOR_TXT[color]}<small>{len(del_color)}</small></h2>'
                      f'<div class="grupo chats">{"".join(fila_semaforo(espacio, llave, f) for f in muestra)}</div>')
    if not filas:
        partes.append('<div class="grupo vacio">Todavía no hay conversaciones. Conecte su WhatsApp en Negocio.</div>')
    return pagina(espacio, llave, "", "Pendientes", "".join(partes), refrescar=60,
                  atras=("Inicio", url(espacio, "", llave)))


# --------------------------------------------------------------------------- #
#  Cola de envío                                                               #
# --------------------------------------------------------------------------- #
def estado_canal(espacio: Espacio) -> tuple[str, str, str]:
    """(tono, título, explicación) de por dónde y qué sale hoy."""
    config = espacio.config()
    if config.get("encendido", "sombra") != "sin_cifra":
        return "mid", "Envío en pausa", "Prepara respuestas y cotizaciones; no se manda nada hasta encender el envío."
    if not canal.configurado(espacio):
        return "bad", "Sin WhatsApp conectado", "El envío está encendido pero el WhatsApp del negocio no está conectado."
    ritmo = enviador.Ritmo.de(espacio)
    return "ok", "Enviando", (f"Uno cada {ritmo.pausa_min} segundos, de {ritmo.hora_desde}:00 a {ritmo.hora_hasta}:59, "
                              f"hasta {ritmo.tope_dia} al día. Antes de mandar se revisa todo otra vez.")


_MOTIVOS = (("sombra", "Envío en pausa"), ("sin conector", "WhatsApp sin conectar"),
            ("se movió", "El cliente escribió después: no se mandó"), ("apartadas", "Esas fechas ya se apartaron"),
            ("sin aprobación", "Falta su sí"), ("ya recibió una ronda", "Ya recibió un mensaje en las últimas 24 h"),
            ("falló", "WhatsApp no lo aceptó"), ("la contesta la persona", "Lo contesta usted"),
            ("otro cliente", "No es de este negocio"), ("no existe", "Ya no existe"))


def motivo_amable(motivo: str) -> str:
    """El porqué de un envío que no salió, en palabras del negocio (lo técnico vive en el registro)."""
    m = (motivo or "").lower()
    return next((txt for clave, txt in _MOTIVOS if clave in m), "No salió")


@router.get("/espacios/{cliente_id}/cola", response_class=HTMLResponse)
def cola(cliente_id: str, llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    alta = espacio.leer_json("alta.json", {}) or {}
    salidas = {s.id: s for s in agente.salidas(espacio)}
    por_aprobar = [s for s in salidas.values() if s.requiere_aprobacion and not s.aprobada_por]
    en_cola = [salidas[i] for i in enviador.pendientes(espacio) if i in salidas]
    hoy = datetime.now(HORA_MX).date()
    registros = [e for e in espacio.leer_lineas(enviador.ENVIADOS)
                 if e.get("cuando") and datetime.fromisoformat(e["cuando"]).astimezone(HORA_MX).date() == hoy]
    salieron = [e for e in registros if e.get("enviado")]
    no_salieron = [e for e in registros if not e.get("enviado")]
    tono, titulo, texto = estado_canal(espacio)

    def renglon(s, boton: bool = False) -> str:
        extra = (f'<button class="btn" style="min-height:38px;font-size:15px;margin-top:8px" '
                 f'onclick="aprobarSalida(this,{esc(json.dumps(s.id))})">Aprobar</button>' if boton else "")
        return _fila(esc(_enmascarar(s.hilo)), f'<span class="linea" style="display:block">{esc((s.texto or "")[:160])}</span>',
                     url(espacio, "conversaciones", llave, hilo=s.hilo), extra=extra,
                     der=esc(_cuando(int(datetime.fromisoformat(s.creada).timestamp()))))

    def registro(e: dict) -> str:
        motivo = esc(motivo_amable(e.get("motivo", ""))) if not e.get("enviado") else "Enviado"
        return _fila(esc(_enmascarar(e.get("hilo", ""))), motivo,
                     url(espacio, "conversaciones", llave, hilo=e["hilo"]) if e.get("hilo") else None,
                     der=esc(datetime.fromisoformat(e["cuando"]).astimezone(HORA_MX).strftime("%H:%M")))

    partes = [f'<div class="bloque"><span class="estado {tono}">{esc(titulo)}</span>'
              f'<p class="lede" style="margin:8px 0 0">{esc(texto)}</p></div>',
              f'<div class="tiles"><div class="tile"><b>{len(por_aprobar)}</b><span>esperan su sí</span></div>'
              f'<div class="tile"><b>{len(en_cola)}</b><span>en cola</span></div>'
              f'<div class="tile"><b>{len(salieron)}</b><span>enviados hoy</span></div>'
              f'<div class="tile"><b>{len(no_salieron)}</b><span>no salieron hoy</span></div></div>']
    if por_aprobar:
        partes.append('<h2 class="sec">Esperan su sí</h2><div class="grupo chats">'
                      + "".join(renglon(s, boton=True) for s in por_aprobar[:50]) + "</div>")
    if en_cola:
        partes.append('<h2 class="sec">En cola</h2><div class="grupo chats">'
                      + "".join(renglon(s) for s in en_cola[:50]) + "</div>")
    if salieron or no_salieron:
        partes.append('<h2 class="sec">Hoy</h2><div class="grupo chats">'
                      + "".join(registro(e) for e in reversed((salieron + no_salieron)[-50:])) + "</div>")
    if not (por_aprobar or en_cola or registros):
        partes.append('<div class="grupo vacio">Nada en la cola. Lo que apruebe aparece aquí y sale al paso de una persona.</div>')
    partes.append("<script>async function aprobarSalida(b,id){b.disabled=true;"
                  f"const r=await fetch({json.dumps(url(espacio, 'salidas/', llave))}.replace('salidas/?','salidas/'+id+'/aprobar?'),"
                  "{method:'POST',headers:{'Content-Type':'application/json'},"
                  f"body:JSON.stringify({{aprobador:{json.dumps(alta.get('aprobador', ''))}}})}});"
                  "const d=await r.json().catch(()=>({}));b.textContent=r.ok?(d.encolada?'En cola ✓':d.enviada?'Enviada ✓':"
                  "'Aprobada ✓'):(d.detail||'No se pudo');if(!r.ok)b.disabled=false}</script>")
    return pagina(espacio, llave, "", "Cola de envío", "".join(partes), refrescar=30,
                  atras=("Inicio", url(espacio, "", llave)))


# --------------------------------------------------------------------------- #
#  Calendario                                                                  #
# --------------------------------------------------------------------------- #
def _propiedades(espacio: Espacio) -> list[str]:
    """Las casas con el id que usa el cotizador (las de la lista de precios aprobada);
    sin lista, las del alta. Así el calendario y la cotización hablan de lo mismo."""
    from . import perfil

    activo = perfil.activo(espacio) or {}
    ids = sorted({r["propiedad"] for r in activo.get("reglas", []) or []
                  if r.get("propiedad") and r["propiedad"] != "ambas"})
    if not ids:
        for nombre in (espacio.leer_json("alta.json", {}) or {}).get("propiedades", []) or []:
            pid = "".join(c if c.isalnum() else "-" for c in str(nombre).strip().lower()).strip("-")[:20]
            if len(pid) >= 2 and pid not in ids:
                ids.append(pid)
    for f in calendario.fuentes(espacio):
        if f["propiedad"] not in ids:
            ids.append(f["propiedad"])
    return ids


@router.get("/espacios/{cliente_id}/calendario", response_class=HTMLResponse)
def calendario_pagina(cliente_id: str, llave: str | None = None) -> str:
    espacio = _espacio(cliente_id, llave)
    oc = calendario.Ocupacion.de(espacio)
    hoy = datetime.now(calendario.ZONA).date()
    partes = []
    if not oc.configurada:
        partes.append('<div class="bloque"><span class="estado mid">Sin calendario</span>'
                      '<p class="lede" style="margin:8px 0 0">Conéctelo para que su asistente no ofrezca fechas que ya '
                      'están apartadas. Mientras tanto, nada con fechas sale en las rondas.</p></div>')
    else:
        filas = []
        for prop, fuentes_ in sorted(oc.por_propiedad.items()):
            for f in fuentes_:
                plataforma = f["fuente"].split("-", 1)[1] if "-" in f["fuente"] else f["fuente"]
                tono = "ok" if f["vigente"] else "bad"
                filas.append(_fila(f"{esc(prop.capitalize())} · {esc(dict(PLATAFORMAS).get(plataforma, plataforma))}",
                                   f'<span class="estado {tono}">{"Al día" if f["vigente"] else esc(f["por_que"])}</span>',
                                   ico=f'<span class="icono c {"c-verde" if f["vigente"] else "c-gris"}">{icono("visto")}</span>'))
        partes.append('<h2 class="sec">Conectados</h2><div class="grupo ico">' + "".join(filas) + "</div>")
        noches = oc.noches(hoy, 42)
        clase = {calendario.LIBRE: "d-libre", calendario.OCUPADA: "d-ocupada", calendario.NO_SE_SABE: "d-nose"}
        for prop, dias in noches.items():
            celdas = "".join(
                f'<i class="{clase[d["estado"]]}" title="{esc(d["noche"])}: {esc(d["estado"].replace("_", " "))}">'
                f'{int(d["noche"][-2:])}</i>' for d in dias)
            partes.append(f'<h2 class="sec">{esc(prop.capitalize())}<small>próximas 6 semanas</small></h2>'
                          f'<div class="bloque"><div class="dias">{celdas}</div></div>')
        partes.append('<p class="lede"><span class="leyenda d-libre"></span> libre · '
                      '<span class="leyenda d-ocupada"></span> ocupada · <span class="leyenda d-nose"></span> sin saber</p>')
    opciones_prop = "".join(f'<option value="{esc(p)}">{esc(p.capitalize())}</option>' for p in _propiedades(espacio))
    opciones_plat = "".join(f'<option value="{v}">{t}</option>' for v, t in PLATAFORMAS)
    partes.append(
        '<h2 class="sec">Conectar un calendario</h2><div class="bloque"><form id="fcal" onsubmit="return conectar(event)">'
        + (f'<label>Casa<select name="propiedad">{opciones_prop}</select></label>' if opciones_prop else
           '<label>Casa<input name="propiedad" placeholder="finca" autocapitalize="off" autocorrect="off" required></label>')
        + f'<label>Dónde lo lleva<select name="plataforma">{opciones_plat}</select></label>'
        '<label>Enlace del calendario (iCal)<input name="url" type="url" inputmode="url" autocomplete="off" '
        'autocapitalize="off" autocorrect="off" placeholder="https://calendar.google.com/calendar/ical/…/basic.ics" required></label>'
        '<button class="btn ancho" type="submit">Conectar</button><p class="lede" id="rcal" style="margin:10px 0 0"></p>'
        '</form></div>'
        '<div class="bloque"><b>Dónde está el enlace</b><p class="lede" style="margin:6px 0 0">'
        '<b>Google Calendar</b> (en computadora): Configuración → el calendario de la casa → '
        '<i>Dirección secreta en formato iCal</i>.<br><b>Airbnb</b>: Anuncio → Disponibilidad → Conectar calendarios → '
        '<i>Exportar calendario</i>.<br><b>Booking.com</b>: Extranet → Tarifas y disponibilidad → Sincronizar calendarios → '
        '<i>Exportar</i>.<br>El enlace se guarda solo en su espacio y no se vuelve a mostrar.</p></div>'
        "<script>async function conectar(ev){ev.preventDefault();const f=new FormData(ev.target),o=document.getElementById('rcal');"
        "o.textContent='Conectando…';"
        f"const r=await fetch({json.dumps(url(espacio, 'calendario/fuentes', llave))},{{method:'POST',"
        "headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(f))});"
        "const d=await r.json().catch(()=>({}));if(!r.ok){o.textContent=d.detail||'No se pudo';return false}"
        "const mal=(d.estado||[]).filter(e=>!e.ok);o.textContent=mal.length?('Se guardó, pero no respondió: '+mal[0].error):"
        "'Conectado ✓';if(!mal.length)setTimeout(()=>location.reload(),900);return false}</script>")
    return pagina(espacio, llave, "negocio", "Calendario", "".join(partes),
                  atras=("Negocio", url(espacio, "negocio", llave)))


def resumen_inicio(espacio: Espacio) -> dict:
    """Lo que Inicio enseña de la operación, sin pintar nada."""
    filas = semaforo.leer(historial.hilos(espacio))
    return {"filas": filas, "resumen": semaforo.resumen(filas), "en_cola": len(enviador.pendientes(espacio)),
            "calendario": calendario.Ocupacion.de(espacio).configurada,
            "enviados_hoy": sum(1 for e in espacio.leer_lineas(enviador.ENVIADOS) if e.get("enviado") and e.get("cuando")
                                and datetime.fromisoformat(e["cuando"]).astimezone(HORA_MX).date()
                                == datetime.now(timezone.utc).astimezone(HORA_MX).date())}
