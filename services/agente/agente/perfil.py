"""El perfil del negocio: contrato JSON por cliente, con versiones y origen por dato.

Como la ontología de Atlas (D-004): un contrato de datos, no texto para el
modelo. Cada renglón (dato, temporada, frase de voz, regla de cotización,
pregunta frecuente, caso que se escala) trae su `origen`, y `validar` descarta
lo que no lo tenga o no lo pueda probar:

- `{"tipo": "mensaje", "id": <wamid>, "cita": <texto>}`: el mensaje existe en el
  historial de ESTE espacio y la cita está literal en su texto. Lo que establece
  algo del negocio (dato, regla, voz, respuesta) tiene que venir de un mensaje
  del negocio, no del cliente final.
- `{"tipo": "alta", "campo": <campo>, "cita": <texto>}`: la cita está en lo que
  el dueño escribió en el alta.
- `{"tipo": "documento", "nombre": <archivo>, "cita": <texto>}`: la cita está en
  la transcripción de un documento suyo (`documentos/<nombre>`).

Si el renglón trae una cifra (monto, porcentaje, noches, personas), la cifra
tiene que aparecer en la cita: una cita real con un monto inventado no pasa.

Versiones (invariante 6): una versión se escribe una vez y no se reescribe.
`proponer` crea la siguiente sin tocar la activa; solo `aprobar`, con el nombre
de quien aprueba registrado en el alta, la enciende. La anterior se conserva.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

from . import historial
from .espacio import Espacio

CONTRATO = "agente-perfil-0.1"
SECCIONES = ("datos", "temporadas", "voz", "reglas", "faq", "escala")
# Secciones cuyo origen puede ser un mensaje del cliente final.
ORIGEN_CLIENTE_PERMITIDO = {"escala"}
CAMPOS_NUMERICOS = ("monto_centavos", "pct", "noches", "personas")


class VersionInmutable(RuntimeError):
    pass


class AprobacionInvalida(PermissionError):
    pass


def _normal(texto: str | None) -> str:
    sin = unicodedata.normalize("NFKC", texto or "")
    return " ".join(sin.casefold().split())


def numeros(texto: str | None) -> set[str]:
    """Las cifras de un texto, sin separadores de miles: "$3,500.00" -> {"3500"}.

    En México se escribe de las dos formas: *"12.000"* (punto de miles) y
    *"$600,00"* (coma decimal). Un separador seguido de dos cifras (o una) al
    final es decimal; seguido de grupos de tres, es de miles (enjambre,
    2026-10-27: *"12.000"* se leía 12 y *"600,00"*, 60000)."""
    salida = set()
    for crudo in re.findall(r"\d[\d,.]*", texto or ""):
        grupos = re.split(r"[,.]", crudo.rstrip(".,"))
        dec = ""
        if len(grupos) > 1 and len(grupos[-1]) in (1, 2):
            dec = grupos.pop()
        if len(grupos) > 1 and not all(len(g) == 3 for g in grupos[1:]):
            # "1.5.2", "10.15": no es un monto bien escrito; se queda cada pedazo
            salida.update(g.lstrip("0") or "0" for g in grupos + ([dec] if dec else []))
            continue
        entero = "".join(grupos).lstrip("0") or "0"
        if dec and set(dec) == {"0"}:
            dec = ""
        salida.add(entero)
        if dec:
            salida.add(f"{entero}.{dec}")
    return salida


def _cifras_del_renglon(renglon: dict) -> set[str]:
    cifras = set()
    for campo in CAMPOS_NUMERICOS:
        valor = renglon.get(campo)
        if isinstance(valor, bool) or valor is None:
            continue
        if campo == "monto_centavos" and isinstance(valor, int):
            pesos, cent = divmod(valor, 100)
            cifras.add(str(pesos) if cent == 0 else f"{pesos}.{cent:02d}")
        elif isinstance(valor, (int, float)):
            cifras.add(str(int(valor)) if float(valor).is_integer() else str(valor))
    valor = renglon.get("valor")
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        cifras.add(str(int(valor)) if float(valor).is_integer() else str(valor))
    return cifras


def _texto_de_origen(espacio: Espacio, origen: dict, mensajes: dict, seccion: str) -> tuple[str | None, str]:
    tipo = origen.get("tipo")
    if tipo == "mensaje":
        m = mensajes.get(origen.get("id"))
        if m is None:
            return None, "el mensaje no existe en el historial de este cliente"
        if not m.del_negocio and seccion not in ORIGEN_CLIENTE_PERMITIDO:
            return None, "el mensaje es del cliente final, no del negocio"
        return m.texto, ""
    if tipo == "alta":
        alta = espacio.leer_json("alta.json", {}) or {}
        valor = alta.get(origen.get("campo", ""))
        return (str(valor) if valor is not None else None), "campo del alta vacío"
    if tipo == "documento":
        nombre = str(origen.get("nombre", ""))
        try:
            ruta = espacio.ruta(f"documentos/{nombre}")
        except ValueError:
            return None, "documento fuera del espacio"
        if not nombre or not ruta.exists():
            return None, "el documento no existe en el espacio"
        return ruta.read_text(encoding="utf-8"), ""
    return None, "origen sin tipo conocido"


def motivo_de_rechazo(espacio: Espacio, seccion: str, renglon: dict, mensajes: dict) -> str:
    """'' si el renglón prueba su origen; si no, por qué no entra."""
    origen = renglon.get("origen")
    if not isinstance(origen, dict):
        return "sin origen"
    cita = origen.get("cita") or ""
    if not cita.strip():
        return "origen sin cita"
    texto, por_que = _texto_de_origen(espacio, origen, mensajes, seccion)
    if texto is None:
        return por_que
    if _normal(cita) not in _normal(texto):
        return "la cita no está literal en su origen"
    faltan = _cifras_del_renglon(renglon) - numeros(cita)
    if faltan:
        return f"cifra que no está en la cita: {sorted(faltan)}"
    return ""


def validar(espacio: Espacio, perfil: dict) -> tuple[dict, list[dict]]:
    """Devuelve (perfil con solo lo que prueba su origen, descartados con motivo)."""
    mensajes = historial.por_id(espacio)
    limpio = {k: v for k, v in perfil.items() if k not in SECCIONES}
    limpio["contrato"] = CONTRATO
    limpio["cliente_id"] = espacio.cliente_id
    descartados = []
    for seccion in SECCIONES:
        limpio[seccion] = []
        for renglon in perfil.get(seccion, []) or []:
            motivo = motivo_de_rechazo(espacio, seccion, renglon, mensajes)
            if motivo:
                descartados.append({"seccion": seccion, "renglon": renglon, "motivo": motivo})
            else:
                limpio[seccion].append(renglon)
    return limpio, descartados


# --------------------------------------------------------------------------- #
#  Versiones                                                                   #
# --------------------------------------------------------------------------- #
def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _nombre_version(n: int) -> str:
    return f"perfil/v{n:04d}.json"


def versiones(espacio: Espacio) -> list[int]:
    carpeta = espacio.ruta("perfil")
    if not carpeta.exists():
        return []
    return sorted(int(p.stem[1:]) for p in carpeta.glob("v*.json"))


def leer_version(espacio: Espacio, n: int) -> dict | None:
    return espacio.leer_json(_nombre_version(n))


def version_activa(espacio: Espacio) -> int | None:
    puntero = espacio.leer_json("perfil/activa.json")
    return puntero["version"] if puntero else None


def activo(espacio: Espacio) -> dict | None:
    n = version_activa(espacio)
    return leer_version(espacio, n)["perfil"] if n else None


def proponer(espacio: Espacio, perfil: dict, *, autor: str, nombre: str) -> tuple[int, list[dict]]:
    """Escribe una versión nueva en estado propuesta. No cambia la activa."""
    if not nombre.strip():
        raise ValueError("una versión lleva nombre")
    limpio, descartados = validar(espacio, perfil)
    n = (max(versiones(espacio)) if versiones(espacio) else 0) + 1
    ruta = espacio.ruta(_nombre_version(n))
    if ruta.exists():
        raise VersionInmutable(f"la versión {n} ya existe")
    espacio.escribir_json(_nombre_version(n), {
        "version": n, "nombre": nombre, "autor": autor, "creada": _ahora(),
        "base": version_activa(espacio), "perfil": limpio, "descartados": descartados,
    })
    return n, descartados


def aprobar(espacio: Espacio, n: int, *, aprobador: str) -> None:
    """La enciende el dueño del negocio, el que quedó escrito en el alta."""
    alta = espacio.leer_json("alta.json", {}) or {}
    quien = (alta.get("aprobador") or "").strip()
    if not quien or _normal(quien) != _normal(aprobador):
        raise AprobacionInvalida("solo aprueba quien el alta dice que aprueba")
    if leer_version(espacio, n) is None:
        raise ValueError(f"no existe la versión {n}")
    espacio.agregar_linea("perfil/aprobaciones.jsonl",
                          {"version": n, "aprobador": aprobador, "en": _ahora(),
                           "anterior": version_activa(espacio)})
    espacio.escribir_json("perfil/activa.json", {"version": n})
