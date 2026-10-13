"""Las dos reglas del medidor de fuentes (`herramientas/medir_fuentes.py`), sin red.

1. Un HTTP 200 no es un dato: el WAF del SMN contesta 200 con una página de
   error, y eso es MUERTA, no VIVA.
2. "No medido" no es "medido y no funcionó": sin respuesta HTTP el veredicto es
   NO CONCLUYE, y un 429 es CUOTA. Ninguno de los dos va al cementerio solo.
Ver `MEMORY/FUENTES.md`.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "medir_fuentes", RAIZ / "herramientas" / "medir_fuentes.py"
)
mf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mf)

PAGINA_WAF = (
    b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"><html><head>'
    b"<title>Error</title></head><body><H2>Error</H2>This page can't be displayed. "
    b"Contact support for additional information.</body></html>"
)


def _fijo(monkeypatch, respuesta):
    monkeypatch.setattr(mf, "pedir", lambda url, *a, **k: mf.Respuesta(url, **respuesta))
    monkeypatch.setattr(mf.time, "sleep", lambda s: None)


def test_medidor_200_del_waf_no_es_dato(monkeypatch):
    _fijo(monkeypatch, {"status": 200, "cuerpo": PAGINA_WAF, "latencia": 0.3})
    assert mf.smn_sequia(25.78, -100.19)["veredicto"] == "MUERTA"
    assert mf.smn_webservice(25.78, -100.19)["veredicto"] == "MUERTA"


def test_medidor_xlsx_con_firma_pk_es_viva(monkeypatch):
    _fijo(monkeypatch, {"status": 200, "cuerpo": b"PK\x03\x04resto", "latencia": 0.3})
    res = mf.smn_sequia(25.78, -100.19)
    assert res["veredicto"] == "VIVA"
    assert res["valor"]["con_dato"] == "5/5"


def test_medidor_sin_respuesta_no_concluye(monkeypatch):
    _fijo(monkeypatch, {"status": None, "error": "URLError: reset", "latencia": 7.0})
    for sonda in (mf.cenace_pml, mf.usgs_sismos, mf.nasa_power, mf.smn_sequia):
        assert sonda(25.78, -100.19)["veredicto"] == "NO CONCLUYE", sonda.__name__


def test_medidor_429_es_cuota_no_muerta(monkeypatch):
    _fijo(monkeypatch, {"status": 429, "cuerpo": b'{"error":true}', "latencia": 0.5})
    assert mf.openmeteo_archivo(25.78, -100.19)["veredicto"] == "CUOTA"


def test_medidor_no_publica_la_clave_en_la_url(monkeypatch):
    monkeypatch.setenv("FIRMS_MAP_KEY", "clave-secreta-123")
    monkeypatch.setenv("INEGI_BIE_TOKEN", "token-secreto-456")
    _fijo(monkeypatch, {"status": 400, "cuerpo": b"Invalid MAP_KEY.", "latencia": 0.2})
    firms = mf.nasa_firms(25.78, -100.19)
    bie = mf.inegi_bie(25.78, -100.19)
    assert "clave-secreta-123" not in str(firms)
    assert "token-secreto-456" not in str(bie)
    assert firms["veredicto"] == "CON CLAVE"


# ------------------------------------------- medición del 2026-10-13 (sin red)
import gzip  # noqa: E402
import json  # noqa: E402
import struct  # noqa: E402
import zlib  # noqa: E402


def _ruteado(monkeypatch, rutas):
    """`pedir` falso: la primera subcadena de `rutas` que esté en la URL decide."""
    def pedir(url, datos=None, cabeceras=None, timeout=None):
        for sub, resp in rutas:
            if sub in url:
                return resp(url, cabeceras or {}) if callable(resp) else mf.Respuesta(url, **resp)
        return mf.Respuesta(url, None, error="sin ruta en el test")
    monkeypatch.setattr(mf, "pedir", pedir)


def _geotiff_de_mosaicos(x0, y0, epsg=32614):
    """GeoTIFF clásico de 4×4 px en mosaicos de 2×2, uint16, deflate + predictor 2.
    El mosaico 1 (arriba a la derecha) vale 100, 200, 300, 400."""
    mosaicos = [[1, 1, 1, 1], [100, 200, 300, 400], [1, 1, 1, 1], [1, 1, 1, 1]]
    crudos = []
    for m in mosaicos:
        dif = [m[0], m[1] - m[0], m[2], m[3] - m[2]]  # predictor 2, fila por fila
        crudos.append(zlib.compress(struct.pack("<4H", *[d & 0xFFFF for d in dif])))
    geokeys = (1, 1, 0, 1, 3072, 0, 1, epsg)
    entradas = [  # (tag, tipo, valores)
        (256, 3, (4,)), (257, 3, (4,)), (258, 3, (16,)), (259, 3, (8,)), (277, 3, (1,)),
        (317, 3, (2,)), (322, 3, (2,)), (323, 3, (2,)), (324, 4, None), (325, 4, None),
        (33550, 12, (10.0, 10.0, 0.0)), (33922, 12, (0.0, 0.0, 0.0, x0, y0, 0.0)),
        (34735, 3, geokeys),
    ]
    fmt = {3: "H", 4: "I", 12: "d"}
    tam = {3: 2, 4: 4, 12: 8}
    ifd_off = 8
    datos_off = ifd_off + 2 + 12 * len(entradas) + 4
    extra = b""
    # Los mosaicos van después de los arreglos; primero se calcula dónde.
    largos_arreglos = sum(tam[t] * (4 if v is None else len(v)) for _, t, v in entradas
                          if tam[t] * (4 if v is None else len(v)) > 4)
    base_mosaicos = datos_off + largos_arreglos
    offs, pos = [], base_mosaicos
    for c in crudos:
        offs.append(pos)
        pos += len(c)
    ifd = struct.pack("<H", len(entradas))
    for tag, tipo, v in entradas:
        v = tuple(offs) if tag == 324 else tuple(len(c) for c in crudos) if tag == 325 else v
        crudo = struct.pack("<" + fmt[tipo] * len(v), *v)
        if len(crudo) <= 4:
            ifd += struct.pack("<HHI", tag, tipo, len(v)) + crudo.ljust(4, b"\0")
        else:
            ifd += struct.pack("<HHII", tag, tipo, len(v), datos_off + len(extra))
            extra += crudo
    ifd += b"\0\0\0\0"
    return b"II*\0" + struct.pack("<I", ifd_off) + ifd + extra + b"".join(crudos)


def _por_rango(buf):
    def resp(url, cab):
        ini, fin = (int(x) for x in cab["Range"].split("=")[1].split("-"))
        return mf.Respuesta(url, 206, buf[ini:fin + 1], 0.1)
    return resp


def test_utm_coincide_con_la_referencia_a_menos_de_un_metro():
    # Referencia: rasterio/PROJ (EPSG:4326 → 326xx/327xx), 2026-10-13.
    for lat, lon, zona, norte, x, y in (
        (25.78, -100.19, 14, True, 380681.258, 2851859.552),
        (18.15, -94.42, 15, True, 349790.211, 2007361.002),
        (20.95, -101.43, 14, True, 247312.203, 2318530.741),
        (-33.9, 151.2, 56, False, 333568.941, 6247473.337),
    ):
        cx, cy = mf.utm(lat, lon, zona, norte)
        assert abs(cx - x) < 1 and abs(cy - y) < 1, (lat, lon, cx, cy)


def test_tiff_ifd_rechaza_lo_que_no_es_tiff():
    import pytest
    for malo in (PAGINA_WAF, b"\x89PNG\r\n\x1a\n" + b"\0" * 20, b"II+\0" + b"\0" * 20):
        with pytest.raises(ValueError):
            mf.tiff_ifd(malo)


def test_recorte_cog_lee_el_mosaico_del_punto_y_deshace_el_predictor(monkeypatch):
    # El punto de Apodaca cae en la fila 1, columna 2 → mosaico 1.
    buf = _geotiff_de_mosaicos(380681.258 - 25, 2851859.552 + 15)
    _ruteado(monkeypatch, [("cog.tif", _por_rango(buf))])
    rec = mf.leer_recorte_cog("https://x/cog.tif", 25.78, -100.19)
    assert rec["epsg"] == 32614
    assert rec["pixel"] == [1, 2]
    assert rec["px_validos"] == 4
    assert rec["mediana_dn"] == 250


def test_recorte_s2_viva_con_ndvi_y_sin_escena_es_muerta(monkeypatch):
    buf = _geotiff_de_mosaicos(380681.258 - 25, 2851859.552 + 15)
    banda = {"raster:bands": [{"scale": 0.0001, "offset": -0.1}]}
    escena = {"features": [{"id": "S2X", "properties": {"datetime": "2026-09-15", "eo:cloud_cover": 0.5},
                            "assets": {"red": {"href": "https://x/B04.tif", **banda},
                                       "nir": {"href": "https://x/B08.tif", **banda}}}]}
    _ruteado(monkeypatch, [("/search", {"status": 200, "cuerpo": json.dumps(escena).encode()}),
                           (".tif", _por_rango(buf))])
    res = mf.stac_earthsearch_s2_recorte(25.78, -100.19)
    assert res["veredicto"] == "VIVA"
    assert res["valor"]["ndvi_de_medianas"] == 0.0  # mismas bandas → NDVI 0
    _ruteado(monkeypatch, [("/search", {"status": 200, "cuerpo": b'{"features": []}'})])
    assert mf.stac_earthsearch_s2_recorte(25.78, -100.19)["veredicto"] == "MUERTA"


def test_s1_planetary_no_publica_la_firma_sas(monkeypatch):
    buf = _geotiff_de_mosaicos(0.0, 0.0)
    href = "https://acct.blob.core.windows.net/c/iw-vv.rtc.tiff"
    escena = {"features": [{"id": "S1D_rtc", "properties": {"datetime": "2026-10-10T00:41:48Z"},
                            "assets": {"vv": {"href": href}}}]}
    firmado = href + "?st=2026&se=2026&sig=FIRMA-SECRETA-789"

    def blob(url, cab):
        if "sig=" not in url:
            return mf.Respuesta(url, 409, b"PublicAccessNotPermitted", 0.1)
        return _por_rango(buf)(url, cab)
    _ruteado(monkeypatch, [("/api/sas/v1/sign", {"status": 200, "cuerpo": json.dumps({"href": firmado}).encode()}),
                           ("/search", {"status": 200, "cuerpo": json.dumps(escena).encode()}),
                           ("iw-vv.rtc.tiff", blob)])
    res = mf.stac_planetary_s1(25.78, -100.19)
    assert res["veredicto"] == "VIVA"
    assert res["valor"]["http_sin_firma"] == 409 and res["valor"]["http_con_firma"] == 206
    assert "FIRMA-SECRETA-789" not in json.dumps(res)


CBP_FEED = [
    {"port_number": "230404", "border": "Mexican Border", "date": "10/12/2026", "time": "20:12:20",
     "commercial_vehicle_lanes": {"maximum_lanes": "19",
                                  "standard_lanes": {"update_time": "At 7:00 pm CDT", "operational_status": "delay",
                                                     "delay_minutes": "45", "lanes_open": "10"},
                                  "FAST_lanes": {"operational_status": "delay", "delay_minutes": "15"}}},
    {"port_number": "250602", "border": "Mexican Border", "date": "10/12/2026", "time": "18:12:20",
     "commercial_vehicle_lanes": {"maximum_lanes": "10",
                                  "standard_lanes": {"operational_status": "Lanes Closed", "delay_minutes": ""},
                                  "FAST_lanes": {"operational_status": "Lanes Closed"}}},
]


def test_cbp_carril_comercial_y_carriles_cerrados_no_es_hueco(monkeypatch):
    _ruteado(monkeypatch, [
        ("historicalwaittimes", {"status": 200, "cuerpo": b'{"wait_times": [{"bwt_day": "0"}]}'}),
        ("bwtnew", {"status": 200, "cuerpo": json.dumps(CBP_FEED).encode()}),
    ])
    res = mf.cbp_bwt(25.78, -100.19)
    assert res["veredicto"] == "VIVA"
    assert res["valor"]["cruces"]["Laredo – World Trade Bridge"]["demora_min"] == "45"
    assert res["valor"]["cruces"]["Otay Mesa – Commercial"]["estado"] == "Lanes Closed"
    # Un feed que responde sin esos cruces no es dato.
    _ruteado(monkeypatch, [("bwtnew", {"status": 200, "cuerpo": b"[]"})])
    assert mf.cbp_bwt(25.78, -100.19)["veredicto"] == "MUERTA"


def test_compras_403_y_captcha_son_muertas_sin_respuesta_no_concluye(monkeypatch):
    _fijo(monkeypatch, {"status": 403, "cuerpo": b'{"success":false,"error":"Acceso no permitido."}'})
    assert mf.comprasmx(25.78, -100.19)["veredicto"] == "MUERTA"
    # La PNT con captcha: aunque contestara 200, no es dato.
    _fijo(monkeypatch, {"status": 200, "cuerpo": b"<html>por favor ayudanos a solucionar el siguiente captcha</html>"})
    assert mf.pnt(25.78, -100.19)["veredicto"] == "MUERTA"
    _fijo(monkeypatch, {"status": None, "error": "URLError: reset"})
    for sonda in (mf.comprasmx, mf.pnt, mf.ocds_nuevo_leon, mf.obra_smpu_nl, mf.cbp_bwt, mf.firms_csv_publico):
        assert sonda(25.78, -100.19)["veredicto"] == "NO CONCLUYE", sonda.__name__


def test_ocds_nl_cuenta_proveedores_y_html_con_200_es_muerta(monkeypatch):
    rel = [{"date": "2026-01-13T11:45:54Z", "tender": {"procurementMethod": "direct"},
            "awards": [{"value": {"amount": 4925.36}, "suppliers": [{"id": "MX-RFC-XAXX010101000"}]}]},
           {"date": "2026-09-11T18:28:07Z", "tender": {"procurementMethod": "open"}, "awards": []}]
    cuerpo = gzip.compress("\n".join(json.dumps(x) for x in rel).encode())
    _fijo(monkeypatch, {"status": 200, "cuerpo": cuerpo})
    res = mf.ocds_nuevo_leon(25.78, -100.19)
    assert res["veredicto"] == "VIVA"
    assert res["valor"]["releases"] == 2 and res["valor"]["con_proveedor"] == 1
    assert res["valor"]["fecha_max"] == "2026-09-11T18:28:07Z"
    _fijo(monkeypatch, {"status": 200, "cuerpo": PAGINA_WAF})
    assert mf.ocds_nuevo_leon(25.78, -100.19)["veredicto"] == "MUERTA"


def test_firms_csv_publico_cuenta_focos_cerca_y_no_usa_la_clave(monkeypatch):
    monkeypatch.setenv("FIRMS_MAP_KEY", "clave-secreta-123")
    csv_ = (b"latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version\n"
            b"25.80,-100.20,330,0.4,0.4,2026-10-12,1711,N20,n,2.0NRT\n"
            b"20.95,-101.43,330,0.4,0.4,2026-10-12,0905,N20,n,2.0NRT\n")
    _fijo(monkeypatch, {"status": 200, "cuerpo": csv_})
    res = mf.firms_csv_publico(25.78, -100.19)
    assert res["veredicto"] == "VIVA"
    assert res["valor"]["focos_region_24h"] == 2 and res["valor"]["focos_a_50km"] == 1
    assert res["valor"]["adquisicion_mas_reciente_utc"] == "2026-10-12 1711"
    assert "clave-secreta-123" not in json.dumps(res)
    _fijo(monkeypatch, {"status": 200, "cuerpo": PAGINA_WAF})
    assert mf.firms_csv_publico(25.78, -100.19)["veredicto"] == "MUERTA"
