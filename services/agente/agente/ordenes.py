"""Las órdenes de la mesa: UNA tabla que lee, enseña la ayuda y dice quién puede.

Dueño, 2026-10-31: *"quiero que tenga por lo menos 50 funciones nuevas o
reconozca comandos más seguido sácalos de gestor Morelos"*. Lo que se trae de
Gestor (`dueno.py`, `cierre.py`, `consultas.py`), llevado a la renta:

- **El formato de WhatsApp no cambia la orden** (Gestor, 2026-10-07: su
  *"\\*cierra 56 6408 6910\\*"* llevaba asteriscos y se fue a la IA). Ni la
  diagonal (*/estado*), ni los acentos, ni *"oye asistente, …"*, ni *"porfa"*.
- **Una errata no tira la orden** (*"pendietes"*): la palabra se corrige contra
  las de la tabla. Si con la corrección sale una orden que cambia algo, no se
  ejecuta: se pregunta (`confirmar`). Leer, sí.
- **Al cliente se le nombra como se pueda**: los últimos 4 dígitos (*…1234*),
  el teléfono con espacios o guiones, o su número en la última lista que se le
  mandó a esa administradora (*"ficha 2"*).
- **Una regla escrita en dos listas no gobierna**: la ayuda, el permiso y el
  manejador salen de esta tabla (`tests/test_agente_ordenes.py` amarra que
  cada orden tenga los tres).

Aquí solo se lee: qué pidió y con qué datos. Lo que hace cada orden vive en
`capacidades.py`; quién la puede dar y el buzón, en `mesa.py`.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from datetime import date

TODAS, QUIEN_APRUEBA = "todas", "aprueba"


@dataclass(frozen=True)
class Orden:
    id: str
    patron: re.Pattern
    quien: str          # todas | aprueba
    tema: str           # para "ayuda <tema>"
    ayuda: str          # una línea: cómo se escribe y qué hace
    cambia: bool = False  # escribe algo (no solo lee): con errata, se pregunta antes


# Lo que va antes de un cliente: *…1234*, *1234*, *777 123 4567*, *+52 1 777-123-4567* o *2*.
#: El teléfono entero (seguido o en grupos con espacio o guion), los últimos 4, o el lugar en la lista.
#: Un teléfono en grupos pide separador entre grupos: así *"cerró 1234 15000"* no se lee como un teléfono.
_TEL = r"\+?\d{10,13}|(?:\+?52[ -]?(?:1[ -]?)?)?\d{2,3}[ -]\d{3,4}[ -]\d{4}"
_REF = rf"(?P<ref>{_TEL}|\d{{4}}|\d{{1,2}})(?!\d)"
_PREP = r"(?:a\s+la\s+|a\s+el\s+|a\s+|al\s+|de\s+la\s+|de\s+|del\s+|con\s+(?:el\s+|la\s+)?|en\s+(?:el\s+|la\s+)?|el\s+|la\s+)?"
_REF_OPC = rf"(?:\s+{_PREP}(?:cliente\s+|numero\s+)?{_REF})?"
_REF_OBL = rf"\s+{_PREP}(?:cliente\s+|numero\s+)?{_REF}"
#: El cliente primero (*"4521 atendido"*, *"el 4521 ya cerró"*): mismo dato, otro nombre de grupo.
_REF_ANTES = rf"(?:(?:el|la|al)\s+)?(?:cliente\s+)?{_REF.replace('?P<ref>', '?P<ref2>')}\s+"
_NUMS = r"(?:el\s+)?\d{1,3}(?:(?:\s*,\s*|\s+(?:y|ni)\s+|\s+)(?:el\s+)?\d{1,3})*"
_LISTA = rf"(?P<lista>todos|todas|todo|{_NUMS})"
#: Con un verbo de todos los días (*manda*, *borra*, *si a*) "todo" no basta: número, o la palabra borradores.
_LISTA_DEBIL = rf"(?:(?:borradores?|mensajes?)\s+(?P<lista2>todos|todas|{_NUMS})|(?P<lista3>{_NUMS})|(?P<lista4>todos)\s+los\s+borradores)"
_PROP = r"(?:\s+(?:la\s+|el\s+|en\s+la\s+|en\s+el\s+|de\s+la\s+|de\s+el\s+|del\s+)?(?P<prop>finca|quinta|ambas|las dos|las dos casas|[a-z]{4,20}))?"
#: Apartar/liberar: una casa con nombre propio va seguida de la fecha (*"aparta palapa el 20"*); una palabra
#: cualquiera (*"aparta la mesa para el sábado"*, *"reserva el brincolín para la fiesta en la finca el 15"*) no.
_NO_CASA = r"(?!(?:para|mesa|mesas|salon|silla|sillas|lugar|lugares|cita|numero|estacionamiento|cuarto|restaurante)\b)"
_FECHA_YA = r"(?:(?:del?|el|los)\s+)?\d{1,2}(?!\d)"  # "el 15", no "el 4521" (eso es un cliente)
_PROP_CAL = (r"(?:\s+(?:la\s+|el\s+|en\s+la\s+|en\s+el\s+)?(?P<prop>finca|quinta|ambas|las dos|las dos casas)"
             r"\s+(?P<resto>.*\d.*)"
             rf"|(?:\s+(?:la\s+|el\s+|en\s+la\s+|en\s+el\s+)?{_NO_CASA}(?P<prop2>[a-z]{{4,20}}))?\s+(?P<resto2>{_FECHA_YA}.*))")


def _o(id_: str, patron: str, tema: str, ayuda: str, quien: str = TODAS, cambia: bool = False) -> Orden:
    return Orden(id_, re.compile(rf"^(?:{patron})$"), quien, tema, ayuda, cambia)


#: El orden importa: la primera que encaja gana (lo largo antes que lo corto).
TABLA: tuple[Orden, ...] = (
    # ------------------------------------------------------------------ ayuda
    _o("ayuda", r"(?:ayuda|help|menu|comandos|ordenes|que puedes hacer|que sabes hacer|que haces|opciones|\?+)"
                r"(?:\s+(?:de|con|para|sobre)?\s*(?P<tema>[a-z]+))?", "ayuda",
       "ayuda · ayuda clientes · ayuda rondas · ayuda precios · ayuda calendario · ayuda envio"),
    # ------------------------------------------------------------ el tablero
    _o("estado", r"(?:(?:el\s+|mi\s+)?(?:estado|reporte|resumen|tablero)(?:\s+(?:del dia|de hoy))?|pulso|numeros"
                 r"|como vamos(?:\s+hoy)?|como va todo|como va el negocio"
                 r"|que hay|que tengo|mandame el reporte|reporte ya|dame el reporte|como estamos)",
       "tablero", "estado: el reporte del día (semáforo, envío, rondas, tiempo al número)"),
    _o("hoy", r"(?:hoy|que paso hoy|resumen de hoy|el dia|como va el dia|movimientos de hoy)", "tablero",
       "hoy: lo que pasó hoy (quién escribió, qué salió, qué contestaron)"),
    _o("semana", r"(?:semana|la semana|resumen de la semana|como va la semana|esta semana)", "tablero",
       "semana: los últimos 7 días contra los 7 anteriores"),
    _o("oportunidades", r"(?:oportunidades|donde esta el dinero|dinero pendiente|que se puede cerrar"
                        r"|a quien le vendo|ventas pendientes|lo que se puede vender)", "tablero",
       "oportunidades: quién está más cerca de rentar (contestaron, prometido, cotizado)"),
    # ---------------------------------------------------------- los clientes
    _o("pendientes", r"(?:pendientes|lo pendiente|que me falta|a quien (?:le )?contesto|a quien contestar"
                     r"|que falta|por contestar|quien espera|(?:los\s+|mis\s+)?pendientes|que pendientes hay|hay pendientes"
                     r"|que me falta contestar|a quien (?:le )?contesto primero|quien esta esperando|quienes esperan"
                     r"|a quien (?:le )?tengo que contestar)(?:\s+(?:pagina\s+)?(?P<pagina>\d{1,2}))?",
       "clientes", "pendientes: a quién contestar primero (pendientes 2: la página 2)"),
    _o("urgentes", r"(?:urgentes|lo urgente|rojos|en rojo|lo rojo|que es urgente)", "clientes",
       "urgentes: solo lo que está en rojo"),
    _o("contestaron", r"(?:contestaron|quien contesto|quienes contestaron|respuestas|respondieron"
                      r"|contestaron al seguimiento|quien respondio|ya contestaron|ya respondieron|alguien contesto"
                      r"|alguien respondio|quien me contesto|quien me respondio|quien ha contestado|que contestaron)", "clientes",
       "contestaron: quién contestó a un seguimiento y espera respuesta"),
    _o("promesas", r"(?:promesas|quedamos de mandar|lo prometido|prometidos|que prometimos|que debemos)",
       "clientes", "promesas: a quién le quedamos de mandar algo"),
    _o("reclamos", r"(?:reclamos|quejas|molestos|enojados|inconformes)", "clientes",
       "reclamos: quién se quejó"),
    _o("nuevos", r"(?:nuevos|sin atender|nadie les ha contestado|los nuevos|nuevos clientes|prospectos nuevos)",
       "clientes", "nuevos: a quién solo le contestó la máquina"),
    _o("medios", r"(?:medios|fotos|audios|solo fotos|solo audios|archivos|notas de voz)", "clientes",
       "medios: quién mandó solo foto, audio o archivo (hay que verlo en el teléfono)"),
    _o("seguimiento", r"(?:seguimiento|seguimientos|a quien le doy seguimiento|cotizados|en seguimiento)",
       "clientes", "seguimiento: cotizados y preguntas sin respuesta del cliente (de 1 a 21 días)"),
    _o("ficha", rf"(?:(?:la\s+)?ficha|cliente|quien es(?:\s+(?:el|la))?|que pidio|info|informacion|datos|ver|abre){_REF_OBL}", "clientes",
       "ficha …1234: qué pidió, cuántos son, qué fechas, en qué va y sus notas"),
    _o("historial", rf"(?:historial|platica|conversacion|mensajes|chat|que dijo|lo que dijo){_REF_OBL}", "clientes",
       "historial …1234: los últimos mensajes de esa plática"),
    _o("busca", r"(?:busca|buscar|buscame|encuentra|quien dijo|quien pregunto por)\s+(?P<texto>.{3,60})",
       "clientes", "busca boda: las pláticas que dicen esa palabra"),
    _o("notas", rf"(?:notas|apuntes|que anote){_REF_OPC}", "clientes",
       "notas …1234: lo anotado de ese cliente (notas a secas: las últimas)"),
    _o("marcados", r"(?:marcados|apartados de la ronda|no contactar|lista negra|los que llevo|bloqueados)",
       "clientes", "marcados: a quién no se le escribe y quién lo lleva usted"),
    # -------------------------------------------- lo que hace la dueña con un cliente
    _o("nota", rf"(?:nota|anota|apunta|apuntale|anotale){_REF_OBL}\s+(?P<texto>.+)", "clientes",
       "nota …1234 paga el viernes: queda en la ficha", cambia=True),
    _o("no_escribir", rf"(?:no le escribas|no le escriban|no escribirle|no contactar|no le mandes nada"
                      rf"|sacalo de las rondas|sacala de las rondas|quita de las rondas|no molestar|no le mandes"
                      rf"|ya no le escribas|ya no le mandes nada|ya no le mandes|no le escribas mas){_REF_OBL}"
                      rf"|{_REF_ANTES}(?:ya\s+)?no le escribas(?:\s+mas)?",
       "clientes", "no le escribas …1234: ninguna ronda ni envío le llega", QUIEN_APRUEBA, cambia=True),
    _o("si_escribir", rf"(?:ya puedes escribirle|ya le pueden escribir|vuelve a escribirle|si le puedes escribir"
                      rf"|regresalo a las rondas|regresala a las rondas){_REF_OBL}", "clientes",
       "ya puedes escribirle …1234: deshace el no le escribas", QUIEN_APRUEBA, cambia=True),
    _o("lo_llevo", rf"(?:(?:yo\s+|ese\s+|esa\s+)?l[oa]\s+(?:llevo|tomo|agarro|atiendo)(?:\s+yo)?|me l[oa] quedo"
                   rf"|(?:yo\s+)?me encargo(?:\s+yo)?){_REF_OBL}", "clientes",
       "lo llevo …1234: usted lo atiende; el equipo no le escribe", QUIEN_APRUEBA, cambia=True),
    _o("suelta", rf"(?:suelta|sueltalo|sueltala|ya no lo llevo|ya no la llevo|liberalo|liberala){_REF_OBL}",
       "clientes", "suelta …1234: el equipo vuelve a darle seguimiento", QUIEN_APRUEBA, cambia=True),
    _o("atendido", rf"(?:atendido|atendida|ya le conteste|ya le respondi|ya lo atendi"
                   rf"|ya la atendi|ya hable con|ya le hable|ya le marque|ya le llame){_REF_OBL}"
                   rf"|{_REF_ANTES}(?:ya\s+)?(?:atendido|atendida)", "clientes",
       "ya le contesté …1234: sale de pendientes hasta que vuelva a escribir", QUIEN_APRUEBA, cambia=True),
    _o("cerro", rf"(?:(?:ya\s+)?(?:cerro|cerramos|rentaron|reservaron|apartaron){_REF_OBL}"
                rf"|{_REF_ANTES}(?:ya\s+)?(?:cerro|rentaron|reservaron|apartaron))"
                r"(?:\s+(?:en|por|con)?\s*\$?\s*(?P<monto>\d{1,3}(?:\s\d{3})+|\d[\d,.]*(?:\s*mil)?))?", "clientes",
       "cerró …1234 15000: la renta queda asentada (sin monto también)", QUIEN_APRUEBA, cambia=True),
    # Con "que" explícito: *"mándale al 7777 la ubicación"* es una instrucción para ella, no un texto (adversarial).
    _o("dile", rf"(?:dile|digale|escribele|mandale|contestale|respondele)(?:\s+(?:porfa|por favor))?{_REF_OBL}"
               r"(?![\s-]*\d)\s+que\s+(?P<texto>.+)",
       "clientes", "dile …1234 que ya está apartado: le enseño lo que saldría y sale cuando conteste sí, mándalo",
       QUIEN_APRUEBA, cambia=True),
    _o("confirma", r"(?:si|va|ok|dale|sale)?\s*(?:mandalo|mandala|envialo|enviala|si mandalo|si envialo|si|va|dale)",
       "clientes", "sí, mándalo: manda lo que me dictó (vale 10 minutos)", QUIEN_APRUEBA, cambia=True),
    _o("cancela", r"(?:no|no lo mandes|no la mandes|cancela|cancelalo|mejor no|no mandes eso)", "clientes",
       "no lo mandes: cancela lo que me dictó", QUIEN_APRUEBA, cambia=True),
    # ------------------------------------------------------- rondas y borradores
    _o("aprueba_borradores", rf"(?:aprueba|apruebo|apruebalos|mandalo|mandalos|aprobar)\s+(?:los\s+|el\s+)?"
                             rf"(?:borradores?\s+|mensajes?\s+)?{_LISTA}"
                             rf"|(?:manda|envia|si a|si al|dale a|dale al)\s+(?:los\s+|el\s+)?{_LISTA_DEBIL}", "rondas",
       "aprueba 1 3: manda esos borradores (aprueba todos: la lista completa)", QUIEN_APRUEBA, cambia=True),
    _o("descarta", rf"(?:descarta|descartalos|no mandes)\s+(?:los\s+|el\s+)?(?:borradores?\s+|mensajes?\s+)?{_LISTA}"
                   rf"|(?:quita|borra|tira|no va)\s+(?:los\s+|el\s+)?{_LISTA_DEBIL}", "rondas", "descarta 2: ese borrador no sale", QUIEN_APRUEBA, cambia=True),
    _o("aprueba", r"(?:aprueba|apruebo|aprobar|si aprueba|manda|mandala|dale con|dale a|si a|si manda|envia|suelta)\s+(?:la\s+)?ronda"
                  r"(?:\s+(?P<nombre>[a-z0-9][a-z0-9-]{2,59}))?", "rondas",
       "aprueba la ronda: manda los seguimientos que preparó el equipo", QUIEN_APRUEBA, cambia=True),
    _o("descarta_ronda", r"(?:descarta|no mandes|cancela|tira|borra)\s+(?:la\s+)?ronda(?:\s+(?P<nombre>[a-z0-9][a-z0-9-]{2,59}))?",
       "rondas", "descarta la ronda: nada de esa ronda sale", QUIEN_APRUEBA, cambia=True),
    _o("borradores", r"(?:borradores|que espera mi si|que esperan mi si|por aprobar|que apruebo|esperan su si"
                     r"|lo que espera|que hay que aprobar|que mando|(?:los\s+|mis\s+)?borradores|que borradores hay"
                     r"|hay borradores|que hay por aprobar)", "rondas",
       "borradores: lo que espera su sí, numerado"),
    _o("rondas", r"(?:rondas|las rondas|que rondas hay|lista de rondas)", "rondas",
       "rondas: las rondas cargadas y en qué van"),
    _o("ronda", r"(?:ronda|la ronda|como va la ronda|detalle de la ronda)(?:\s+(?P<nombre>[a-z0-9][a-z0-9-]{2,59}))?",
       "rondas", "ronda <nombre>: el detalle de una ronda (sin nombre, la última)"),
    _o("desenlace", r"(?:desenlace|como le fue a la ronda|resultados|como les fue|resultado de las rondas"
                    r"|que paso con la ronda|efectividad)", "rondas",
       "resultados: qué pasó después de cada ronda (contestaron, cerraron, esperan)"),
    # ------------------------------------------------------------- el envío
    _o("cola", r"(?:cola|envios|envio|la cola|(?:que|lo que)\s+(?:sale|va a salir)(?:\s+hoy)?|como va la cola|que hay en la cola)", "envio",
       "cola: lo que espera su sí y lo que sale"),
    _o("enviados", r"(?:enviados|que salio|que salio hoy|que se mando|que se mando hoy|mandados|enviados hoy)",
       "envio", "enviados: lo que salió hoy"),
    _o("fallidos", r"(?:fallidos|que no salio|no salieron|errores|que fallo|rebotados)", "envio",
       "fallidos: lo que no salió hoy y por qué"),
    _o("canal", r"(?:canal|whatsapp|conexion|esta conectado|como esta el whatsapp|vinculado)", "envio",
       "canal: si el WhatsApp está conectado y si el envío está encendido"),
    _o("enciende", r"(?:ya\s+|vuelve a\s+)?(?:enciende|prende|activa|encender|prender|activar|reanuda|reanudar|suelta|libera|arranca)"
                   r"\s+(?:el\s+|la\s+|los\s+)?(?:envio|envios|cola|salida|mensajes)", "envio",
       "enciende el envío: sale lo que usted aprueba", QUIEN_APRUEBA, cambia=True),
    _o("pausa", r"(?:pausa|apaga|deten|detener|parar|pausar|frena|frenar|apagar)(?:\s+(?:el|la|los|todo))?"
                r"(?:\s+(?:envio|envios|cola|salida|mensajes|todo))?|para (?:el envio|los envios|la cola|todo)|(?:ya\s+)?no mandes nada", "envio",
       "pausa el envío: no sale nada", QUIEN_APRUEBA, cambia=True),
    _o("ritmo", r"(?:ritmo|horario de envio|cuantos al dia|tope|limite)", "envio",
       "ritmo: cada cuánto, a qué hora y cuántos al día"),
    _o("tope", r"(?:manda|envia|tope(?: de)?|limite(?: de)?|maximo)\s+(?:maximo\s+)?(?P<n>\d{1,3})(?:\s+(?:al|por)\s+dia)?",
       "envio", "máximo 50 al día: baja el tope de envíos (el techo es 100)", QUIEN_APRUEBA, cambia=True),
    # ------------------------------------------------------------ los precios
    _o("cotiza", r"(?:cotiza|cotizame|cotizacion|la cotizacion|una cotizacion|cuanto (?:es|sale|seria|cobro)|precio|dame precio|dame la cotizacion"
                 r"|cuanto le cobro|cuanto cobro)\s+(?:para\s+|de\s+|a\s+|por\s+)?(?P<personas>\d{1,3})(?:\s+(?:personas|pax|gente|huespedes|invitados))?"
                 r"(?P<resto>.*)", "precios",
       "cotiza 8 personas del 9 al 11 de noviembre: el número según su lista (para usted)"),
    _o("precios", r"(?:precios|(?:la\s+)?lista de precios|tarifas|la lista|lista|cuanto cobramos|nuestros precios"
                    r"|que precios tenemos|que precios hay)" + _PROP,
       "precios", "precios: la lista activa (precios quinta: solo la quinta)"),
    _o("perfil", r"(?:perfil|version|que version|la version|perfil activo)", "precios",
       "perfil: qué versión de la lista y de las respuestas está activa"),
    _o("propuestas", r"(?:propuestas|versiones|cambios pendientes|que hay por aprobar del perfil)", "precios",
       "propuestas: versiones del perfil que esperan su sí"),
    _o("aprueba_perfil", r"(?:aprueba|apruebo|activa|enciende)\s+(?:el\s+|la\s+)?(?:perfil|version|lista|precios)"
                         r"(?:\s+(?:version\s+)?v?(?P<n>\d{1,3}))?", "precios",
       "aprueba la versión 4: esa lista y esas respuestas quedan activas", QUIEN_APRUEBA, cambia=True),
    _o("faq", r"(?:faq|preguntas frecuentes|respuestas|respuestas guardadas|que contestas solo)", "precios",
       "faq: las respuestas guardadas que el agente cita"),
    _o("recuerda", r"(?:recuerda|aprende|nueva regla|regla nueva|toma en cuenta|para la proxima)\s+(?P<texto>.+)", "precios",
       "recuerda: la alberca se calienta con 24 h de aviso. Queda para la próxima versión, no se activa sola",
       cambia=True),
    _o("gasto", r"(?:gasto|cuanto llevamos|gasto de api|cuanto gastamos|consumo|costo)", "precios",
       "gasto: lo gastado este mes en inteligencia artificial y el tope"),
    # ----------------------------------------------------------- el calendario
    _o("disponible", r"(?:disponible|disponibilidad|libre|esta libre|hay lugar|tenemos libre|hay disponibilidad"
                     r"|esta ocupado|ocupado)" + _PROP + r"\s+(?P<resto>.*\d.*)", "calendario",
       "libre del 9 al 11 de noviembre: si las casas están libres esas noches"),
    _o("calendario", r"(?:(?:el\s+|la\s+|mi\s+)?(?:calendario|ocupacion|agenda)|reservas del mes|que esta ocupado"
                     r"|como esta (?:el calendario|la agenda))"
                     r"(?:\s+(?P<dias>\d{1,2})\s*dias)?", "calendario",
       "calendario: las noches ocupadas de los próximos 30 días"),
    _o("huecos", r"(?:huecos|fines libres|fines de semana libres|que fines tengo libres|dias muertos|que esta libre"
                 r"|fechas libres|que (?:fines|fechas|dias)(?: de semana)? (?:tengo|hay|estan|tenemos) (?:libres|disponibles)"
                 r"|(?:fines|fechas)(?: de semana)? disponibles)", "calendario", "huecos: los fines de semana libres de las próximas 8 semanas"),
    _o("aparta", r"(?:aparta|bloquea|ocupa|reserva|marca ocupad[oa])" + _PROP_CAL, "calendario",
       "aparta finca del 9 al 11 de noviembre: esas noches no se ofrecen", QUIEN_APRUEBA, cambia=True),
    _o("libera", r"(?:libera|desbloquea|desaparta|quita lo apartado)" + _PROP_CAL, "calendario",
       "libera finca del 9 al 11 de noviembre: quita lo que usted apartó", QUIEN_APRUEBA, cambia=True),
    _o("reservas", r"(?:(?:las\s+|mis\s+)?(?:reservas|rentas)(?:\s+del mes)?|ventas|cerrados|cuanto vendimos"
                   r"|cuanto se vendio|ventas del mes|que (?:rentas|reservas) tenemos|cuanto llevamos vendido"
                   r"|cuanto hemos vendido)", "calendario",
       "reservas: las rentas asentadas este mes (con cerró …1234)"),
    # ------------------------------------------------------ la mesa misma
    _o("bitacora", r"(?:bitacora|que ordene|ordenes de hoy|historial de ordenes|que he pedido)", "mesa",
       "bitácora: las últimas órdenes y quién las dio"),
    _o("administradoras", r"(?:administradoras|administradores|quien manda|quien puede|admins)", "mesa",
       "administradoras: quién puede escribirle a la mesa"),
    _o("agrega_admin", r"(?:agrega|alta|anade|suma)\s+(?:a\s+)?(?:la\s+|el\s+)?(?:administradora|administrador|admin)\s+"
                       r"(?P<tel>\+?\d[\d -]{8,16}\d)", "mesa",
       "agrega administradora 777 123 4567: también recibe reportes", QUIEN_APRUEBA, cambia=True),
    _o("quita_admin", r"(?:quita|baja|elimina|borra)\s+(?:a\s+)?(?:la\s+|el\s+)?(?:administradora|administrador|admin)\s+"
                      r"(?P<tel>\+?\d[\d -]{8,16}\d)", "mesa", "quita administradora 777 123 4567",
       QUIEN_APRUEBA, cambia=True),
    _o("silencia", r"(?:silencia|apaga|calla|ya no mandes|no mandes|pausa)\s+(?:los\s+|el\s+|mis\s+)?reportes?", "mesa",
       "silencia los reportes: ya no le llegan los de las 9 y las 19", cambia=True),
    _o("activa_reportes", r"(?:activa|prende|enciende|manda|reanuda)\s+(?:los\s+|el\s+|mis\s+)?reportes?", "mesa",
       "activa los reportes: vuelven los de las 9 y las 19", cambia=True),
    _o("deshaz", r"(?:deshaz|deshacer|deshazlo|revierte|revertir)(?:\s+eso|\s+lo ultimo)?", "mesa",
       "deshaz: revierte su última orden, si fue hace menos de 30 minutos",
       cambia=True),
)

POR_ID = {o.id: o for o in TABLA}
TEMAS = {"ayuda": "Cómo pedir", "tablero": "El día", "clientes": "Clientes", "rondas": "Rondas y borradores",
         "envio": "El envío", "precios": "Precios y perfil", "calendario": "Calendario y rentas",
         "mesa": "La mesa"}
_SINONIMOS_TEMA = {"cliente": "clientes", "platicas": "clientes", "ronda": "rondas", "borradores": "rondas",
                   "envios": "envio", "cola": "envio", "precio": "precios", "lista": "precios", "perfil": "precios",
                   "fechas": "calendario", "reservas": "calendario", "agenda": "calendario", "dia": "tablero",
                   "reporte": "tablero", "admin": "mesa", "administradoras": "mesa"}


# --------------------------------------------------------------------------- #
#  Normalizar lo que escribe una persona                                       #
# --------------------------------------------------------------------------- #
_FORMATO = re.compile(r"(?<!\w)[*_~]+|[*_~]+(?!\w)")
_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]")
_CORTESIA_INICIO = re.compile(
    r"^(?:(?:hola|oye|oiga|ola|buen(?:os|as)?(?: dias| tardes| noches)?|asistente|bot|mesa|porfa|por favor|plis|please"
    r"|me puedes|puedes|podrias|me podrias|quiero|quisiera|necesito|me das|dame|pasame|mandame|ensename|muestrame"
    r"|dime|a ver|haber|ver|ahora|y|ok|oka|va|bueno|oye asistente|me dices|me pasas|me mandas|me ensenas|que onda"
    r"|xfa|pls|plz|porfis|porfavor)\s+)+")
_CORTESIA_FIN = re.compile(r"(?:\s+(?:por favor|porfa|plis|please|gracias|muchas gracias|ya|ahorita|asistente"
                           r"|xfa|pls|plz|porfis|porfavor))+$")
#: *q* = que, *x* = por, *xq* = porque (WhatsApp).
_ABREV = ((re.compile(r"\bq\b"), "que"), (re.compile(r"\bxq\b"), "porque"), (re.compile(r"\bx\b"), "por"))


def normalizar(texto: str | None, cortesias: bool = True) -> str:
    """Minúsculas sin acentos, sin formato de WhatsApp, sin emojis, sin signos y sin cortesías.

    Se dejan los dígitos con sus espacios y guiones (un teléfono se escribe así) y
    los guiones de un nombre de ronda."""
    t = _FORMATO.sub("", texto or "")
    t = _EMOJI.sub(" ", t).strip().lstrip("/").strip()
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("…", " ").replace("...", " ").replace("$", " $ ")
    t = re.sub(r"[¿?¡!.,;:\"'()\[\]]", lambda m: " " if m.group() != "?" else " ? ", t)
    t = " ".join(t.split())
    for patron, por in _ABREV:
        t = patron.sub(por, t)
    if t.strip(" ?") == "":
        return "?" if "?" in t else ""
    t = t.replace(" ?", "").replace("?", "").strip()
    for _ in range(3):
        t2 = _CORTESIA_INICIO.sub("", t)
        t2 = (_CORTESIA_FIN.sub("", t2) if cortesias else t2).strip()
        if t2 == t:
            break
        t = t2
    # "$ 15 000" y "15,000" ya vienen sin coma; el "$" suelto no estorba.
    return " ".join(t.replace(" $ ", " ").replace("$", "").split())


# --------------------------------------------------------------------------- #
#  Erratas: la palabra se corrige contra el vocabulario de la tabla            #
# --------------------------------------------------------------------------- #
def _vocabulario() -> set[str]:
    palabras: set[str] = set()
    for o in TABLA:
        for trozo in re.findall(r"[a-z]{4,}", o.patron.pattern):
            palabras.add(trozo)
    return palabras


VOCABULARIO = frozenset(_vocabulario())
CORTE_ERRATA = 0.84


def _corregir(t: str) -> str:
    salida = []
    for w in t.split():
        if len(w) >= 5 and w not in VOCABULARIO and not w.isdigit():
            cerca = difflib.get_close_matches(w, VOCABULARIO, n=1, cutoff=CORTE_ERRATA)
            salida.append(cerca[0] if cerca else w)
        else:
            salida.append(w)
    return " ".join(salida)


# --------------------------------------------------------------------------- #
#  Leer                                                                        #
# --------------------------------------------------------------------------- #
def _limpiar_ref(ref: str | None) -> str:
    return re.sub(r"\D", "", ref or "")


def lista(texto: str | None) -> list[int] | str:
    t = (texto or "").strip()
    if t in ("todos", "todas", "todo"):
        return "todos"
    return [int(n) for n in re.findall(r"\d+", t)]


def _crudo(texto: str) -> str:
    """El texto con sus acentos y mayúsculas, sin formato: para lo que se le dice a un cliente."""
    return _EMOJI.sub("", _FORMATO.sub("", texto or "")).strip().lstrip("/").strip()


_PALABRA_LIBRE = re.compile(r"\b(?:recuerda|aprende|nueva regla|regla nueva|toma en cuenta|para la pr[oó]xima)\b[:,-]?\s*",
                            re.I)
#: *recuerda* enseña una regla solo con dos puntos: *"Recuerda que mañana voy"* es plática (adversarial).
_RECUERDA_CON_DOS_PUNTOS = re.compile(
    r"^\W*(?:recuerda|aprende|nueva regla|regla nueva|toma en cuenta|para la pr[oó]xima)\s*:", re.I)


def texto_propio(texto: str, ref: str | None) -> str:
    """Lo que viene después del cliente (o de *recuerda*), con los acentos y mayúsculas de quien lo escribió."""
    crudo = _crudo(texto)
    if ref:
        digitos = re.sub(r"\D", "", ref)
        m = re.search(r"\D{0,3}".join(digitos) + r"(?!\d)", crudo)  # "777.123.4567" también
        if not m:
            return ""
        resto = crudo[m.end():]
    else:
        m = _PALABRA_LIBRE.search(crudo)
        if not m:
            return ""
        resto = crudo[m.end():]
    return re.sub(r"^[\s:,.-]*(?:que\b)?[\s:,.…-]*", "", resto, flags=re.I).strip()


def _con_datos(o: Orden, m: re.Match, texto: str) -> dict:
    d = {"orden": o.id, **{re.sub(r"\d$", "", k): v for k, v in m.groupdict().items() if v}}
    if "ref" in d:
        d["ref"] = _limpiar_ref(d["ref"])
    if "lista" in d:
        d["lista"] = lista(d["lista"])
    if "tel" in d:
        d["tel"] = _limpiar_ref(d["tel"])
    for k in ("pagina", "n", "dias", "personas"):
        if k in d:
            d[k] = int(d[k])
    if "texto" in d and o.id in ("dile", "nota", "recuerda"):
        # Lo que se le dice al cliente, o lo que queda en la ficha, va con SUS palabras.
        if (propio := texto_propio(texto, m.group("ref") if "ref" in m.groupdict() else None)):
            d["texto"] = propio
    if "prop" in d:
        d["prop"] = {"las dos": "ambas", "las dos casas": "ambas"}.get(d["prop"], d["prop"])
    return d


def leer(texto: str | None) -> dict | None:
    """`{"orden": id, …datos}` o None. Con errata corregida: `"corregida": True`."""
    t = normalizar(texto)
    if not t:
        return None
    pregunta = "?" in (texto or "")
    if re.fullmatch(_REF, t):  # solo el cliente: "…1234", "777 123 4567"
        return {"orden": "ficha", "ref": _limpiar_ref(t)} if len(_limpiar_ref(t)) >= 4 else None
    for o in TABLA:
        if (m := o.patron.match(t)):
            if o.id == "recuerda" and not _RECUERDA_CON_DOS_PUNTOS.match(_crudo(texto or "")):
                return None
            if pregunta and o.cambia:
                # *"¿cerró el 4521?"* es una pregunta, no una orden: lo que cambia algo se confirma antes.
                return {**_con_datos(o, m, texto or ""), "corregida": True, "como": t, "pregunta": True}
            return _con_datos(o, m, texto or "")
    # *"dile a 4521 que gracias"*: el "gracias" del final era lo que se le dice, no una cortesía.
    entero = normalizar(texto, cortesias=False)
    if entero != t:
        for o in TABLA:
            if o.id in ("dile", "nota") and (m := o.patron.match(entero)):
                return _con_datos(o, m, texto or "")
    corregido = _corregir(t)
    if corregido != t:
        for o in TABLA:
            if (m := o.patron.match(corregido)):
                return {**_con_datos(o, m, texto or ""), "corregida": True, "como": corregido}
    return None


#: Palabras de los patrones que también son plática de todos los días: no bastan para suponer una orden.
_COMUNES = frozenset({"quien", "quienes", "donde", "cuanto", "cuantos", "tenemos", "puedes", "puede", "todos", "todas",
                      "mandes", "esta", "estas", "estamos", "hay", "llevo", "tomo", "quedo", "ahora", "proxima",
                      "cuenta", "dijo", "paso", "pago", "salio", "listo", "libre", "ocupado", "manda", "mandale",
                      "dile", "nota", "pausa", "para", "precio", "ronda", "rentaron", "rento", "cerro", "aparto"})


def parece_orden(texto: str | None) -> str | None:
    """Si no es orden pero se parece a una, la que quiso decir; si no, None.

    Solo con diagonal (*/pendints*) o con una o dos palabras casi iguales a una
    de la tabla (*"pendints"*): una plática normal con la dueña (*"mañana llega
    la familia"*) no recibe respuestas solas."""
    crudo = (texto or "").strip()
    palabras = [w for w in normalizar(crudo).split() if not w.isdigit()]
    if not palabras or (len(palabras) > 2 and not crudo.startswith("/")):
        return None
    for w in palabras:
        if len(w) < 5 or w in _COMUNES:
            continue
        cerca = difflib.get_close_matches(w, VOCABULARIO, n=1, cutoff=CORTE_ERRATA if not crudo.startswith("/") else 0.7)
        if cerca:
            # La orden donde esa palabra aparece primero en su patrón: "pendientes" es de pendientes,
            # no de oportunidades ("ventas pendientes").
            con_ella = [(o.patron.pattern.find(cerca[0]), i, o.id) for i, o in enumerate(TABLA)
                        if re.search(rf"\b{re.escape(cerca[0])}\b", o.patron.pattern)]
            if con_ella:
                return min(con_ella)[2]
    return None


def ayuda(tema: str | None = None) -> str:
    tema = _SINONIMOS_TEMA.get(tema or "", tema or "")
    if tema in TEMAS and tema != "ayuda":
        lineas = [f"{TEMAS[tema]}:"] + [f"· {o.ayuda}" for o in TABLA if o.tema == tema]
        return "\n".join(lineas) + "\nLo que cambia algo solo lo ordena quien aprueba."
    lineas = ["Puede escribirme (sin acentos, con o sin diagonal):"]
    for clave in ("tablero", "clientes", "rondas", "envio", "precios", "calendario", "mesa"):
        ejemplos = [o.ayuda.split(":")[0] for o in TABLA if o.tema == clave][:5]
        lineas.append(f"· {TEMAS[clave]}: " + ", ".join(ejemplos))
    lineas.append("Para ver más de un tema: ayuda clientes, ayuda rondas, ayuda precios, ayuda calendario, ayuda envio.")
    lineas.append("A un cliente lo nombra con sus últimos 4 dígitos (…1234) o con su número en la última lista.")
    return "\n".join(lineas)


def fechas_de(texto: str, hoy: date) -> tuple[date, date] | None:
    """Fechas como las escribe la dueña: *"del 9 al 11 de noviembre"*, *"9-11 nov"*,
    *"el 15 de nov 2 noches"*, *"15/11 al 17/11"*."""
    from . import lectura
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})(?:/(?:20)?(\d\d))?\b",
               lambda m: f"{m.group(1)} de {_MES_N[int(m.group(2))]}" + (f" de 20{m.group(3)}" if m.group(3) else "")
               if 1 <= int(m.group(2)) <= 12 else m.group(0), texto or "")
    return lectura.fechas_en(t, hoy)


_MES_N = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
          9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}


def monto_centavos(texto: str | None) -> int | None:
    """*"15000"*, *"15,000"*, *"15.000"*, *"15 mil"* → centavos. El dinero es entero."""
    t = (texto or "").strip().lower().replace(" ", "")
    if not t:
        return None
    mil = t.endswith("mil")
    t = t.removesuffix("mil")
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", t):
        centavos = int(re.sub(r"[.,]", "", t)) * 100
    elif re.fullmatch(r"\d+(?:[.,]\d{1,2})?", t):
        entero, _, dec = t.replace(",", ".").partition(".")
        centavos = int(entero) * 100 + int((dec + "00")[:2])
    else:
        return None
    return centavos * 1000 if mil else centavos
