"""Cómo habla la gente por WhatsApp: lo que Gestor Morelos aprendió con clientes reales.

Exportado de `rasdg05/Gestor-Morelos` (main del 2026-10-27, corridas 5 a 9):
`services/turno.py` (la ráfaga y lo que nadie oyó), `expediente_cotizacion.py`
(acuse, cierre, la pelota es suya, promesa, nada que contestar),
`bot.py` (reclamo, insulto, pedir una persona, "¿eres un bot?") y
`libro_cotizaciones.py` (el "ok" que aplaza no es un sí). Cada regla viene de
una conversación que salió mal allá; aquí se quitó lo que era de placas y
quedó lo que es de cualquier negocio que atiende por WhatsApp.

Nada de esto llama a un modelo. Son detectores baratos que deciden, ANTES de
gastar, si hay algo que contestar y quién lo contesta.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

RAFAGA_SEGUNDOS = 180


@lru_cache(maxsize=4096)
def normalizar(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")
    return " ".join(sin.lower().split())


def _solo_letras(texto: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", normalizar(texto)).split())


# --------------------------------------------------------------------------- #
#  Lo que nadie oyó no tiene turno (turno.es_solo_marca)                       #
# --------------------------------------------------------------------------- #
_SOLO_MARCA = re.compile(r"^\[(?:sticker|reacci[oó]n[^\]]*|[a-z]+ sin (?:descargar|leer))\]$")


def tiene_turno(texto: str | None) -> bool:
    crudo = (texto or "").strip()
    renglones = [r.strip() for r in crudo.splitlines() if r.strip()]
    return bool(renglones) and not all(_SOLO_MARCA.match(r) for r in renglones)


def rafaga(mensajes: list, segundos: int = RAFAGA_SEGUNDOS) -> str:
    """Lo que el cliente dijo desde la última respuesta del negocio, en un texto.

    `mensajes`: objetos con `del_negocio`, `ts` y `texto`, en orden, terminando
    en el que se contesta. Junta los del cliente pegados (≤ `segundos` uno del
    otro) y quita los repetidos seguidos. Con uno solo devuelve ese."""
    partes: list[str] = []
    siguiente = None
    for m in reversed(mensajes):
        if m.del_negocio:
            break
        if not tiene_turno(m.texto):
            continue
        if siguiente is not None and siguiente - m.ts > segundos:
            break
        siguiente = m.ts
        texto = m.texto.strip()
        if not partes or partes[0] != texto:
            partes.insert(0, texto)
    return "\n".join(partes)


# --------------------------------------------------------------------------- #
#  Escalar: reclamo, insulto, pedir una persona, "¿eres un bot?" (bot.py)      #
# --------------------------------------------------------------------------- #
# Un falso positivo aquí cuesta pasarle a una persona de más; un falso negativo
# deja a alguien molesto hablando con una máquina. La dirección segura es cachar.
RECLAMO = re.compile(
    r"(reembols|devuelv|fraud|estaf|me deben|nos deben|denunci|profeco|"
    r"demand(?!e al? |amos)|rater|ladr|me robaron|me estan robando|"
    r"mi dinero|me regresen|regresen?me|me reintegr|de vuelta mi|"
    r"me cobraron de mas|cobro de mas|no me (?:lo |la )?regresaron)")
# "Vergüenza" y "no mames" (asombro) no son insultos.
INSULTO = re.compile(r"(put[oa]|pendej|pinche|verg(?!uenz|onz)|mierda|chinga|imbecil|estupid|idiot|"
                     r"(?<!no )mames|culer|mamon|baboso)")
# Palabras enteras: "uso personal" no pide una persona. Y "persona" sola tampoco:
# en una renta es la cuenta de huéspedes (*"para 100 persona"*, *"por persona"*);
# en Finca Emiliano, 11 de 11 disparos eran eso (2026-10-27). Pedir una persona
# es "hablar con una persona", "una persona real", "que me atienda alguna persona".
PIDE_PERSONA = re.compile(
    r"\b(?:asesor(?:a|es|as)?|humano|ejecutiv[oa]|operador(?:a)?|encargad[oa]|alguien real)\b"
    r"|(?<!para )(?<!por )(?<!cada )\b(?:una|alguna|otra) persona\b(?!\s+(?:moral|fisica|mas|adicional|extra))"
    r"|\bpersona real\b|\bhablar con (?:una |alguna )?persona\b")
PREGUNTA_SI_ES_BOT = re.compile(
    r"\b(?:eres|es|son|sera|estoy hablando con|hablo con|me contesta|me responde)\s+"
    r"(?:un |una |el |la )?(?:bot|robot|maquina|ia|inteligencia artificial|programa|contestadora|"
    r"asistente virtual|persona real|humano|persona)\b"
    r"|\bes (?:una )?respuesta automatica\b|\bes automatico\b|\bpuro bot\b")


def es_reclamo(texto: str) -> bool:
    t = normalizar(texto)
    return bool(RECLAMO.search(t) or INSULTO.search(t))


def pregunta_si_es_bot(texto: str) -> bool:
    """Va antes de "pide una persona": *"eres humano?"* trae "humano"."""
    return bool(PREGUNTA_SI_ES_BOT.search(normalizar(texto)))


def pide_persona(texto: str) -> bool:
    return bool(PIDE_PERSONA.search(normalizar(texto)))


# --------------------------------------------------------------------------- #
#  El acuse, el cierre y la pelota que es suya (expediente_cotizacion.py)     #
# --------------------------------------------------------------------------- #
# El acuse no le pasa la pelota al negocio; el cierre termina la conversación.
ACUSE = re.compile(
    r"^(?:(?:hola|buen dia|buenos dias|buenas tardes|buenas noches)\s+)?"
    r"(?:(?:ok\w*|oka+y|okey|oki|va|vale|sale|perfecto|excelente|entendido|bueno|"
    r"enterado|de acuerdo|a ok|ah ok|ah ya|ya veo|muy bien|bien|listo|claro|entiendo|"
    r"(?:que )?lastima|ni modo|se agradece|(?:te|le|les) agradezco(?: mucho| muchisimo)?|"
    r"si de nada|de nada|muchas gracias|mil gracias|muchas grax|mil grax|gracias igualmente|"
    r"igualmente|gracias|garcias|gracis|grax|thanks|"
    r"(?:yo\s+)?(?:te|le|les)\s+(?:aviso|confirmo|escribo|marco)|"
    r"lo (?:voy a )?pienso|lo voy a pensar|lo checo|saludos|bendiciones|"
    r"gracias a (?:usted|ustedes|ti)|a (?:usted|ustedes|ti)|"
    r"(?:muchas |mil )?gracias por (?:la |su |tu )?(?:atencion|ayuda|apoyo|informacion|info|todo)|"
    r"(?:ahi|hay|ai) nos (?:vemos|encontramos)|"
    r"(?:le |te )?agradezco (?:su|tu) (?:tiempo|atencion|ayuda)|"
    r"que tenga (?:buen dia|buena tarde|buena noche)|igual)[\s,.!]*)+$")
CIERRE = re.compile(
    r"\bya\s+(?:lo\s+|la\s+|le\s+|me\s+|nos\s+)?(?:reserve|rente|aparte|encontre|consegui|resolvi|decidi"
    r"|reservamos|rentamos|apartamos|encontramos|conseguimos|resolvimos|decidimos)\b"
    r"\s*(?:otr[oa]|en otro|en otra)?"
    r"|^(?:muchas\s+)?gracias,?\s+ya\s+no[\s,.!]*$"
    r"|\bno\s+(?:hace\s+falta|es\s+necesario)\b|\blo\s+tendre\s+en\s+cuenta\b"
    r"|\bya\s+(?:no\s+)?(?:me\s+)?(?:interesa|necesito|ocupo)\b"
    r"|\bno\s+me\s+interesa\b|^no,?\s+gracias\b"
    r"|\b(?:por el momento|por ahora|mejor) no,?\s+(?:muchas\s+)?gracias\b"
    r"|^ya no[\s,.!]*(?:muchas\s+)?(?:gracias)?[\s,.!]*$"
    r"|\b(?:estan|esta|es|sale|muy)\s+(?:muy\s+|bien\s+)?car[oa]s?\b.*\b(?:gra(?:c|s)ias|grax)\b"
    r"|\bgra(?:c|s)ias\b.*\b(?:estan|esta|muy)\s+(?:muy\s+)?car[oa]s?\b"
    r"|\bno\s+me\s+alcanza\b|\bdejelo\s+mejor\b|\bmejor\s+lo\s+dejo\b"
    r"|\bnos\s+decidimos\s+por\s+otr[oa]s?\b|\b(?:sera|seria)\s+(?:en|para)\s+otra\s+ocasion\b"
    r"|\bya\s+no\s+(?:lo\s+|la\s+)?vamos\s+a\s+(?:hacer|rentar|necesitar)\b"
    r"|^(?:esta|estas|se)\s+equivocad[oa]\b|\bnumero\s+equivocado\b"
    # Corrida GM, 2026-10-29 (respuestas a la ronda): "ya tenemos opción", "ya tengo
    # un lugar tratado", "será próxima vez, ahora no", "tuve que cancelar".
    r"|\bya\s+(?:tenemos|tengo)\s+(?:otra\s+|una\s+|un\s+)?(?:opcion|lugar|reservacion)\b"
    r"|\b(?:sera|seria)\s+(?:la\s+)?proxima\s+vez\b|\bahora\s+no[\s,.!]*$"
    r"|\b(?:tuve|tuvimos)\s+que\s+cancelar\b|\bya\s+tienen\s+(?:una\s+)?reservacion\b")
LA_PELOTA_ES_SUYA = re.compile(
    r"\b(?:lo pienso|lo voy a pensar|(?:te|le|les) aviso|(?:te|le) confirmo|"
    r"quedo (?:al )?pendiente|estoy (?:al )?pendiente|"
    r"(?:te|le) (?:hablo|ablo|marco|escribo|busco|contacto)|"
    r"me pongo en contacto|por el momento espero|dejeme (?:consultarlo|checar|ver)|"
    r"dejame (?:consultarlo|checar|ver|juntar)|lo consulto|"
    r"lo (?:platico|comento|consulto|hablo) con|lo voy a (?:platicar|comentar|consultar|juntar|reunir)|"
    r"voy a (?:reunir|juntar|ahorrar|conseguir) (?:el|la|los|lo)|"
    r"cuando tenga (?:el dinero|la lana|lo del|todo)|"
    r"(?:te |se )?lo checo|checo,? gracias|"
    r"(?:aun |todavia )?(?:lo |la )?(?:estoy|sigo|seguimos|estamos) (?:evaluando|pensando|analizando|"
    r"viendolo|checando|revisando)|(?:te|le|les) avisare|"
    r"aun no (?:tengo|tenemos|hay) noticias|dejeme pensarlo|dejame pensarlo|"
    r"(?:deme|dame|deje|deja) (?:un )?(?:tiempo|chance)|lo contacto|"
    r"(?:deje|deja|dejeme|dejame|luego|despues|al rato|ahorita) (?:lo |la )?"
    r"(?:platicamos|platico|pensamos|pienso|checamos|vemos)"
    # Finca Emiliano (2026-10-27): el cliente lo consulta con su gente.
    r"|regreso (?:contigo|con usted|con ustedes)"
    r"|(?:deja|dejame|dejeme|deje) (?:le |les )?(?:pregunto|consulto|comento|ensen\w*|muestro|mostrarlo|mostrarla)"
    r"|hablo con mi (?:familia|esposo|esposa|marido|novio|novia|jefe|jefa|mama|papa|hermana|hermano)"
    r"|(?:le|les) (?:comento|pregunto|paso los datos) a mi (?:familia|esposo|esposa|marido|novio|novia|jefe|jefa)"
    r"|espero tener(?:le|te)? (?:la|una) (?:confirmacion|respuesta)"
    # Corrida GM, 2026-10-29.
    r"|(?:le|te|les) (?:avisamos|avisaremos|escribimos|confirmamos)|me comunico con (?:usted|ustedes|ud)"
    r"|voy a (?:comentar|platicar|consultar)(?:lo|la)?)\b")
# "Estoy pendiente de mi presupuesto" NO es "quedo pendiente": espera algo que le
# debemos (Finca Emiliano, 2026-10-27: el turno callaba).
SIGUE_PIDIENDO = re.compile(r"\?|\b(?:quiero|necesito|cuanto|cotiza\w*|ahora|precio|disponib\w*|presupuesto|estimado|"
                            r"podria|podrias|me (?:puede|pueden|puedes|manda|mandas|pasa|pasas|envia|envias))\b")
PROMESA = re.compile(
    r"\b(?:ma[nñ]ana|al rato|luego|ahorita|hoy|en un momento)\b[^.]{0,40}"
    r"\b(?:le mando|le env[ií]o|te mando|te env[ií]o|se lo mando|le paso|paso|los mando)\b"
    r"|\b(?:le mando|le env[ií]o|te mando|te env[ií]o|se lo mando|le paso|te paso)\b[^.]{0,30}"
    r"\b(?:ma[nñ]ana|al rato|luego|hoy|en un rat(?:o|ito))\b"
    r"|\bs[ií] checo\b|\bvoy a checar\b"
    r"|^(?:ahorita |al rato |luego )?(?:te|le|se la|se lo) (?:mando|envio|paso)\b"
    r"|^(?:si,? )?(?:deme|dame|permitame|permiteme|espereme|esperame) (?:unos? )?"
    r"(?:\d+|cinco|diez|quince|veinte|treinta|media) (?:min\w*|hora)"
    r"|^(?:voy manejando|mas tarde|mas tardecito|al rato|en un rato)\W*$")
_ARRANQUE = (r"(?:(?:ok\w*|oka+y|okey|oki|va|vale|sale|bueno|perfecto|excelente|ah|aa+h?|ya|claro|listo|"
             r"entendido|enterado|de acuerdo|esta bien|muy bien|bien|gracias|muchas gracias|mil gracias|"
             r"pues|entonces|igualmente|si|ok si|hola)\s+)*")
CLAUSULA_SIN_PEDIDO = re.compile(
    "^" + _ARRANQUE + r"(?:"
    r"muy amable(?: gracias)?|que amable|"
    r"(?:muchas |mil )?gracias (?:por|x) (?:la |su |tu |el |toda la |todo |tanto )?"
    r"(?:atencion|informacion|info|tiempo|ayuda|apoyo|respuesta|paciencia|todo|atenderme|responder|contestar)"
    r"(?: brindada| prestada)?|"
    r"estamos en contacto|seguimos en contacto|"
    r"(?:quedo|quedamos|estoy|estamos|me quedo) (?:atent[oa]s?|en espera|a la espera|al pendiente|"
    r"pendientes?|a sus ordenes|al tanto)(?: de (?:su|sus|tu) \w+)?|"
    r"(?:dios )?(?:lo|la|los|te|le) bendiga|bendiciones|ahi andamos|nos vemos|hasta luego|"
    r"(?:entonces )?quedamos (?:asi|en eso)|(?:va )?que sea asi|asi quedamos|"
    r"(?:ahorita )?lo (?:reviso|checo|veo|analizo|platico|comento|consulto|pienso|leo)"
    r"(?: con (?:mi |el |la )?\w+)?(?: y (?:le|te) (?:aviso|digo|confirmo))?|"
    r"lo voy a (?:revisar|checar|ver|pensar|platicar|comentar|consultar|juntar|reunir)(?: con (?:mi |el |la )?\w+)?|"
    r"espero (?:su|sus|tu|tus) (?:mensaje|respuesta|indicaciones|llamada|informacion|confirmacion)|"
    r"(?:si |ya )*(?:vi|lo vi|lo lei|lei|entendi|anotado)|"
    r"buen(?:a|o)s? (?:dia|tarde|noche)s?|que (?:tenga|tengan|este) (?:un )?"
    r"(?:buen|bonito|excelente|lindo)? ?(?:dia|tarde|noche|fin)(?: de semana)?|saludos|igualmente|"
    r"ahi (?:le|te) (?:aviso|digo|confirmo)|"
    r"(?:y )?(?:disculpe|disculpa|perdon|perdone)(?: (?:las|la|por las|por la) molestias?)?|"
    r"(?:me|nos) (?:avisa|avisas|avisan|confirma|confirmas)(?: (?:porfa|por favor|cualquier cosa))?|"
    r"(?:lo que (?:se ofrezca|necesite|ocupe)|cualquier (?:cosa|duda))(?: (?:me|nos) (?:avisa|avisas|dice|dices|escribe))?|"
    r"a (?:ti|usted|ustedes)|para servirle|(?:con )?mucho gusto|"
    r"(?:entonces )?ya (?:esta|quedo) (?:aclarado|claro)|porfa|por favor|confirmo|confirmado|"
    r"voy a esperar(?: \w+){0,8}|"
    # Corrida GM, 2026-10-29 (pendientes etiquetados a ciegas):
    r"(?:linda|lindo|bonita|bonito|feliz) (?:tard\w*|dia|noche|fin)(?: de semana)?(?: \w{1,2})?|"
    r"gracias (?:de|por) todas (?:maneras|formas)|de todas (?:maneras|formas)(?: gracias)?|"
    r"(?:nunca|no) me fije(?: en eso)?|gracias por estar (?:al )?pendientes?|"
    r"(?:solo )?(?:nos|me) falta(?:n)? (?:por )?(?:definir|confirmar|decidir)(?: \w+){0,4}|"
    r"(?:aun|todavia) no (?:sabemos|se|decidimos|decido)(?: \w+){0,6}|"
    r"a ver si (?:aun|todavia) (?:esta|estan|hay|tienen) (?:disponible|libre|lugar)|"
    r"ok\w*|oka+y|okey|oki|va|vale|sale|bueno|perfecto|excelente|ah|ya|claro|listo|"
    r"entendido|enterado|de acuerdo|esta bien|muy bien|bien|gracias|gracis|si|pues|correcto|hola"
    r")(?:\s+(?:muchas gracias|mil gracias|gracias|grax|muchas grax|saludos|porfa|por favor))*$")
#: El cliente dice con todas sus letras que él vuelve (corrida GM, 2026-10-29): manda
#: sobre el resto de la ráfaga si no hay pregunta ni número (*"Tenemos un familiar
#: hospitalizado (...) Si después decidimos ir le avisamos"*).
APLAZA_FUERTE = re.compile(
    r"\bsi (?:despues|luego|mas adelante) (?:decidimos|decido|nos decidimos|nos animamos|confirmamos)\b.{0,40}"
    r"\b(?:le|te|les) (?:aviso|avisamos|avisare|avisaremos|escribo|escribimos|confirmo|confirmamos)\b"
    r"|\bme comunico con (?:usted|ustedes|ud)\b.{0,25}\b(?:mas adelante|despues|luego|la proxima|en la semana)\b"
    r"|\bvoy a (?:comentar|platicar|consultar)(?:lo|la)?\b.{0,25}\b(?:le|te|les) (?:escribo|aviso|confirmo|marco)\b")
_EMPIEZA_CON_SI = re.compile(r"^(?:ah |a |ok |pues )?si\b")
_SOLO_SALUDO = re.compile(r"^(?:hola|ola|que tal|buen(?:os|as)?(?: (?:dia|dias|tarde|tardes|noche|noches))?)"
                          r"(?: (?:buen(?:os|as)? (?:dia|dias|tarde|tardes|noche|noches)|que tal))?$")
# Del otro lado a veces contesta otra máquina.
CONTESTADOR = re.compile(
    r"\bsoy (?:el|la|un|una) asistente\b|\bte he conectado con\b|\balguien te atendera en breve\b"
    r"|\ben breve (?:le|te) atenderemos\b|\bmensaje automatico\b|\brespuesta automatica\b"
    r"|\bgracias por comunicarte con\b|\bnuestro horario de atencion\b")


def _clausulas(texto: str) -> list[str]:
    t = " | ".join(normalizar(r) for r in (texto or "").splitlines() if r.strip())
    partes = re.split(r"[,.;!¡\n|]+|\s+(?:y|pero)\s+(?=(?:lo|le|te|ya|voy|cuando|espero|quedo|gracias|muchas|"
                      r"estamos|ahi|nos|que|saludos|bendiciones)\b)"
                      r"|(?<!ahorita)\s+(?=lo\s+(?:platico|reviso|checo|pienso|comento|consulto|veo|leo)\b)", t)
    return [s for s in (" ".join(re.sub(r"[^\w\s]", " ", p).split()) for p in partes) if s]


def _sin_pedido(clausulas: list[str]) -> bool:
    for c in clausulas:
        if ACUSE.match(c) or CLAUSULA_SIN_PEDIDO.match(c):
            continue
        if PROMESA.search(c) and not re.search(r"\b(?:cuanto|precio|costo)\b", c):
            continue
        if LA_PELOTA_ES_SUYA.search(c) and len(c.split()) <= 8 and not SIGUE_PIDIENDO.search(c):
            continue
        return False
    return True


def nada_que_contestar(texto: str, con_si: bool = True) -> bool:
    """¿No le pide nada al negocio? Cortesía, acuse, el cliente que dice que él
    sigue (*"lo platico"*, *"mañana le mando"*) o que ya leyó. Sin `?`, sin cifra
    y sin dato. `con_si=False`: un "sí" al frente puede contestar una pregunta
    del negocio, y ése lo lee el hilo."""
    crudo = (texto or "").strip()
    if not crudo or "?" in crudo or "¿" in crudo or re.search(r"\d", crudo):
        return False
    if crudo and not _solo_letras(crudo):
        return True  # 👍, 🙏 solos: un acuse
    if not con_si and _EMPIEZA_CON_SI.match(_solo_letras(crudo)):
        return False
    if APLAZA_FUERTE.search(_solo_letras(crudo)):
        return True
    clausulas = _clausulas(crudo)
    if not clausulas or all(_SOLO_SALUDO.match(c) for c in clausulas):
        return False  # un saludo solo sí pide respuesta: el saludo
    if _sin_pedido(clausulas):
        return True
    renglones = [r for r in crudo.splitlines() if r.strip()]
    return len(renglones) > 1 and _sin_pedido(_clausulas(" ".join(renglones)))


def es_cierre(texto: str) -> bool:
    """Termina la conversación: ya rentó en otro lado, ya no le interesa, está caro."""
    t = _solo_letras(texto)
    # "ahora no" no es "ahora sí quiero": no cuenta como que sigue pidiendo.
    return bool(t) and bool(CIERRE.search(t)) and not SIGUE_PIDIENDO.search(
        re.sub(r"\bahora no\b", "", normalizar(texto)))


def es_contestador(texto: str) -> bool:
    return bool(CONTESTADOR.search(normalizar(texto)))


def es_acuse(texto: str) -> bool:
    crudo = (texto or "").strip()
    if not crudo:
        return False
    letras = _solo_letras(crudo)
    if not letras:
        return True  # 👍 solo
    return bool(ACUSE.match(letras) or es_contestador(crudo)
                or ("?" not in crudo and LA_PELOTA_ES_SUYA.search(letras) and not SIGUE_PIDIENDO.search(letras)))


# --------------------------------------------------------------------------- #
#  El "ok" que aplaza no es un sí (libro_cotizaciones.py, corrida 9)           #
# --------------------------------------------------------------------------- #
_SI_DEBIL = re.compile(r"^(?:va|dale|ok\w*|okey|si|sale|perfecto|de acuerdo)\b")
_NO_ES_UN_SI = re.compile(
    r"\b(?:ya vi|lo vi|lo lei|espero (?:su|sus|tu) \w+|(?:le|te) (?:aviso|escribo|marco|hablo|confirmo)|"
    r"cuando tenga|lo (?:pienso|voy a pensar|platico|reviso|checo)|ahi andamos|deme un tiempo|aun no decido)\b")
_SI_FUERTE = re.compile(r"\b(?:lo apart\w*|apart(?:o|amos|ala|elo)|reserv(?:o|amos|ala|ela)|como (?:le )?deposit\w*|"
                        r"a que cuenta|me pasa(?:s)? (?:la|los) (?:cuenta|datos)|cerramos|lo tomamos|la tomamos|"
                        r"si (?:la|lo) quiero|nos interesa)\b")


def senal_tras_la_cotizacion(textos: list[str]) -> str:
    """Qué dijo el cliente después de la cotización: `acepta`, `tibio`, `cierra`, `silencio` o `respondio`."""
    ts = [normalizar(t) for t in textos if (t or "").strip()]
    if not ts:
        return "silencio"
    if any(es_cierre(t) for t in ts):
        return "cierra"
    if any(_SI_FUERTE.search(t) for t in ts):
        return "acepta"
    if any(_SI_DEBIL.search(t) for t in ts):
        return "respondio" if any(_NO_ES_UN_SI.search(t) for t in ts) else "tibio"
    return "respondio"
