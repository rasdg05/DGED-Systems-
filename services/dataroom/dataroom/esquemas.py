"""El esquema fijo de cada tipo de documento.

Cada campo tiene una CLASE que decide cómo se verifica contra su cita:

- ``texto``: resumen corto de lo que dice la cita (la cita sí es literal).
- ``transcripcion``: el valor mismo tiene que estar dentro de la cita. Todo lo
  que el código CRUZA (nombres, naves) y todo lo de un oficio de suministro es
  transcripción: lo que se compara no puede ser una paráfrasis del modelo.
- ``numero``: la cifra tiene que aparecer en la cita.
- ``fecha``: AAAA-MM-DD, y esa fecha tiene que leerse en la cita.

No existe, en ningún tipo, un campo de capacidad eléctrica, carga o MW (D-003).
Lo que diga un oficio sobre eso viaja como transcripción "según el oficio".
"""
from __future__ import annotations

from dataclasses import dataclass, field

TEXTO, TRANSCRIPCION, NUMERO, FECHA = "texto", "transcripcion", "numero", "fecha"


@dataclass(frozen=True)
class Campo:
    nombre: str
    clase: str
    descripcion: str


@dataclass(frozen=True)
class Tipo:
    nombre: str
    descripcion: str
    campos: tuple[Campo, ...] = field(default_factory=tuple)
    renglones: tuple[Campo, ...] = field(default_factory=tuple)
    descripcion_renglon: str = ""


def _c(nombre, clase, descripcion):
    return Campo(nombre, clase, descripcion)


NAVE = _c("identificador_nave", TRANSCRIPCION, "Identificador de la nave o unidad tal como lo escribe el documento, p. ej. 'Nave 2'.")

TIPOS: dict[str, Tipo] = {
    "contrato_renta": Tipo(
        "contrato_renta",
        "Contrato de arrendamiento de una nave o local industrial.",
        campos=(
            _c("inquilino", TRANSCRIPCION, "Razón social del arrendatario, como aparece en el contrato."),
            _c("arrendador", TRANSCRIPCION, "Razón social del arrendador."),
            NAVE,
            _c("ubicacion", TEXTO, "Domicilio o ubicación de la nave."),
            _c("superficie_m2", NUMERO, "Superficie rentada en metros cuadrados."),
            _c("renta_mensual", NUMERO, "Renta mensual pactada, sin IVA."),
            _c("moneda", TEXTO, "Moneda de la renta: MXN o USD."),
            _c("fecha_inicio", FECHA, "Fecha de inicio del arrendamiento."),
            _c("fecha_vencimiento", FECHA, "Fecha de vencimiento del arrendamiento."),
            _c("incrementos", TEXTO, "Cómo y cuándo se incrementa la renta."),
            _c("garantia", TEXTO, "Depósito en garantía, fianza o carta de crédito pactada."),
            _c("mantenimiento", TEXTO, "Quién paga el mantenimiento."),
            _c("predial", TEXTO, "Quién paga el impuesto predial."),
            _c("seguro", TEXTO, "Quién paga o contrata los seguros."),
            _c("terminacion_anticipada", TEXTO, "Condiciones de terminación anticipada."),
        ),
    ),
    "escritura": Tipo(
        "escritura",
        "Escritura pública de propiedad del inmueble.",
        campos=(
            _c("propietario", TRANSCRIPCION, "Propietario del inmueble según la escritura."),
            _c("ubicacion", TEXTO, "Ubicación del inmueble."),
            _c("superficie_terreno_m2", NUMERO, "Superficie del terreno en metros cuadrados."),
            _c("gravamenes", TEXTO, "Gravámenes, hipotecas o limitaciones de dominio mencionados, o que está libre de ellos."),
        ),
        renglones=(
            NAVE,
            _c("superficie_construida_m2", NUMERO, "Superficie construida de esa nave en metros cuadrados."),
        ),
        descripcion_renglon="Una entrada por cada nave o construcción que la escritura describe con su superficie.",
    ),
    "permiso": Tipo(
        "permiso",
        "Permiso, licencia o dictamen de una autoridad (uso de suelo, construcción, protección civil, ambiental...).",
        campos=(_c("titular", TRANSCRIPCION, "Titular del permiso."),),
        renglones=(
            _c("tipo_permiso", TRANSCRIPCION, "Nombre del permiso, licencia o dictamen tal como lo titula el documento."),
            _c("alcance", TEXTO, "Naves o predio que ampara."),
            _c("autoridad", TEXTO, "Autoridad que lo emite."),
            _c("fecha_emision", FECHA, "Fecha de emisión."),
            _c("vigencia_hasta", FECHA, "Fecha hasta la que es vigente. Vacío si el documento no dice vigencia."),
        ),
        descripcion_renglon="Una entrada por cada permiso, licencia o dictamen distinto que traiga el archivo.",
    ),
    "oficio_cfe": Tipo(
        "oficio_cfe",
        "Oficio de la empresa suministradora de electricidad (CFE u otra): factibilidad, contrato o condiciones de servicio.",
        campos=(
            _c("emisor", TRANSCRIPCION, "Quién emite el oficio."),
            _c("tipo_servicio", TRANSCRIPCION, "Tipo de servicio o tarifa, transcrito tal cual (p. ej. 'media tensión, tarifa GDMTH')."),
            _c("lo_que_dice", TRANSCRIPCION, "Transcripción literal de lo que el oficio dice sobre el servicio, la carga o sus condiciones. No se interpreta ni se resume."),
            _c("fecha", FECHA, "Fecha del oficio."),
        ),
    ),
    "lista_rentas": Tipo(
        "lista_rentas",
        "Relación o lista de rentas (rent roll) entregada por el vendedor.",
        renglones=(
            _c("inquilino", TRANSCRIPCION, "Inquilino como aparece en la lista."),
            NAVE,
            _c("superficie_m2", NUMERO, "Superficie en metros cuadrados."),
            _c("renta_mensual", NUMERO, "Renta mensual."),
            _c("moneda", TEXTO, "Moneda: MXN o USD."),
        ),
        descripcion_renglon="Una entrada por cada renglón de la lista.",
    ),
}

