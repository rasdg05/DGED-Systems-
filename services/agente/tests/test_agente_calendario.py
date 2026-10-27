"""El calendario de ocupación (iCal de Airbnb, Booking y Google) y su lugar en la cotización.

Los .ics de aquí tienen la forma que publican las plataformas; **no** son una
descarga de Finca Emiliano (no medido contra sus calendarios).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from agente import agente, calendario
from agente.espacio import Espacio
from fastapi.testclient import TestClient
from tests.test_agente_lista_precios import BASE, LISTA, T0, _m

AIRBNB = """BEGIN:VCALENDAR\r
PRODID;X-RICAL-TZSOURCE=TZINFO:-//Airbnb Inc//Hosting Calendar 1.0//EN\r
CALSCALE:GREGORIAN\r
VERSION:2.0\r
BEGIN:VEVENT\r
DTEND;VALUE=DATE:20261108\r
DTSTART;VALUE=DATE:20261106\r
UID:1418fb94e984-ab0c1b2d@airbnb.com\r
DESCRIPTION:Reservation URL: https://www.airbnb.com/hosting/reservations/de\r
 tails/HMXXXXXXXX\\nPhone Number (Last 4 Digits): 0000\r
SUMMARY:Reserved\r
END:VEVENT\r
BEGIN:VEVENT\r
DTEND;VALUE=DATE:20261202\r
DTSTART;VALUE=DATE:20261128\r
UID:7f8c-bloqueo@airbnb.com\r
SUMMARY:Airbnb (Not available)\r
END:VEVENT\r
END:VCALENDAR\r
"""

BOOKING = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Booking.com//Booking.com Calendar//EN
BEGIN:VEVENT
UID:1a2b3c@booking.com
DTSTAMP:20261027T120000Z
DTSTART;VALUE=DATE:20261113
DTEND;VALUE=DATE:20261115
SUMMARY:CLOSED - Not available
END:VEVENT
BEGIN:VEVENT
UID:cancelada@booking.com
DTSTART;VALUE=DATE:20261120
DTEND;VALUE=DATE:20261122
STATUS:CANCELLED
SUMMARY:CLOSED - Not available
END:VEVENT
END:VCALENDAR
"""

