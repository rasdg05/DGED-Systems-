"""El turno: un mensaje del cliente final entra, una `Salida` queda escrita.

Orden (del más barato y seguro al más caro):

1. Sin perfil aprobado, todo a la persona.
2. Respuesta guardada del negocio: sin modelo.
3. Borrador del modelo chico (el grande si el chico dice `dificil=si`).
4. Candados por código: cifra en el texto del modelo, voz ajena o duda → a
   la persona, con el borrador para que no empiece de cero.
5. Si pide cotizar con fechas y personas, la cifra la pone el cotizador y la
   salida queda **esperando aprobación** (invariante 2). Incompleta, sin total.

Una `Salida` no se envía aquí: la envía `canal.py`, que revisa el modo de
encendido y la aprobación. Todas quedan en `salidas.jsonl` para la sombra.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone

from . import (
    calendario,
    conversacion,
    cotizador,
    gasto,
    guardia,
    historial,
    jugadas,
    lectura,
    modelo,
    perfil,
    respuestas,
    voz,
)
from .espacio import Espacio
from .historial import Mensaje

ARCHIVO = "salidas.jsonl"
CONTEXTO_MENSAJES = 20
#: Si una persona del negocio escribió en estas horas, el agente calla (Gestor, `fuera_de_lugar`).
HORAS_DE_LA_PERSONA = 24
LO_CONFIRMO = "Permítame confirmarlo y le escribo en un momento."
#: Lo que la casa escribe cuando le piden precio sin decir cuántos son (Finca
#: Emiliano: *"Cuántas personas?"* 21 veces, *"Para cuántas personas?"* 7).
PIDE_PERSONAS = "Para cuántas personas?"
_FIN_DE_ANO = re.compile(r"\bfin de ano\b|\bano nuevo\b|\bnavidad\b|\bnochebuena\b")
#: Preguntas de precio que no son de hospedaje: el apartado, los eventos y lo que
#: se arma aparte. Las lleva una persona (o el extra de la lista, abajo).
_NO_ES_HOSPEDAJE = re.compile(r"\bapart\w*|\banticipo\b|\bdeposit\w*|\bevento\b|\bboda\b|\bxv\b|\bfiesta\b"
                              r"|\bpaquete\w*|\btodo incluido\b|\bbanquete\b|\balimentos\b|\bcomida\b"
                              r"|\btransporte\b|\bbautizo\b|\bcumple\w*|\bmesas?\b|\bsillas?\b|\bhoras?\b|\bhrs\b")
_ALBERCA = re.compile(r"\balberca\b|\bcalefacc\w*|\bclimatiz\w*|\bcaldera\b")
_NOMBRE = {"finca": "la finca", "quinta": "la quinta", "ambas": "las dos casas"}
_UNIDAD_EXTRA = {"dia": "el día", "persona": "por persona", "noche": "la noche"}


@dataclass
class Salida:
    cliente_id: str
    hilo: str
    responde_a: str
    via: str                   # guardada | regla | modelo | cotizador | persona | silencio
    texto: str                 # lo que recibiría el cliente final
    borrador: str = ""         # lo que redactó el modelo, si no salió
    motivo: str = ""
    cotizacion: dict | None = None
    requiere_aprobacion: bool = False
    aprobada_por: str | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    creada: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @property
    def a_persona(self) -> bool:
        return self.via == "persona"

    def a_dict(self) -> dict:
        return asdict(self)


def _conversacion(espacio: Espacio, entrante: Mensaje) -> list[dict]:
    hilo = [m for m in historial.hilos(espacio).get(entrante.hilo, []) if m.texto and m.ts <= entrante.ts]
    if not hilo or hilo[-1].id != entrante.id:
        hilo.append(entrante)
    salida: list[dict] = []
    for m in hilo[-CONTEXTO_MENSAJES:]:
        rol = "assistant" if m.del_negocio else "user"
        if salida and salida[-1]["role"] == rol:
            salida[-1]["content"] += "\n" + m.texto
        else:
            salida.append({"role": rol, "content": m.texto})
    while salida and salida[0]["role"] != "user":
        salida.pop(0)
    return salida


def _fecha(texto: str | None) -> date | None:
    try:
        return date.fromisoformat((texto or "").strip())
    except ValueError:
        return None


def _entero(texto: str | None) -> int | None:
    t = (texto or "").strip()
    return int(t) if t.isdigit() else None


def _a_persona(base: dict, motivo: str, borrador: str = "") -> Salida:
    return Salida(**base, via="persona", texto=LO_CONFIRMO, borrador=borrador, motivo=motivo)


def _callar(base: dict, motivo: str) -> Salida:
    return Salida(**base, via="silencio", texto="", motivo=motivo)


def lo_lleva_una_persona(hilo: list[Mensaje], entrante: Mensaje, fijas: set[str],
                         horas: float = HORAS_DE_LA_PERSONA) -> bool:
    """Una PERSONA del negocio escribió en las últimas `horas` horas de este hilo.

    Lo automático no cuenta (`jugadas.automaticas`): la bienvenida de WhatsApp
    Business llega como mensaje del negocio y, contada como persona, callaba al
    agente 24 h justo cuando el cliente acababa de llegar (339 de 1,003 momentos
    de Finca Emiliano, medido 2026-10-27)."""
    auto = jugadas.automaticas(hilo, fijas)
    return any(m.del_negocio and m.id not in auto and m.id != entrante.id and 0 <= entrante.ts - m.ts <= horas * 3600
               for m in hilo)


def _lo_lleva_una_persona(espacio: Espacio, entrante: Mensaje) -> bool:
    horas = float(espacio.config().get("horas_de_la_persona", HORAS_DE_LA_PERSONA))
    hilos = historial.hilos(espacio)
    hilo = [m for m in hilos.get(entrante.hilo, []) if m.ts <= entrante.ts]
    return lo_lleva_una_persona(hilo, entrante, jugadas.plantillas(hilos), horas)


def antes_del_modelo(base: dict, entrante: Mensaje, hilo: list[Mensaje], activo: dict | None,
                     ocupacion: calendario.Ocupacion | None = None) -> Salida | None:
    """Todo lo que el turno decide sin modelo, en orden. `None`: iría al modelo.

    Es la parte que la vara (`vara.py`) corre sobre cada momento real: el mismo
    código del turno, sin llamar a nada. `hilo` es lo que el agente vería (lo
    anterior al mensaje, que lo incluye); no lee el reloj de pared. `ocupacion`:
    el calendario, si el espacio tiene uno (la vara no lo pasa: no hay calendario
    del pasado)."""
    if activo is None:
        return _a_persona(base, "sin perfil aprobado")
    if not conversacion.tiene_turno(entrante.texto):
        # `otro` no es un medio: es un aviso de protocolo de WhatsApp (reacción,
        # edición, llaves). Pegado a un texto del cliente, se contesta ese texto (710
        # de Finca Emiliano, 475 justo tras un texto suyo). Solo, va a una persona:
        # callarlo costó 7 errores caros en la vara (la bienvenida automática corta
        # la ráfaga y lo que el cliente preguntó antes queda sin leer).
        if entrante.tipo != "otro" or not conversacion.rafaga(hilo):
            return _a_persona(base, "mensaje sin texto (foto, audio o documento)")
    # Lo que Gestor aprendió con clientes reales, antes de gastar un token
    # (`conversacion.py`): la ráfaga se lee junta y hay cosas que no se contestan.
    dicho = conversacion.rafaga(hilo) or entrante.texto
    if conversacion.es_reclamo(dicho):
        return _a_persona(base, "reclamo o molestia: lo atiende una persona")
    if conversacion.intenta_cambiar_las_reglas(dicho):
        return _a_persona(base, "el mensaje le da órdenes al asistente: lo ve una persona")
    if conversacion.pregunta_si_es_bot(dicho):
        nombre = activo.get("nombre_comercial") or "este negocio"
        return Salida(**base, via="regla", texto=(f"Soy el asistente automático de {nombre}. "
                                                  "Si prefiere, una persona le contesta por aquí."))
    if conversacion.pide_persona(dicho):
        return _a_persona(base, "pidió hablar con una persona")
    if conversacion.es_cierre(dicho):
        return _callar(base, "el cliente cerró la conversación")
    if conversacion.es_contestador(dicho):
        return _callar(base, "contestó otra máquina")
    if conversacion.nada_que_contestar(dicho, con_si=False):
        return _callar(base, "acuse: no pide nada")
    guardada = respuestas.buscar(activo, dicho)
    if guardada:
        return Salida(**base, via="guardada", texto=guardada["respuesta"])
    return por_grupo(base, hilo, dicho, activo, ocupacion)


def por_grupo(base: dict, hilo: list[Mensaje], dicho: str, activo: dict,
              ocupacion: calendario.Ocupacion | None = None) -> Salida | None:
    """La cotización por grupo, sin modelo, con la lista de precios del perfil.

    Entra si el cliente pide precio o da su grupo o sus fechas. Sin cuántos son,
    los pregunta (como la casa). Con el grupo, el cotizador elige la propiedad por
    el tamaño y, con fechas, da el total; sin fechas, el precio de la lista. La
    cifra siempre espera el sí de una persona (invariante XXXIII); incompleta, va
    a la persona con la cotización como borrador.

    Con calendario y fechas, una propiedad ocupada no se cotiza (invariante LXII);
    si todas lo están, va a una persona con el aviso como borrador. Lo que el
    calendario no sabe viaja en la cotización para quien la aprueba."""
    from .lista_precios import propiedad_en_platica

    if not any(r.get("tipo") == "grupo" for r in activo.get("reglas", []) or []):
        return None
    t = conversacion.normalizar(dicho)
    propiedad = propiedad_en_platica(hilo)
    if _ALBERCA.search(t) and (lectura.pide_precio(dicho) or "?" in dicho):
        r = cotizador.extra(activo, "alberca", propiedad)
        if r is None:
            return None
        cuanto = f"{cotizador.pesos(r['monto_centavos'])} {_UNIDAD_EXTRA.get(r.get('unidad') or '', '')}".strip()
        return Salida(**base, via="cotizador", texto=f"La alberca climatizada tiene un costo de {cuanto}.",
                      cotizacion={"modo": "extra", "concepto": "alberca", "propiedad": r["propiedad"],
                                  "monto_centavos": r["monto_centavos"], "unidad": r.get("unidad")},
                      requiere_aprobacion=True)
    if _NO_ES_HOSPEDAJE.search(t) or lectura.pide_por_cuarto(dicho):
        return None
    # Dar grupo o fechas porque el negocio los pidió NO dispara: la casa contesta
    # eso con fotos y presentación, no con precio (grupo-3 en la bitácora: 0.289).
    if not (lectura.pide_precio(dicho) or _da_lo_que_faltaba(hilo, dicho)):
        return None
    personas = lectura.personas(hilo)
    if personas is None:
        return Salida(**base, via="cotizador", texto=PIDE_PERSONAS, motivo="cotizar por grupo: faltan las personas") \
            if lectura.pide_precio(dicho) else None
    fechas = lectura.fechas(hilo)
    temporada = None
    if fechas is None and any(_FIN_DE_ANO.search(conversacion.normalizar(m.texto or ""))
                              for m in hilo if not m.del_negocio):
        temporada = next((t["nombre"] for t in activo.get("temporadas", []) or [] if t.get("fin_de_ano")), None)
    cot = cotizador.cotizar_grupo(activo, personas, *(fechas or (None, None)), temporada=temporada,
                                  propiedad=propiedad, noches=lectura.noches(hilo))
    if not cot.completa:
        return Salida(**base, via="persona", texto=LO_CONFIRMO, borrador=cot.texto(),
                      motivo="cotización incompleta: " + "; ".join(cot.faltan), cotizacion=cot.a_dict())
    disponibilidad = None
    if ocupacion is not None and ocupacion.configurada and cot.llegada and cot.salida:
        disponibilidad = {o.propiedad: ocupacion.disponibilidad(o.propiedad, cot.llegada, cot.salida)
                          for o in cot.opciones}
        libres = [o for o in cot.opciones if disponibilidad[o.propiedad].estado != calendario.OCUPADA]
        if not libres:
            nombres = " ni ".join(_NOMBRE.get(p, p) for p in disponibilidad)
            return Salida(**base, via="persona", texto=LO_CONFIRMO,
                          borrador=f"Para esas fechas ya no tenemos disponible {nombres}.",
                          motivo="fechas ocupadas en el calendario",
                          cotizacion={**cot.a_dict(), "disponibilidad": [d.a_dict() for d in disponibilidad.values()]})
        cot.opciones = libres
    datos = cot.a_dict()
    if disponibilidad is not None:
        datos["disponibilidad"] = [disponibilidad[o.propiedad].a_dict() for o in cot.opciones]
    return Salida(**base, via="cotizador", texto=cot.texto(), cotizacion=datos, requiere_aprobacion=True)


def _da_lo_que_faltaba(hilo: list[Mensaje], dicho: str) -> bool:
    """El cliente da su grupo o sus fechas después de haber pedido precio sin
    recibirlo (*"¿Costo?"* → *"Cuántas personas?"* → *"20"*)."""
    hoy = lectura.hoy_de(hilo[-1]) if hilo else None
    if not (lectura.personas_en(dicho) is not None or lectura.personas(hilo) != lectura.personas(hilo[:-1])
            or (hoy and lectura.fechas_en(dicho, hoy) is not None)):
        return False
    for m in reversed(hilo[:-1]):
        if m.del_negocio and m.texto and jugadas.es_monto(m.texto):
            return False
        if not m.del_negocio and lectura.pide_precio(m.texto):
            return True
    return False


def candados(base: dict, texto: str, meta: dict, activo: dict) -> Salida | None:
    """Lo que detiene un borrador (del modelo o del enjambre) antes de salir: va a
    la persona con el borrador. `None`: pasa. La vara usa esta misma función."""
    if (cifras := guardia.cifras_no_permitidas(texto)):
        return _a_persona(base, f"cifra que no puso el cotizador: {cifras}", texto)
    if guardia.dice_ser_persona(texto):
        return _a_persona(base, "el borrador dice ser una persona", texto)
    if (rasgos := voz.hallazgos(texto, activo)):
        return _a_persona(base, "voz ajena: " + "; ".join(rasgos), texto)
    if meta.get("persona") == "si" or not texto:
        return _a_persona(base, meta.get("duda") or "el modelo pidió a la persona", texto)
    return None


def decidir(espacio: Espacio, entrante: Mensaje, client=None, en_vivo: bool = False) -> Salida:
    """`en_vivo=True` solo en el turno real: ahí el agente no habla encima de una
    persona. La sombra redacta igual para poder medir (Gestor: `fiel`)."""
    base = {"cliente_id": espacio.cliente_id, "hilo": entrante.hilo, "responde_a": entrante.id}
    activo = perfil.activo(espacio)
    hilo = [m for m in historial.hilos(espacio).get(entrante.hilo, []) if m.ts <= entrante.ts]
    if not hilo or hilo[-1].id != entrante.id:
        hilo.append(entrante)
    if activo is not None and conversacion.tiene_turno(entrante.texto) and en_vivo \
            and _lo_lleva_una_persona(espacio, entrante):
        return _callar(base, "lo lleva una persona: el agente no habla encima")
    ocupacion = calendario.Ocupacion.de(espacio)
    sin_modelo = antes_del_modelo(base, entrante, hilo, activo, ocupacion if ocupacion.configurada else None)
    if sin_modelo is not None:
        return sin_modelo

    charla = _conversacion(espacio, entrante)
    try:
        texto, meta = modelo.turno(espacio, activo, charla, client=client)
        if meta.get("dificil") == "si" and gasto.puede_gastar(espacio):
            texto, meta = modelo.turno(espacio, activo, charla, client=client, modelo=modelo.MODELO_GRANDE)
    except (modelo.Dormido, gasto.TopeAlcanzado, modelo.LlamadaFallida) as error:
        return _a_persona(base, str(error) or type(error).__name__)

    if (detenida := candados(base, texto, meta, activo)) is not None:
        return detenida

    llegada, salida_ = _fecha(meta.get("llegada")), _fecha(meta.get("salida"))
    personas, propiedad = _entero(meta.get("personas")), (meta.get("propiedad") or "").strip()
    if meta.get("cotizar") == "si" and personas and not propiedad \
            and any(r.get("tipo") == "grupo" for r in activo.get("reglas", []) or []):
        cot = cotizador.cotizar_grupo(activo, personas, llegada, salida_) if llegada and salida_ \
            else cotizador.cotizar_grupo(activo, personas)
        if not cot.completa:
            return Salida(**base, via="persona", texto=LO_CONFIRMO, borrador=texto,
                          motivo="cotización incompleta: " + "; ".join(cot.faltan), cotizacion=cot.a_dict())
        return Salida(**base, via="cotizador", texto=f"{texto}\n\n{cot.texto()}", borrador=texto,
                      cotizacion=cot.a_dict(), requiere_aprobacion=True)
    if meta.get("cotizar") == "si" and llegada and salida_ and personas and propiedad:
        cot = cotizador.cotizar(activo, propiedad, llegada, salida_, personas, meta.get("evento") == "si")
        if not cot.completa:
            return Salida(**base, via="persona", texto=LO_CONFIRMO, borrador=texto,
                          motivo="cotización incompleta: " + "; ".join(cot.faltan), cotizacion=cot.a_dict())
        return Salida(**base, via="cotizador", texto=f"{texto}\n\n{cot.texto()}", borrador=texto,
                      cotizacion=cot.a_dict(), requiere_aprobacion=True)
    return Salida(**base, via="modelo", texto=texto)


def atender(espacio: Espacio, entrante: Mensaje, client=None) -> Salida:
    historial.guardar(espacio, [entrante])
    salida = decidir(espacio, entrante, client=client, en_vivo=True)
    espacio.agregar_linea(ARCHIVO, salida.a_dict())
    return salida


def salidas(espacio: Espacio) -> list[Salida]:
    """Las salidas con su aprobación al día: la aprobación vive aparte
    (`aprobaciones_salida.jsonl`) y sin juntarla aquí, una ronda aprobada seguía
    contando como "espera su sí" en la Cola y en el reporte (2026-10-27)."""
    ya = aprobadas(espacio)
    lista = [Salida(**d) for d in espacio.leer_lineas(ARCHIVO)]
    for s in lista:
        if s.aprobada_por is None and s.id in ya:
            s.aprobada_por = ya[s.id]
    return lista


def aprobar_salida(espacio: Espacio, salida_id: str, aprobador: str) -> Salida:
    """Una persona del negocio aprueba una cotización. Queda escrito quién."""
    alta = espacio.leer_json("alta.json", {}) or {}
    autorizados = {a.strip().casefold() for a in [alta.get("aprobador", "")] + list(alta.get("asesores", []) or []) if a}
    if aprobador.strip().casefold() not in autorizados:
        raise perfil.AprobacionInvalida("solo aprueban las personas que el alta registra")
    for s in salidas(espacio):
        if s.id == salida_id:
            s.aprobada_por = aprobador
            espacio.agregar_linea("aprobaciones_salida.jsonl", {"id": salida_id, "aprobador": aprobador,
                                                                "en": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            return s
    raise KeyError(salida_id)


def aprobadas(espacio: Espacio) -> dict[str, str]:
    return {r["id"]: r["aprobador"] for r in espacio.leer_lineas("aprobaciones_salida.jsonl")}
