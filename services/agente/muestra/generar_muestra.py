"""Genera la muestra FICTICIA de propiedades vacacionales (finca y quinta).

    python services/agente/muestra/generar_muestra.py

**Todo aquí es inventado**: números de teléfono 52100000000xx, montos,
frases y conversaciones. No son del familiar de la demo ni de nadie (no se
guardan nombres ni teléfonos reales en el repo). Sirve para los tests y para
enseñar el flujo; ninguna cifra de aquí se le dice a un cliente real.

Escribe:
- `historial_webhook.json`: el historial en la forma del webhook `history` de Meta.
- `alta.json`: lo que el dueño escribiría en el alta.
- `perfil_grabado.json`: lo que el modelo grande "propondría" (respuesta
  grabada), con dos renglones malos a propósito: uno cita a un cliente final y
  otro trae un monto que no está en su cita. Los dos deben caer.
"""
from __future__ import annotations

import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
NEGOCIO = "5210000000000"
INICIO = 1780300800  # 2026-06-01 08:00 UTC

CONVERSACIONES = [
    [("c", "Hola, buenas tardes. Quiero informes de la finca para un cumpleaños"),
     ("n", "Buenas tardes, con gusto. Para que fecha seria y cuantas personas?"),
     ("c", "Sería el 14 de noviembre, unas 25 personas"),
     ("n", "La finca entre semana sale en $6,000 la noche y viernes o sábado en $8,500. El evento se cobra aparte, $5,000."),
     ("c", "Va, lo platico y le aviso")],
    [("c", "Buenas, ¿la quinta acepta mascotas?"),
     ("n", "Si, aceptamos mascotas en la quinta, solo le pedimos que no se suban a las camas."),
     ("c", "Perfecto gracias")],
    [("c", "Hola cuál es el horario de entrada?"),
     ("n", "La entrada es a las 3 de la tarde y la salida a las 12 del dia."),
     ("c", "Ok")],
    [("c", "Buen día, para diciembre cuánto cuesta la finca?"),
     ("n", "En temporada alta, del 15 de diciembre al 6 de enero, la noche en la finca es de $9,500."),
     ("c", "Y cuántas personas caben?"),
     ("n", "En la finca duermen hasta 30 personas. Arriba de 20 personas se cobran $250 por persona extra por noche.")],
    [("c", "Qué incluye la quinta?"),
     ("n", "La quinta tiene alberca, asador y cuatro recamaras. Caben 12 personas."),
     ("c", "Y el precio?"),
     ("n", "La quinta sale en $3,500 la noche entre semana y $4,500 viernes o sábado. Mínimo 2 noches.")],
    [("c", "Hola cómo aparto?"),
     ("n", "Se aparta con el 50% de anticipo y el resto al llegar. Además se deja un depósito de $3,000 que se regresa al salir."),
     ("c", "Gracias")],
    [("c", "Oiga me cobraron de más el depósito, no me lo regresaron"),
     ("n", "Disculpe, eso lo revisa directamente el encargado, ahorita le marca.")],
    [("c", "Hasta qué hora puede durar la música en un evento?"),
     ("n", "La música es hasta las 2 de la mañana, por los vecinos."),
     ("c", "Ok gracias")],
    [("c", "Buenas, para la finca también es mínimo 2 noches?"),
     ("n", "Si, en la finca el minimo es de 2 noches."),
     ("c", "Va")],
]


def historial() -> dict:
    hilos = []
    ts = INICIO
    for i, conversacion in enumerate(CONVERSACIONES, start=1):
        cliente = f"52100000000{i:02d}"
        mensajes = []
        for j, (quien, texto) in enumerate(conversacion):
            ts += 600 + 60 * j
            mensajes.append({"from": NEGOCIO if quien == "n" else cliente, "id": f"wamid.MUESTRA{i:02d}{j:02d}",
                             "timestamp": str(ts), "type": "text", "text": {"body": texto},
                             "history_context": {"status": "READ"}})
        hilos.append({"id": cliente, "messages": mensajes})
        ts += 86400
    return {"object": "whatsapp_business_account", "entry": [{"id": "000000000000000", "changes": [{
        "field": "history", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": NEGOCIO, "phone_number_id": "100000000000001"},
            "history": [{"metadata": {"phase": 1, "chunk_order": 1, "progress": 100}, "threads": hilos}]}}]}]}


ALTA = {
    "giro": "renta vacacional (MUESTRA FICTICIA)",
    "nombre_comercial": "Finca y Quinta de Muestra",
    "que_vende": "Renta de una finca para eventos y familias grandes y de una quinta más chica",
    "como_cobra": "Por noche, más caro viernes y sábado; los eventos aparte",
    "horario": "Contestamos de 9 a 21 h",
    "aprobador": "Dueña de muestra",
    "aprobador_telefono": "5210000000000",
    "asesores": ["Encargado de muestra"],
    "propiedades": ["finca", "quinta"],
}


def m(i: int, j: int, cita: str) -> dict:
    return {"tipo": "mensaje", "id": f"wamid.MUESTRA{i:02d}{j:02d}", "cita": cita}


