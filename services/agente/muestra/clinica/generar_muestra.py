"""Genera la muestra FICTICIA de una clínica estética (faciales, Botox, láser).

    python services/agente/muestra/clinica/generar_muestra.py

**Todo aquí es inventado**: teléfonos 52100000001xx, montos, frases y
conversaciones. No es de ninguna clínica real ni de nadie: sirve para enseñar
la app a un prospecto y para los tests. Ninguna cifra de aquí se le dice a un
cliente real.

Escribe en esta carpeta, con la misma forma que la muestra de la finca:
- `historial_webhook.json`: el historial en la forma del webhook `history` de Meta.
- `alta.json`: lo que la dueña escribiría en el alta.
- `perfil_grabado.json`: lo que el modelo grande "propondría", con dos renglones
  malos a propósito (un precio que no está en su cita y una "frase de voz" de
  una clienta). Los dos deben caer al validar.
"""
from __future__ import annotations

import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
NEGOCIO = "5210000000100"
INICIO = 1788249600  # 2026-09-01 08:00 UTC

CONVERSACIONES = [
    # 1
    [("c", "Hola buenas tardes, cuánto cuesta la limpieza facial?"),
     ("n", "Buenas tardes, con gusto. La limpieza facial profunda tiene un costo de $850 por sesión e incluye extracción, mascarilla y protector solar."),
     ("c", "Y cada cuánto se hace?"),
     ("n", "Se recomienda una vez al mes. Si gusta llevar 4 sesiones, el paquete queda en $3,000."),
     ("c", "Ok lo pienso, gracias")],
    # 2
    [("c", "Hola! Precio del botox?"),
     ("n", "Hola, buen día. El Botox tiene un costo de $3,500 por zona (frente, entrecejo o patas de gallo)."),
     ("c", "Y si son las 3 zonas?"),
     ("n", "Las 3 zonas quedan en $8,500. Antes del tratamiento se hace una valoración con la doctora."),
     ("c", "Va, gracias")],
    # 3
    [("c", "Buenas, la valoración tiene costo?"),
     ("n", "La valoración tiene un costo de $300 y se abona a su tratamiento si lo realiza el mismo día."),
     ("c", "Perfecto")],
    # 4
    [("c", "Cuánto la depilación láser de axila?"),
     ("n", "La depilación láser de axila es de $450 por sesión. El paquete de 6 sesiones queda en $2,400."),
     ("c", "Y piernas completas?"),
     ("n", "Piernas completas es de $1,800 por sesión."),
     ("c", "Gracias")],
    # 5
    [("c", "Hola, estoy embarazada, me puedo aplicar botox?"),
     ("n", "Felicidades. Eso se lo tiene que valorar la doctora, ahorita le pido que le escriba.")],
    # 6
    [("c", "Qué horario tienen?"),
     ("n", "Atendemos de lunes a viernes de 10 a 8 y sábados de 10 a 3."),
     ("c", "Ok gracias")],
    # 7
    [("c", "Cómo aparto mi cita?"),
     ("n", "Su cita se aparta con un anticipo de $200, que se descuenta del tratamiento."),
     ("c", "Ok")],
    # 8
    [("c", "Oiga me hice el peeling y me quedó la cara muy roja y me arde"),
     ("n", "Una disculpa, ahorita la doctora le marca para revisarla.")],
    # 9
    [("c", "Dónde están ubicados?"),
     ("n", "Estamos en Av. de Muestra 123, local 4, a un costado de la farmacia."),
     ("c", "Gracias")],
    # 10
    [("c", "Buen día, el hidrofacial cuánto sale?"),
     ("n", "Buen día. El hidrofacial tiene un costo de $1,200 por sesión."),
     ("c", "Gracias, luego le aviso")],
    # 11 — pendiente: pidió precio y nadie contestó (la demo enseña qué haría el agente)
    [("c", "Hola, precio de la limpieza facial por favor")],
    # 12 — pendiente
    [("c", "Buenas noches, cuánto cuesta el botox de frente?")],
    # 13 — pendiente: pregunta de salud, la ve la doctora
    [("c", "Hola, tomo anticoagulantes, puedo hacerme el láser?")],
    # 14 — pendiente: pide precio sin decir de qué
    [("c", "Hola, me pasa sus precios?")],
]


def historial() -> dict:
    hilos = []
    ts = INICIO
    for i, conversacion in enumerate(CONVERSACIONES, start=1):
        cliente = f"52100000001{i:02d}"
        mensajes = []
        for j, (quien, texto) in enumerate(conversacion):
            ts += 600 + 60 * j
            mensajes.append({"from": NEGOCIO if quien == "n" else cliente, "id": f"wamid.CLINICA{i:02d}{j:02d}",
                             "timestamp": str(ts), "type": "text", "text": {"body": texto},
                             "history_context": {"status": "READ"}})
        hilos.append({"id": cliente, "messages": mensajes})
        ts += 86400
    return {"object": "whatsapp_business_account", "entry": [{"id": "000000000000000", "changes": [{
        "field": "history", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": NEGOCIO, "phone_number_id": "100000000000101"},
            "history": [{"metadata": {"phase": 1, "chunk_order": 1, "progress": 100}, "threads": hilos}]}}]}]}


ALTA = {
    "giro": "clínica estética (MUESTRA FICTICIA)",
    "nombre_comercial": "Clínica Estética de Muestra",
    "que_vende": "Faciales, Botox y rellenos, depilación láser y peelings, con valoración de la doctora",
    "como_cobra": "Por sesión o por zona, con paquetes de varias sesiones; la cita se aparta con anticipo",
    "horario": "Lunes a viernes de 10 a 20 h y sábados de 10 a 15 h",
    "aprobador": "Doctora de muestra",
    "aprobador_telefono": "5210000000100",
    "asesores": ["Recepción de muestra"],
    # En una clínica, "propiedades" son las categorías de la lista de precios.
    "propiedades": ["faciales", "inyectables", "laser"],
}