GOOGLE = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Google Inc//Google Calendar 70.9054//EN
BEGIN:VEVENT
DTSTART;TZID=America/Mexico_City:20261120T150000
DTEND;TZID=America/Mexico_City:20261122T120000
SUMMARY:Quinta - familia que regresa
UID:abc@google.com
END:VEVENT
BEGIN:VEVENT
DTSTART:20261125T160000Z
DTEND:20261125T180000Z
SUMMARY:Visita para ver la finca
UID:visita@google.com
END:VEVENT
END:VCALENDAR
"""

AHORA = datetime(2026, 10, 27, 18, 0, tzinfo=timezone.utc)


# ----------------------------------------------------------------- leer el .ics
def test_airbnb_reserva_y_bloqueo_con_la_salida_sin_contar_y_lineas_plegadas():
    bloques = calendario.leer_ics(AIRBNB)
    assert [(b.desde, b.hasta, b.tipo) for b in bloques] == [
        (date(2026, 11, 6), date(2026, 11, 8), "reserva"), (date(2026, 11, 28), date(2026, 12, 2), "bloqueo")]
    assert bloques[0].noches() == [date(2026, 11, 6), date(2026, 11, 7)]


def test_booking_lo_cancelado_no_ocupa():
    assert [(b.desde, b.tipo) for b in calendario.leer_ics(BOOKING)] == [(date(2026, 11, 13), "bloqueo")]


def test_google_lo_que_cruza_la_noche_ocupa_y_una_visita_del_dia_no():
    bloques = calendario.leer_ics(GOOGLE)
    assert [(b.desde, b.hasta) for b in bloques] == [(date(2026, 11, 20), date(2026, 11, 22))]


@pytest.mark.parametrize("texto", ["<html><body>Inicia sesión</body></html>", "", "Not Found"])
def test_un_200_que_no_es_calendario_no_se_lee_como_vacio(texto):
    with pytest.raises(calendario.NoEsCalendario):
        calendario.leer_ics(texto)


# ----------------------------------------------------------------- invariante LXI
def _espacio(tmp_path, *fuentes) -> Espacio:
    espacio = Espacio("finca-prueba", tmp_path)
    for propiedad, plataforma in fuentes:
        calendario.agregar_fuente(espacio, propiedad, plataforma, f"https://ejemplo.test/{propiedad}-{plataforma}.ics")
    return espacio


def _bajador(**por_plataforma):
    def descargar(url):
        respuesta = por_plataforma[url.rsplit("-", 1)[1].removesuffix(".ics")]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta
    return descargar


NOV = (date(2026, 11, 9), date(2026, 11, 11))  # lunes a miércoles, sin nada en ningún calendario


def test_libre_solo_si_todas_las_fuentes_de_la_propiedad_respondieron_y_estan_frescas(tmp_path):
    espacio = _espacio(tmp_path, ("finca", "airbnb"), ("finca", "booking"))
    # sin descargar: no se sabe
    assert calendario.Ocupacion.de(espacio, AHORA).disponibilidad("finca", *NOV).estado == calendario.NO_SE_SABE
    # una de las dos devolvió una página de error con 200: no se sabe, nunca libre
    calendario.bajar(espacio, _bajador(airbnb=AIRBNB, booking="<html>error</html>"), AHORA)
    d = calendario.Ocupacion.de(espacio, AHORA).disponibilidad("finca", *NOV)
    assert d.estado == calendario.NO_SE_SABE and "booking" in d.por_que
    # las dos bien: libre
    calendario.bajar(espacio, _bajador(airbnb=AIRBNB, booking=BOOKING), AHORA)
    assert calendario.Ocupacion.de(espacio, AHORA).disponibilidad("finca", *NOV).estado == calendario.LIBRE
    # pasadas las horas de vigencia sin volver a leer: no se sabe
    tarde = AHORA + timedelta(hours=calendario.VIGENCIA_HORAS, minutes=1)
    assert calendario.Ocupacion.de(espacio, tarde).disponibilidad("finca", *NOV).estado == calendario.NO_SE_SABE
    # una propiedad sin calendario conectado: no se sabe
    assert calendario.Ocupacion.de(espacio, AHORA).disponibilidad("quinta", *NOV).estado == calendario.NO_SE_SABE


def test_una_fuente_que_falla_despues_no_borra_lo_ocupado_ni_se_vuelve_libre(tmp_path):
    espacio = _espacio(tmp_path, ("finca", "airbnb"))
    calendario.bajar(espacio, _bajador(airbnb=AIRBNB), AHORA)
    calendario.bajar(espacio, _bajador(airbnb=OSError("timeout")), AHORA + timedelta(minutes=30))
    oc = calendario.Ocupacion.de(espacio, AHORA + timedelta(minutes=31))
    assert oc.disponibilidad("finca", date(2026, 11, 6), date(2026, 11, 8)).estado == calendario.OCUPADA
    assert oc.disponibilidad("finca", *NOV).estado == calendario.NO_SE_SABE


def test_ocupada_por_cualquiera_de_sus_fuentes_y_las_dos_casas_si_una_lo_esta(tmp_path):
    espacio = _espacio(tmp_path, ("finca", "airbnb"), ("finca", "booking"), ("quinta", "google"))
    calendario.bajar(espacio, _bajador(airbnb=AIRBNB, booking=BOOKING, google=GOOGLE), AHORA)
    oc = calendario.Ocupacion.de(espacio, AHORA)
    d = oc.disponibilidad("finca", date(2026, 11, 13), date(2026, 11, 15))
    assert d.estado == calendario.OCUPADA and d.choques[0]["fuente"] == "booking"
    # la salida es el día que otro llega: no choca
    assert oc.disponibilidad("finca", date(2026, 11, 4), date(2026, 11, 6)).estado == calendario.LIBRE
    assert oc.disponibilidad("ambas", date(2026, 11, 20), date(2026, 11, 22)).estado == calendario.OCUPADA
    assert oc.disponibilidad("ambas", *NOV).estado == calendario.LIBRE
    marcas = {f["noche"]: f["estado"] for f in oc.noches(date(2026, 11, 5), 4)["finca"]}
    assert marcas == {"2026-11-05": "libre", "2026-11-06": "ocupada", "2026-11-07": "ocupada", "2026-11-08": "libre"}


def test_la_url_va_con_https_y_no_sale_en_la_vista(tmp_path, monkeypatch):
    espacio = _espacio(tmp_path, ("finca", "airbnb"))
    with pytest.raises(ValueError):
        calendario.agregar_fuente(espacio, "finca", "airbnb", "http://ejemplo.test/x.ics")
    from agente import app as app_mod
    from agente.espacio import llave_de

    monkeypatch.setenv("TENANT_INTERNAL_TOKEN", "secreto-de-prueba")
    monkeypatch.setenv("AGENTE_DATOS", str(tmp_path))
    calendario.bajar(espacio, _bajador(airbnb=AIRBNB))  # el servidor lee con el reloj de pared
    r = TestClient(app_mod.app).get("/espacios/finca-prueba/calendario.json?desde=2026-11-05&dias=3",
                                    headers={"X-Tenant-Key": llave_de("finca-prueba")})
    assert r.status_code == 200 and "ejemplo.test" not in r.text
    assert [n["estado"] for n in r.json()["noches"]["finca"]] == ["libre", "ocupada", "ocupada"]
    malo = TestClient(app_mod.app).post("/espacios/finca-prueba/calendario/fuentes", headers={
        "X-Tenant-Key": llave_de("finca-prueba")}, json={"propiedad": "quinta", "plataforma": "airbnb",
                                                          "url": "http://ejemplo.test/q.ics"})
    assert malo.status_code == 422 and "https" in malo.text


# ----------------------------------------------------------------- invariante LXII, en el turno
def _ocupacion(tmp_path, **por_plataforma) -> calendario.Ocupacion:
    fuentes = [("finca", "airbnb"), ("quinta", "google")]
    espacio = _espacio(tmp_path, *fuentes)
    calendario.bajar(espacio, _bajador(**por_plataforma), AHORA)
    return calendario.Ocupacion.de(espacio, AHORA)


def _turno_con(ocupacion, *mensajes):
    hilo = [_m(f"c{i}", t, n, T0 + i * 60, BASE["hilo"]) for i, (t, n) in enumerate(mensajes)]
    return agente.antes_del_modelo(BASE, hilo[-1], hilo, LISTA, ocupacion)


def test_una_propiedad_ocupada_no_sale_en_la_cotizacion(tmp_path):
    # 18 personas caben en la finca y en la quinta; la finca está reservada en Airbnb ese fin.
    oc = _ocupacion(tmp_path, airbnb=AIRBNB, google=GOOGLE)
    s = _turno_con(oc, ("Somos 18, del 6 al 8 de noviembre, precio?", False))
    assert s.via == "cotizador" and s.requiere_aprobacion
    assert [o["propiedad"] for o in s.cotizacion["opciones"]] == ["quinta"]
    assert "Finca" not in s.texto and s.cotizacion["disponibilidad"][0]["estado"] == calendario.LIBRE


def test_si_todas_estan_ocupadas_va_a_una_persona_sin_cifra(tmp_path):
    google = GOOGLE.replace("20261120T150000", "20261106T150000").replace("20261122T120000", "20261108T120000")
    oc = _ocupacion(tmp_path, airbnb=AIRBNB, google=google)
    s = _turno_con(oc, ("Somos 18, del 6 al 8 de noviembre, precio?", False))
    assert s.via == "persona" and s.texto == agente.LO_CONFIRMO and not s.requiere_aprobacion
    assert "ocupadas" in s.motivo and "$" not in s.texto + s.borrador


def test_lo_que_el_calendario_no_sabe_viaja_a_quien_aprueba(tmp_path):
    oc = _ocupacion(tmp_path, airbnb=AIRBNB, google="<html>login</html>")
    s = _turno_con(oc, ("Somos 18, del 9 al 11 de noviembre, precio?", False))
    assert s.via == "cotizador" and s.requiere_aprobacion
    estados = {d["propiedad"]: d["estado"] for d in s.cotizacion["disponibilidad"]}
    assert estados == {"quinta": calendario.NO_SE_SABE}  # entre semana la finca no tiene precio para 18


def test_sin_calendario_el_turno_es_el_de_siempre():
    hilo = [_m("s0", "Somos 18, del 6 al 8 de noviembre, precio?", False, T0, BASE["hilo"])]
    s = agente.antes_del_modelo(BASE, hilo[-1], hilo, LISTA)
    assert s.via == "cotizador" and "disponibilidad" not in s.cotizacion
