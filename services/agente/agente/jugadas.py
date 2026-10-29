"""Las jugadas del giro: qué HIZO un mensaje del negocio, en una palabra.

La vara compara jugadas, no textos (Gestor, `app/services/replay.py`): el
parecido de texto castiga decir lo mismo con otras palabras y premia copiar la
plantilla. Con jugadas, *"Que fecha ?"* y *"¿Para cuándo sería?"* son lo mismo
(`pide:fechas`), y *"35,000 el fin de semana"* es una `cifra` aunque nadie la
haya escrito igual.

Las jugadas de una renta de finca y quinta (`docs/18`, corregidas con los
mensajes de Finca Emiliano del 2026-07-29 al 2026-10-27):

· `cifra` — dio un monto (*"30,000 el fin de semana"*, *"5500 la noche"*);
· `disponibilidad` — sí o no hay fecha (*"Ya tenemos ocupado esa fecha"*);
· `anticipo` — cómo apartar, depósito, comprobante, INE;
· `pide:fechas` · `pide:personas` · `pide:evento` · `pide:propiedad` — pide el
  dato que falta para cotizar; `pide:otra` pregunta otra cosa;
· `espera` — gana tiempo (*"déjeme checar"*, *"le hago una cotización"*);
· `visita` — ofrece o agenda visita o videollamada;
· `info:capacidad` · `info:ubicacion` · `info:incluye` — contesta qué hay, dónde
  está y qué incluye (alberca, mascotas, alimentos, reglas);
· `fotos` — mandó imágenes o documentos sin decir nada con contenido (las
  tarifas de la finca viven en imágenes: el texto no las ve);
· `confirma` — *"Así es"*, *"Sí claro"* a lo que el cliente preguntó (no es un
  acuse: confirma un hecho que solo el negocio sabe; Gestor v8);
· `saludo` · `acuse` — saluda o acusa sin contenido;
· `medio` — un audio o sticker solo: no se mide;
· `otra` — lo que todavía no tiene nombre. Meta: < 10% en desarrollo.

Del lado del agente, además: `persona` (lo pasa a una persona), `silencio`
(calla), `ia` (iría al modelo: la vara no llama a ninguna IA) y `soy_asistente`.

**Lo automático no es una persona.** Una plantilla (≥ `USOS_DE_PLANTILLA` usos y
≥ `PALABRAS_DE_PLANTILLA` palabras) que sale a ≤ `SEGUNDOS_AUTOMATICA` del
cliente la mandó el contestador. La misma frase minutos después es una
respuesta rápida que eligió una persona: eso sí es una jugada. Medido en Finca
Emiliano: de 1,102 envíos de plantilla, 880 salen en ≤ 15 s y la cola se
aplana pasando los 20 s; *"Ok"* (26 usos) y *"Si"* (21) los teclea una persona.

No llama a ningún modelo ni escribe nada: es una cuenta sobre el historial.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .conversacion import es_acuse, normalizar
from .guardia import DINERO
from .historial import Mensaje

#: Cambia cuando cambia lo que una jugada significa: intentos con otro
#: clasificador no se comparan (ni DSR ni PBO).
#: finca-2 (2026-10-29, corrida GM): `es_acuse` lee "entiendo", "le agradezco mucho", "qué
#: lástima" y los aplazamientos nuevos, así que esas frases del negocio pasan de `otra` a
#: `acuse`. Los intentos c1-* del universo 8c8c8b3f se midieron ya con estas lecturas
#: (las de B3) bajo el nombre finca-1: no se comparan con los de finca-2.
CLASIFICADOR_VERSION = "finca-2"

USOS_DE_PLANTILLA = 20
PALABRAS_DE_PLANTILLA = 4
SEGUNDOS_AUTOMATICA = 20
DIAS_BIENVENIDA = 14

#: Lo que el agente hace sin hablar como el negocio.
NO_ACTUA = frozenset({"persona", "silencio", "espera", ""})
JUGADAS = ("cifra", "disponibilidad", "anticipo", "pide:fechas", "pide:personas", "pide:evento",
           "pide:propiedad", "pide:otra", "espera", "visita", "info:capacidad", "info:ubicacion",
           "info:incluye", "fotos", "confirma", "saludo", "acuse", "medio", "otra")
MEDIOS_QUE_ENSENAN = frozenset({"imagen", "image", "video", "documento", "document"})


# --------------------------------------------------------------------------- #
#  Lo automático                                                               #
# --------------------------------------------------------------------------- #
def plantillas(hilos: dict[str, list[Mensaje]]) -> set[str]:
    """Los textos del negocio que se repiten como plantilla. Un *"Ok"* repetido
    no es plantilla: lo teclea una persona."""
    usos = Counter(m.texto.strip() for ms in hilos.values() for m in ms if m.del_negocio and m.texto)
    return {t for t, n in usos.items() if n >= USOS_DE_PLANTILLA and len(t.split()) >= PALABRAS_DE_PLANTILLA}


def automaticas(mensajes: list[Mensaje], fijas: set[str]) -> set[str]:
    """Los ids de los mensajes del negocio que mandó el contestador en este hilo.

    Una plantilla es automática si sale a ≤ `SEGUNDOS_AUTOMATICA` del último
    mensaje del cliente, **o si abre el intercambio** (ningún mensaje del negocio
    en `DIAS_BIENVENIDA` días): es la bienvenida de WhatsApp Business, que la
    manda el teléfono y llega tarde si estaba apagado (628 de 628 en Finca
    Emiliano abren el intercambio; 36 llegaron después de los 20 s)."""
    salida: set[str] = set()
    ultimo_cliente = ultimo_negocio = None
    for m in mensajes:
        if not m.del_negocio:
            ultimo_cliente = m.ts
            continue
        if m.texto and m.texto.strip() in fijas and ultimo_cliente is not None:
            pronto = 0 <= m.ts - ultimo_cliente <= SEGUNDOS_AUTOMATICA
            abre = ultimo_negocio is None or m.ts - ultimo_negocio > DIAS_BIENVENIDA * 86400
            if pronto or abre:
                salida.add(m.id)
        ultimo_negocio = m.ts
    return salida


# --------------------------------------------------------------------------- #
#  Un mensaje                                                                  #
# --------------------------------------------------------------------------- #
#: Un monto pelón: *"5500 la noche"*, *"35,000"*. Un año (1950–2039) o una hora no.
_MONTO = re.compile(r"(?<![\d:/.])(\d{1,3}(?:,\d{3})+|\d{4,6})(?![\d:/])")
_ANO = re.compile(r"19[5-9]\d|20[0-3]\d")
#: Un monto de tres cifras con su unidad: *"900 el día"*, *"Son 900"*, *"100 pesos por persona"*.
_MONTO_CORTO = re.compile(r"\b\d{3}\s*(?:el|la|por|x|al)\s*(?:dia|noche|persona|fin|evento|hora|mes)\b"
                          r"|^(?:son|seria|serian|queda en|sale en|le sale en)\s+\d{3}\b")
#: La capacidad dicha como cifra de personas: *"37 personas"*.
_CAPACIDAD_PELONA = re.compile(r"^(?:para |hasta |maximo |son )?\d{1,3} personas[.!\s]*$")
#: Un horario: *"Entrada 10:00 am y salida 1:00 pm"*.
_HORARIO = re.compile(r"\b(?:llegar|llegada|entrada|salida)\b.{0,20}\b(?:a las \d{1,2}|por la manana|por la tarde)\b"
                      r"|\bpor la manana de preferencia\b|\b(?:entrada|salida|llegar|llegada|check)\b.{0,25}\b\d{1,2}(?::\d\d)?\s*(?:am|pm|hrs?)\b")

_DISPONIBILIDAD = re.compile(
    r"\bdisponib\w*|\bocupad[oa]s?\b|\b(?:ya )?(?:tenemos|esta|estan|esa fecha esta|ese fin (?:lo )?tenemos)"
    r" (?:ya )?(?:reservad[oa]|ocupad[oa]|apartad[oa]|rentad[oa])"
    r"|\bya (?:esta|se) (?:reservad|rentad|apartad|ocupad)\w*|\bno (?:tenemos|hay|tengo) (?:fecha|lugar|cupo|espacio)"
    r"|\b(?:fecha|fechas|fin|dia|dias) (?:ya )?(?:esta |estan )?(?:reservad|ocupad|rentad|apartad)\w*"
    r"|\bva(?: a)? estar (?:rentad|ocupad|reservad)\w*|\bsolo tengo (?:la|el) (?:quinta|finca)\b|\btengo (?:libre|la quinta libre|la finca libre)\b"
    r"|\b(?:si|no) (?:hay|tenemos|tengo) (?:esa fecha|para esa fecha|para esas fechas)\b")
_ANTICIPO = re.compile(
    r"\banticipo\b|\bapart(?:ar|arlo|arla|ado|amos)\b|\bdeposit\w*|\btransferencia|\bclabe\b"
    r"|\bnumero de cuenta\b|\bcuenta bancaria\b|\bcomprobante\b|\b(?:su|tu|la) ine\b|\bidentificacion\b"
    r"|\bliquid(?:ar|a|an|ación|acion)\b|\brestar(?:ian|ia)\b|\bel resto\b|\bpago\b.{0,20}\b(?:efectivo|tarjeta)\b"
    r"|\bcontrato\b")
_FECHAS = re.compile(
    r"\bque (?:fecha|fechas|dia|dias|mes)\b|\bpara (?:que|cuando) (?:fecha|dia|seria)\b|\bde que mes\b"
    r"|\bfecha\s*\?|\bcuando (?:seria|serian|les gustaria|quieren|vienen|llegarian|es el evento)\b"
    r"|\bcuantas noches\b|\b(?:solo|nada mas) (?:1|una) noche\b|\b(?:el )?fin de semana o\b"
    r"|\b(?:tus|sus) fechas\b|\bdel \d{1,2} al \d{1,2}\s*\?|\bque dia (?:les|le|te) gustaria\b|\bpara cuando\b")
_PERSONAS = re.compile(
    r"\bse van a quedar\b|\bse quedan\b|\bsolo son visitas\b|\bcuantos se quedan\b|\bcuant[oa]s (?:personas|invitados|adultos|ninos|huespedes|son|serian|vienen|van|serán)\b"
    r"|\bpara cuant[oa]s\b|\bcuantos serian\b|\bpara \d+ (?:personas|invitados)\s*\?|^cuant[oa]s\s*\?")
_EVENTO = re.compile(
    r"\bes (?:boda|cumple\w*|xv|evento|fiesta|bautizo|comunion|reunion)\b|\bque (?:les gustaria|tipo de evento)\b"
    r"|\b(?:evento|fiesta) o (?:solo )?hospedaje\b|\bsolo hospedaje\b|\bquieres banquete\b|\bque evento\b"
    r"|\bboda\s*,|\bcumpleanos\s*\?")
_PROPIEDAD = re.compile(
    r"\b(?:finca|casa grande) o (?:la )?quinta\b|\bquinta o (?:la )?finca\b|\bcual (?:casa|opcion|propiedad)\b"
    r"|\bcuantas habitaciones\b|\blas (?:9|nueve|6|seis|5|cinco) habitaciones\s*\?")
_ESPERA = re.compile(
    r"\b(?:dejame|dejeme|deja|permitame|permiteme|deme|dame) (?:un momento|checar|checo|ver|revisar|confirmar|"
    r"preguntar|consultar|reviso|veo)\b|\b(?:le|te) (?:hago|mando|paso|envio) (?:una |la |su )?cotizacion\b"
    r"|\b(?:le|te) confirmo\b|\bahorita (?:le|te) (?:digo|confirmo|mando|paso|cotizo)\b|\ben un momento\b"
    r"|\blo checo\b|\bvoy a checar\b|\b(?:le|te) (?:aviso|digo) (?:en un rato|mas tarde|al rato)\b")
_VISITA = re.compile(
    r"\bvideo ?llamada\b|\b(?:una|la|de|hacer|agendar|si quiere|si gusta) visita\b|\bvisitar(?:nos|la|lo)?\b"
    r"|\b(?:te|les|le|los) (?:ensene|ensenen|muestre|muestren)\b|\ba que hora (?:los|las|lo|la) esperamos\b|\bconocer (?:la|el|las) (?:lugar|finca|quinta|instalaciones)\b"
    r"|\brecorrido\b|\bvengan? a (?:conocer|ver)\b|\bpasar a (?:ver|conocer)\b|\ba que hora (?:le|les|te) (?:digo|espero)\b")
_UBICACION = re.compile(
    r"\bubicad\w*|\bchiconcuac\b|\bxochitepec\b|\bmaps\.|google\.com/maps|\bminutos de cuernavaca\b"
    r"|^(?:en |estamos en )?morelos\b|\bestamos en morelos\b|\bubicacion\b|\bcomo llegar\b")
_CAPACIDAD = re.compile(
    r"\bcapacidad\b|\bhabitaciones\b|\bcaben\b|\bcupo\b|\bhospedar\b|\b(?:2|dos) (?:casas|opciones)\b"
    r"|\bsomos finca emiliano\b|\bquinta emiliano es nuestra opcion\b|\botra quinta\b|\bpersonas mas\b")
_INCLUYE = re.compile(
    r"\bincluy\w*|\balberca\b|\bclimatiz\w*|\bcalefaccion\b|\bmascota\w*|\bpet ?friendly\b|\bmobiliario\b"
    r"|\balimentos\b|\bbanquete\b|\bmenu\b|\bmeser\w*|\blimpieza\b|\breglas?\b|\bmusica\b|\bruido\b"
    r"|\bcheck ?(?:in|out)\b|\bhora de (?:entrada|salida)\b|\btoallas\b|\basador\b|\bcocina\b"
    r"|\bestacionamiento\b|\bno se los voy a contar\b|\bminimo (?:de )?(?:\d+|dos|tres|cuatro) noches\b"
    r"|\btodo incluido\b|\btenemos todo\b|\baparte\b|\bwifi\b|\baire acondicionado\b|\bbrincolin\b"
    r"|\bpaquetes?\b|\bcomida\b|\bmesas?\b|\bsillas\b|\bdecoracion\b|\bpueden llegar\b|\bpueden entrar\b|\bvisitas?\b.{0,20}\bpor persona\b")
_CONFIRMA = re.compile(
    r"^(?:si+|asi es|claro(?: que si)?|correcto|exacto|efectivamente|si claro|claro si|si se puede"
    r"|si no hay (?:ningun )?problema|si no (?:te|se) preocupe?s?|por supuesto)\b")
_SALUDO = re.compile(r"^(?:hola|buen(?:os|as)? (?:dia|dias|tardes|noches)|buen dia|que tal)\b")
_CORTESIA = re.compile(
    r"\b(?:con gusto|de nada|a (?:usted|ustedes|ti)|quedo (?:al )?pendiente|seguimos en contacto|"
    r"estamos en contacto|los esperamos|sin problema|para servir\w*|mucho gusto|cualquier duda|"
    r"gracias|que (?:tenga|tengan|este) (?:un )?(?:buen|excelente|bonito|lindo)|bendiciones|saludos|"
    r"aqui estamos|un placer|una disculpa|disculpe?|confirmado|cuando gusten)\b"
    r"|^(?:ok|okey|oki|claro|va|sale|perfecto|excelente|listo|si)\b(?=.{0,30}$)")
LARGO_CORTO = 60


def es_monto(texto: str) -> bool:
    """¿Trae un monto? `guardia.DINERO` o un número pelón de 4 a 6 cifras que no es año."""
    if DINERO.search(texto or ""):
        return True
    return any(not _ANO.fullmatch(n) for n in _MONTO.findall(texto or ""))


def _pregunta(texto: str, t: str) -> bool:
    return "?" in texto or "¿" in texto or len(t) <= LARGO_CORTO


def jugada(texto: str | None, tipo: str = "text") -> str:
    """La jugada de UN mensaje del negocio (o de un texto del agente)."""
    if not (texto or "").strip():
        return "fotos" if tipo in MEDIOS_QUE_ENSENAN else "medio"
    crudo = texto.strip()
    t = normalizar(crudo)
    if es_monto(crudo) or _MONTO_CORTO.search(t):
        return "cifra"
    if _CAPACIDAD_PELONA.match(t):
        return "info:capacidad"
    if _DISPONIBILIDAD.search(t):
        return "disponibilidad"
    if _ANTICIPO.search(t):
        return "anticipo"
    if _pregunta(crudo, t):
        for nombre, patron in (("pide:fechas", _FECHAS), ("pide:personas", _PERSONAS),
                               ("pide:evento", _EVENTO), ("pide:propiedad", _PROPIEDAD)):
            if patron.search(t):
                return nombre
    if _ESPERA.search(t):
        return "espera"
    if _VISITA.search(t):
        return "visita"
    if _CAPACIDAD.search(t):
        return "info:capacidad"
    if _UBICACION.search(t):
        return "info:ubicacion"
    if _INCLUYE.search(t) or _HORARIO.search(t):
        return "info:incluye"
    if "?" in crudo or "¿" in crudo:
        return "pide:otra"
    if len(t) <= LARGO_CORTO:
        if _CONFIRMA.match(t):
            return "confirma"
        if _SALUDO.match(t):
            return "saludo"
        if es_acuse(crudo) or _CORTESIA.search(t):
            return "acuse"
    elif _CORTESIA.search(t) and not re.search(r"\b(?:porque|pero|si quiere|tenemos|hay)\b", t):
        return "acuse"
    return "otra"


#: El orden en que una jugada de la tanda gana a las demás: lo que trae
#: contenido gana a la cortesía que lo acompaña (*"Buen día"* + *"Para qué fecha?"*).
_PRIORIDAD = ("cifra", "disponibilidad", "anticipo", "pide:fechas", "pide:personas", "pide:evento",
              "pide:propiedad", "espera", "visita", "info:capacidad", "info:incluye", "info:ubicacion",
              "fotos", "pide:otra", "confirma", "saludo", "acuse", "otra", "medio")


def jugada_de_tanda(mensajes: list[Mensaje], cliente: str = "") -> str:
    """La jugada de varios mensajes seguidos del negocio. Con `cliente` (lo último
    que el cliente dijo), un *"Sí"* a una pregunta es `confirma`; si el cliente
    no preguntó nada, es `acuse`."""
    jugadas = [jugada(m.texto, m.tipo) for m in mensajes]
    if not jugadas:
        return ""
    gana = min(jugadas, key=_PRIORIDAD.index)
    if gana == "confirma" and not pregunta_el_cliente(cliente):
        return "acuse"
    return gana


def pregunta_el_cliente(cliente: str) -> bool:
    """¿El cliente preguntó o pidió algo (con o sin signo)?"""
    t = normalizar(cliente)
    return ("?" in (cliente or "") or "¿" in (cliente or "")
            or es_monto(cliente or "")
            or bool(re.search(r"\b(?:verdad|cierto|se puede|puedo|podemos|hay|tienen|tiene|incluye|aceptan|"
                              r"seria|serian|entonces)\b", t)))


# --------------------------------------------------------------------------- #
#  Los momentos: cada vez que una persona del negocio contestó a un cliente   #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Momento:
    id: str                 # el id del primer mensaje de la tanda (wamid): no lleva teléfono
    hilo: str               # la "persona" de la purga; no sale del espacio
    ts: int                 # cuándo contestó la persona
    entrante: Mensaje       # el último mensaje del cliente antes de la respuesta
    prefijo: tuple          # todo lo anterior a la respuesta (lo que el agente habría visto)
    tanda: tuple            # lo que la persona mandó hasta que el cliente volvió a escribir
    casa: str               # la jugada de la persona
    cliente: str            # lo que dijo el cliente (su ráfaga), para auditar


#: El botón del anuncio: el cliente llegó por una campaña.
_CTA = re.compile(r"quiero mas informacion|me gustaria (?:conseguir|obtener|recibir) mas informacion")


def es_platica_de_venta(mensajes: list[Mensaje], fijas: set[str]) -> bool:
    """¿Es una plática con un cliente del negocio? El teléfono vinculado es también
    el de la dueña como clienta de otros (proveedores, viajes): ahí ella escribe
    *"¡Hola! Quiero más información"* y la vara no tiene nada que medir. Es de
    venta si el negocio mandó una de sus plantillas o el cliente llegó por el
    anuncio. Medido en Finca Emiliano: 675 de 701 hilos."""
    return (any(m.del_negocio and m.texto and m.texto.strip() in fijas for m in mensajes)
            or any(not m.del_negocio and m.texto and _CTA.search(normalizar(m.texto)) for m in mensajes))


def momentos(hilos: dict[str, list[Mensaje]], solo_venta: bool = True) -> list[Momento]:
    """Cada respuesta de una PERSONA del negocio a un mensaje del cliente final.

    Lo automático se salta (no es una persona). La jugada `medio` no se mide.
    Solo la primera tanda tras el cliente: lo que se mide es qué se contestó."""
    from .conversacion import rafaga

    fijas = plantillas(hilos)
    salida: list[Momento] = []
    for hilo, mensajes in hilos.items():
        if solo_venta and not es_platica_de_venta(mensajes, fijas):
            continue
        auto = automaticas(mensajes, fijas)
        humanos = [m for m in mensajes if not (m.del_negocio and m.id in auto)]
        for i, m in enumerate(humanos):
            if not m.del_negocio or i == 0 or humanos[i - 1].del_negocio:
                continue
            tanda = []
            for x in humanos[i:]:
                if not x.del_negocio:
                    break
                tanda.append(x)
            prefijo = tuple(mensajes[:mensajes.index(m)])
            dicho = rafaga(list(humanos[:i])) or "\n".join(x.texto or "" for x in humanos[:i][-3:] if not x.del_negocio)
            casa = jugada_de_tanda(tanda, dicho)
            if casa == "medio":
                continue
            salida.append(Momento(id=m.id, hilo=hilo, ts=m.ts, entrante=humanos[i - 1], prefijo=prefijo,
                                  tanda=tuple(tanda), casa=casa, cliente=dicho))
    return sorted(salida, key=lambda x: (x.ts, x.id))