def m(i: int, j: int, cita: str) -> dict:
    return {"tipo": "mensaje", "id": f"wamid.CLINICA{i:02d}{j:02d}", "cita": cita}


def servicio(categoria, clave, nombre, unidad, origen, alias, **campos) -> dict:
    return {"propiedad": categoria, "tipo": "servicio", "servicio": clave, "nombre": nombre,
            "unidad": unidad, "alias": alias, **campos, "origen": origen}


PERFIL = {
    "trato": "usted",
    "datos": [
        {"objeto": "Servicio", "id": "limpieza_facial", "campo": "incluye",
         "valor": "extracción, mascarilla y protector solar",
         "origen": m(1, 1, "incluye extracción, mascarilla y protector solar")},
        {"objeto": "Negocio", "id": "ubicacion", "campo": "direccion", "valor": "Av. de Muestra, local 4",
         "origen": m(9, 1, "Estamos en Av. de Muestra 123, local 4")},
    ],
    "temporadas": [],
    "voz": [
        {"frase": "Buenas tardes, con gusto.", "origen": m(1, 1, "Buenas tardes, con gusto.")},
        {"frase": "Eso se lo tiene que valorar la doctora, ahorita le pido que le escriba.",
         "origen": m(5, 1, "Eso se lo tiene que valorar la doctora, ahorita le pido que le escriba.")},
    ],
    "reglas": [
        servicio("faciales", "limpieza_facial", "Limpieza facial profunda", "sesion",
                 m(1, 1, "La limpieza facial profunda tiene un costo de $850 por sesión"),
                 ["limpieza facial", "limpieza profunda", "limpieza de cara", "facial"], monto_centavos=85000),
        servicio("faciales", "limpieza_facial", "Limpieza facial profunda", "paquete",
                 m(1, 3, "Si gusta llevar 4 sesiones, el paquete queda en $3,000"),
                 ["limpieza facial", "limpieza profunda", "limpieza de cara", "facial"],
                 sesiones=4, monto_centavos=300000),
        servicio("faciales", "hidrofacial", "Hidrofacial", "sesion",
                 m(10, 1, "El hidrofacial tiene un costo de $1,200 por sesión"),
                 ["hidrofacial", "hydrafacial", "hidro facial"], monto_centavos=120000),
        servicio("inyectables", "botox", "Botox", "zona",
                 m(2, 1, "El Botox tiene un costo de $3,500 por zona"),
                 ["botox", "toxina", "botulinica", "baby botox"], monto_centavos=350000),
        servicio("inyectables", "botox", "Botox", "paquete",
                 m(2, 3, "Las 3 zonas quedan en $8,500"),
                 ["botox", "toxina", "botulinica", "baby botox"], zonas=3, monto_centavos=850000),
        servicio("laser", "laser_axila", "Depilación láser de axila", "sesion",
                 m(4, 1, "La depilación láser de axila es de $450 por sesión"),
                 ["axila", "axilas"], monto_centavos=45000),
        servicio("laser", "laser_axila", "Depilación láser de axila", "paquete",
                 m(4, 1, "El paquete de 6 sesiones queda en $2,400"),
                 ["axila", "axilas"], sesiones=6, monto_centavos=240000),
        servicio("laser", "laser_piernas", "Depilación láser de piernas completas", "sesion",
                 m(4, 3, "Piernas completas es de $1,800 por sesión"),
                 ["piernas completas", "piernas"], monto_centavos=180000),
        {"tipo": "valoracion", "propiedad": "inyectables", "monto_centavos": 30000, "abona": True,
         "origen": m(3, 1, "La valoración tiene un costo de $300 y se abona a su tratamiento")},
        {"tipo": "anticipo_cita", "propiedad": None, "monto_centavos": 20000,
         "origen": m(7, 1, "Su cita se aparta con un anticipo de $200")},
        # MALO a propósito: el monto no está en la cita. Debe caer.
        servicio("faciales", "peeling", "Peeling químico", "sesion",
                 m(10, 1, "El hidrofacial tiene un costo de $1,200 por sesión"),
                 ["peeling"], monto_centavos=95000),
    ],
    "faq": [
        {"pregunta": "Qué horario tienen?",
         "respuesta": "Atendemos de lunes a viernes de 10 a 8 y sábados de 10 a 3.",
         "origen": m(6, 1, "Atendemos de lunes a viernes de 10 a 8 y sábados de 10 a 3.")},
        {"pregunta": "Dónde están ubicados?",
         "respuesta": "Estamos en Av. de Muestra 123, local 4, a un costado de la farmacia.",
         "origen": m(9, 1, "Estamos en Av. de Muestra 123, local 4, a un costado de la farmacia.")},
    ],
    "escala": [
        {"caso": "pregunta de salud o contraindicación", "origen": m(5, 0, "estoy embarazada")},
        {"caso": "reacción después de un tratamiento", "origen": m(8, 0, "me quedó la cara muy roja y me arde")},
    ],
}
# MALO a propósito: una "frase de voz" que es de la clienta. Debe caer.
PERFIL["voz"].append({"frase": "Perfecto", "origen": m(3, 2, "Perfecto")})


def main() -> None:
    (AQUI / "historial_webhook.json").write_text(json.dumps(historial(), ensure_ascii=False, indent=1), encoding="utf-8")
    (AQUI / "alta.json").write_text(json.dumps(ALTA, ensure_ascii=False, indent=1), encoding="utf-8")
    (AQUI / "perfil_grabado.json").write_text(json.dumps(PERFIL, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