def regla(propiedad, tipo, origen, **campos) -> dict:
    return {"propiedad": propiedad, "tipo": tipo, **campos, "origen": origen}


PERFIL = {
    "trato": "usted",
    "datos": [
        {"objeto": "Propiedad", "id": "finca", "campo": "capacidad_personas", "valor": 30,
         "origen": m(4, 3, "En la finca duermen hasta 30 personas")},
        {"objeto": "Propiedad", "id": "quinta", "campo": "incluye", "valor": "alberca, asador y cuatro recamaras",
         "origen": m(5, 1, "La quinta tiene alberca, asador y cuatro recamaras")},
        {"objeto": "Propiedad", "id": "quinta", "campo": "mascotas", "valor": "sí, sin subirse a las camas",
         "origen": m(2, 1, "aceptamos mascotas en la quinta")},
        {"objeto": "Regla", "id": "musica", "campo": "hora_limite", "valor": "2 de la mañana",
         "origen": m(8, 1, "La música es hasta las 2 de la mañana")},
    ],
    "temporadas": [
        {"nombre": "alta", "desde": "12-15", "hasta": "01-06",
         "origen": m(4, 1, "En temporada alta, del 15 de diciembre al 6 de enero")},
    ],
    "voz": [
        {"frase": "Buenas tardes, con gusto. Para que fecha seria y cuantas personas?",
         "origen": m(1, 1, "Buenas tardes, con gusto. Para que fecha seria y cuantas personas?")},
        {"frase": "Si, aceptamos mascotas en la quinta, solo le pedimos que no se suban a las camas.",
         "origen": m(2, 1, "Si, aceptamos mascotas en la quinta, solo le pedimos que no se suban a las camas.")},
    ],
    "reglas": [
        regla("finca", "noche", m(1, 3, "La finca entre semana sale en $6,000 la noche"),
              dias="entre_semana", monto_centavos=600000),
        regla("finca", "noche", m(1, 3, "viernes o sábado en $8,500"), dias="fin_de_semana", monto_centavos=850000),
        regla("finca", "noche", m(4, 1, "la noche en la finca es de $9,500"), temporada="alta", monto_centavos=950000),
        regla("finca", "evento", m(1, 3, "El evento se cobra aparte, $5,000"), monto_centavos=500000),
        regla("finca", "capacidad", m(4, 3, "En la finca duermen hasta 30 personas"), personas=30),
        regla("finca", "persona_extra", m(4, 3, "Arriba de 20 personas se cobran $250 por persona extra por noche"),
              personas=20, monto_centavos=25000),
        regla("finca", "minimo_noches", m(9, 1, "en la finca el minimo es de 2 noches"), noches=2),
        regla("finca", "anticipo", m(6, 1, "Se aparta con el 50% de anticipo"), pct=50),
        regla("finca", "deposito", m(6, 1, "un depósito de $3,000 que se regresa al salir"), monto_centavos=300000),
        regla("quinta", "noche", m(5, 3, "La quinta sale en $3,500 la noche entre semana"),
              dias="entre_semana", monto_centavos=350000),
        regla("quinta", "noche", m(5, 3, "$4,500 viernes o sábado"), dias="fin_de_semana", monto_centavos=450000),
        regla("quinta", "capacidad", m(5, 1, "Caben 12 personas"), personas=12),
        regla("quinta", "minimo_noches", m(5, 3, "Mínimo 2 noches"), noches=2),
        regla("quinta", "anticipo", m(6, 1, "Se aparta con el 50% de anticipo"), pct=50),
        # MALO a propósito: el monto no está en la cita. Debe caer.
        regla("quinta", "evento", m(5, 3, "La quinta sale en $3,500 la noche"), monto_centavos=200000),
    ],
    "faq": [
        {"pregunta": "Cuál es el horario de entrada y salida?",
         "respuesta": "La entrada es a las 3 de la tarde y la salida a las 12 del dia.",
         "origen": m(3, 1, "La entrada es a las 3 de la tarde y la salida a las 12 del dia.")},
        {"pregunta": "La quinta acepta mascotas?",
         "respuesta": "Si, aceptamos mascotas en la quinta, solo le pedimos que no se suban a las camas.",
         "origen": m(2, 1, "aceptamos mascotas en la quinta")},
    ],
    "escala": [
        {"caso": "reclamo por el depósito", "origen": m(7, 0, "me cobraron de más el depósito")},
    ],
}
# MALO a propósito: una "frase de voz" que es del cliente final. Debe caer.
PERFIL["voz"].append({"frase": "Perfecto gracias", "origen": m(2, 2, "Perfecto gracias")})


def main() -> None:
    (AQUI / "historial_webhook.json").write_text(json.dumps(historial(), ensure_ascii=False, indent=1), encoding="utf-8")
    (AQUI / "alta.json").write_text(json.dumps(ALTA, ensure_ascii=False, indent=1), encoding="utf-8")
    (AQUI / "perfil_grabado.json").write_text(json.dumps(PERFIL, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