OTRO = "otro"


def _esquema_campo(campo: Campo) -> dict:
    return {
        "type": "object",
        "description": campo.descripcion,
        "properties": {
            "valor": {"type": "string", "description": "El valor; cadena vacía si el documento no lo dice."},
            "pagina": {"type": "integer", "description": "Número de página (1 = primera) donde está la cita; 0 si no hay valor."},
            "cita": {"type": "string", "description": "Fragmento copiado EXACTO del texto de esa página que sostiene el valor; vacío si no hay valor."},
        },
        "required": ["valor", "pagina", "cita"],
        "additionalProperties": False,
    }


def _objeto(campos: tuple[Campo, ...]) -> dict:
    return {
        "type": "object",
        "properties": {c.nombre: _esquema_campo(c) for c in campos},
        "required": [c.nombre for c in campos],
        "additionalProperties": False,
    }


def esquema_extraccion(tipo: Tipo) -> dict:
    propiedades, requeridos = {}, []
    if tipo.campos:
        propiedades["campos"] = _objeto(tipo.campos)
        requeridos.append("campos")
    if tipo.renglones:
        renglon = _objeto(tipo.renglones)
        propiedades["renglones"] = {"type": "array", "description": tipo.descripcion_renglon, "items": renglon}
        requeridos.append("renglones")
    return {"type": "object", "properties": propiedades, "required": requeridos, "additionalProperties": False}


ESQUEMA_CLASIFICACION = {
    "type": "object",
    "properties": {
        "tipo": {"type": "string", "enum": [*TIPOS, OTRO]},
        "motivo": {"type": "string", "description": "Una línea: por qué es de ese tipo."},
    },
    "required": ["tipo", "motivo"],
    "additionalProperties": False,
}


def es_clasificacion(esquema: dict) -> bool:
    return "tipo" in (esquema.get("properties") or {})
