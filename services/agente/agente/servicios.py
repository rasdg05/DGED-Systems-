"""El giro de servicios por sesión (clínica estética, spa): qué tratamiento pide y cuánto cuesta.

El cotizador de renta (`cotizador.py`) cobra noches y grupos; una clínica cobra
tratamientos. Las reglas son renglones del perfil aprobado, cada uno con su
origen (`perfil.py`), igual que las de la finca:

- `servicio`: `propiedad` (la categoría: faciales, inyectables, láser),
  `servicio` (clave), `nombre`, `unidad` (`sesion` | `zona` | `paquete`),
  `monto_centavos`, `alias` (cómo lo dice la clienta) y, en un paquete,
  `sesiones` o `zonas`.
- `valoracion`: `monto_centavos`; `abona=True` si se descuenta del tratamiento.
- `anticipo_cita`: `monto_centavos` con que se aparta la cita.

Dos reglas que no se negocian:

- **Una pregunta de salud la contesta la especialista** (`pregunta_de_salud`):
  embarazo, lactancia, medicamentos, alergias, una reacción después de un
  tratamiento. Ningún texto automático le dice a nadie si puede o no aplicarse
  algo; va a una persona, sin borrador del modelo.
- **La cifra la pone el código y espera el sí de una persona** (invariante
  XXXIII). Dos reglas del mismo servicio y unidad con montos distintos no se
  promedian: la cotización sale incompleta, sin total.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .conversacion import normalizar
from .cotizador import pesos

UNIDADES = {"sesion": "por sesión", "zona": "por zona"}

#: Lo que pide criterio médico. Ancho a propósito: un falso positivo cuesta que
#: una persona conteste; un falso negativo, que una máquina dé un consejo de salud.
_SALUD = re.compile(
    r"\bembaraz\w*|\blactan\w*|\bamamant\w*|\bdando pecho\b|\bdiabet\w*|\bhipertens\w*|\bpresion alta\b"
    r"|\banticoagul\w*|\bmedicament\w*|\bmedicina\b|\bpastillas?\b|\btomo\b.{0,25}\b(?:pastilla|medic|trata)\w*"
    r"|\bisotretinoin\w*|\broaccutan\w*|\bantibiotic\w*|\balergi\w*|\balergic\w*|\bqueloide\w*|\bherpes\b"
    r"|\bcancer\b|\bquimio\w*|\btiroide\w*|\bcontraindic\w*|\befectos? secundari\w*|\bes peligroso\b|\bes seguro\b"
    r"|\bme puedo (?:aplicar|hacer|poner)\b|\bpuedo (?:aplicarme|hacerme|ponerme)\b"
    r"|\bme (?:quedo|salio|salieron|arde|duele|pica)\b|\bmoreton\w*|\bhinch\w*|\binflam\w*|\bronchas?\b"
    r"|\bampollas?\b|\bmanchas? despues\b|\bparpado caido\b|\bse me cayo\b")

_AGENDAR = re.compile(r"\bagend\w*|\bcita\b|\bapart\w*\s+(?:una |mi |la )?(?:cita|lugar|espacio)|\bdisponibilidad\b"
                      r"|\btiene(?:n)? (?:espacio|lugar|horario)\b")


def pregunta_de_salud(texto: str | None) -> bool:
    return bool(_SALUD.search(normalizar(texto or "")))


def quiere_agendar(texto: str | None) -> bool:
    return bool(_AGENDAR.search(normalizar(texto or "")))


def reglas_de(perfil: dict | None, tipo: str = "servicio") -> list[dict]:
    return [r for r in (perfil or {}).get("reglas", []) or [] if r.get("tipo") == tipo]


def es_giro_de_servicios(perfil: dict | None) -> bool:
    return bool(reglas_de(perfil))


def servicios_en(perfil: dict | None, texto: str | None) -> list[str]:
    """Las claves de los servicios que nombra el texto, en el orden del perfil.

    Gana el alias más largo: *"limpieza facial"* no es también *"facial"* de otro
    servicio, y *"piernas completas"* no es solo *"piernas"*."""
    t = normalizar(texto or "")
    hallados: list[tuple[int, int, str]] = []  # (inicio, fin, clave)
    for r in reglas_de(perfil):
        for alias in r.get("alias", []) or [r.get("nombre", "")]:
            if (a := normalizar(alias)):
                hallados += [(m.start(), m.end(), r["servicio"]) for m in re.finditer(rf"\b{re.escape(a)}\b", t)]
    # un alias dentro de otro más largo (y de otro servicio) no cuenta aparte
    vivos = {clave for i, f, clave in hallados
             if not any(i2 <= i and f <= f2 and (f2 - i2) > (f - i) and c2 != clave for i2, f2, c2 in hallados)}
    return [c for c in dict.fromkeys(r["servicio"] for r in reglas_de(perfil)) if c in vivos]


def servicio_en_platica(perfil: dict | None, textos: list[str]) -> list[str]:
    """Lo último que la clienta nombró en la plática (de lo más nuevo a lo más viejo)."""
    for texto in reversed(textos):
        if claves := servicios_en(perfil, texto):
            return claves
    return []


@dataclass
class CotizacionServicio:
    servicios: list[str]
    renglones: list[tuple[str, int]] = field(default_factory=list)  # (qué, centavos)
    notas: list[str] = field(default_factory=list)
    faltan: list[str] = field(default_factory=list)

    @property
    def completa(self) -> bool:
        return bool(self.renglones) and not self.faltan

    def texto(self) -> str:
        """Escrito por código. Lo que falta no lleva cifra."""
        if not self.completa:
            return "Falta confirmar " + "; ".join(self.faltan or ["el precio"]) + "."
        return "\n".join([f"{que}: {pesos(monto)}." for que, monto in self.renglones] + self.notas)

    def a_dict(self) -> dict:
        return {"modo": "servicio", "servicios": self.servicios, "renglones": self.renglones,
                "notas": self.notas, "faltan": self.faltan, "completa": self.completa, "texto": self.texto()}


def _uno(reglas: list[dict]) -> dict | None:
    """La regla si todas las candidatas dicen el mismo monto; si chocan, None."""
    montos = {r.get("monto_centavos") for r in reglas}
    return reglas[0] if len(montos) == 1 and None not in montos else None


def cotizar(perfil: dict, claves: list[str]) -> CotizacionServicio:
    c = CotizacionServicio(servicios=list(claves))
    if not claves:
        c.faltan.append("qué tratamiento le interesa")
        return c
    con_valoracion = False
    for clave in claves:
        suyas = [r for r in reglas_de(perfil) if r.get("servicio") == clave]
        if not suyas:
            c.faltan.append(f"el precio de {clave.replace('_', ' ')}")
            continue
        nombre = suyas[0].get("nombre") or clave
        for unidad in ("sesion", "zona"):
            if not (de_unidad := [r for r in suyas if r.get("unidad") == unidad]):
                continue
            if (r := _uno(de_unidad)) is None:
                c.faltan.append(f"el precio de {nombre} {UNIDADES[unidad]} (dos precios distintos)")
            else:
                c.renglones.append((f"{nombre} {UNIDADES[unidad]}", int(r["monto_centavos"])))
        paquetes: dict[tuple, list[dict]] = {}
        for r in suyas:
            if r.get("unidad") == "paquete":
                paquetes.setdefault((r.get("sesiones"), r.get("zonas")), []).append(r)
        for (sesiones, zonas), grupo in sorted(paquetes.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1] or 0)):
            que = (f"{nombre}, paquete de {sesiones} sesiones" if sesiones
                   else f"{nombre}, {zonas} zonas" if zonas else f"{nombre}, paquete")
            if (r := _uno(grupo)) is None:
                c.faltan.append(f"el precio de {que} (dos precios distintos)")
            else:
                c.renglones.append((que, int(r["monto_centavos"])))
        if any(r.get("propiedad") in {v.get("propiedad") for v in reglas_de(perfil, "valoracion")} for r in suyas):
            con_valoracion = True
    if con_valoracion and (v := _uno(reglas_de(perfil, "valoracion"))):
        c.notas.append(f"Antes del tratamiento se hace una valoración con la especialista ({pesos(v['monto_centavos'])}"
                       + (", se abona a su tratamiento)." if v.get("abona") else ")."))
    if (a := _uno(reglas_de(perfil, "anticipo_cita"))):
        c.notas.append(f"Su cita se aparta con un anticipo de {pesos(a['monto_centavos'])}.")
    return c
