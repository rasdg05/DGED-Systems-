"""Ojo satelital: umbral, área mínima, nubes, hectáreas y citas. Sin red.

Los arreglos son sintéticos con espectros típicos de Sentinel-2 L2A
(reflectancia de superficie): vegetación, suelo desnudo y techo metálico.
"""

import numpy as np
import pytest
from satelite import indices as ix
from satelite.indices import Bandas, clasificar, disco, filtrar_por_area, nubosidad
from satelite.render import dibujar
from satelite.resultado import Escena, assert_citado, construir, motivo_para_no_concluir

N = 60  # píxeles por lado del recorte sintético (600 m)

#            blue  green red   nir   swir16
VEGETACION = (0.03, 0.06, 0.04, 0.35, 0.18)
SUELO = (0.10, 0.14, 0.18, 0.24, 0.32)
TECHO = (0.35, 0.37, 0.38, 0.40, 0.30)
SUELO_MOJADO = (0.09, 0.125, 0.16, 0.215, 0.29)  # mismo suelo, 10% más oscuro


def _escena(fondo, parches=(), scl=4):
    """Bandas uniformes con `parches` [(rebanada_fila, rebanada_col, espectro)]."""
    capas = [np.full((N, N), v, np.float32) for v in fondo]
    for fs, cs, espectro in parches:
        for capa, v in zip(capas, espectro, strict=True):
            capa[fs, cs] = v
    s = np.full((N, N), scl, np.uint8)
    return Bandas(blue=capas[0], green=capas[1], red=capas[2], nir=capas[3], swir16=capas[4], scl=s)


def _esc(id_="S2X_TEST_A", nub=0.0, fecha="2024-01-15T17:00:00Z"):
    return Escena(id=id_, fecha=fecha, nubosidad_recorte=nub, nubosidad_escena=1.0,
                  mosaico="14RLP", epsg=32614, fuente="sintetico")


def _cambio(antes, despues, region=None):
    return filtrar_por_area(clasificar(antes, despues, region))


def _construir(antes, despues, cambio, va=("2024-01-01", "2024-03-31"), vd=("2026-01-01", "2026-03-31")):
    return construir(lat=25.0, lon=-100.0, radio_m=300, ventana_antes=va, ventana_despues=vd,
                     antes=antes, despues=despues, cambio=cambio)


# --- Índices --------------------------------------------------------------

def test_reflectancia_aplica_escala_offset_y_nodata():
    r = ix.reflectancia(np.array([0, 1000, 3000], np.uint16), 0.0001, -0.1)
    assert np.isnan(r[0])
    assert r[1] == pytest.approx(0.0, abs=1e-6)
    assert r[2] == pytest.approx(0.2, abs=1e-6)


def test_indices_de_espectros_tipicos():
    b = _escena(VEGETACION).indices()
    assert b["ndvi"][0, 0] > 0.7 and b["bsi"][0, 0] < 0
    s = _escena(SUELO).indices()
    assert s["ndvi"][0, 0] < ix.NDVI_NO_VEGETACION and s["bsi"][0, 0] > 0


# --- Umbral ---------------------------------------------------------------

def test_desmonte_se_detecta_como_vegetacion_a_suelo():
    antes = _escena(VEGETACION)
    despues = _escena(VEGETACION, [(slice(10, 20), slice(10, 20), SUELO)])
    c = _cambio(antes, despues)
    assert [z.tipo for z in c.zonas] == ["vegetacion_a_suelo"]
    assert c.hectareas() == pytest.approx(1.0)


def test_caida_de_ndvi_bajo_el_umbral_no_es_cambio():
    # NDVI 0.79 → ~0.62 (caída ~0.17 < 0.20): vegetación más seca, no desmonte.
    seca = (0.03, 0.06, 0.06, 0.26, 0.18)
    antes = _escena(VEGETACION)
    despues = _escena(VEGETACION, [(slice(0, 20), slice(0, 20), seca)])
    a, d = antes.indices()["ndvi"][0, 0], despues.indices()["ndvi"][0, 0]
    assert ix.DELTA_NDVI_PERDIDA < d - a < 0
    assert _cambio(antes, despues).zonas == []


def test_suelo_que_se_vuelve_techo_es_construido():
    antes = _escena(SUELO)
    despues = _escena(SUELO, [(slice(5, 25), slice(5, 15), TECHO)])
    c = _cambio(antes, despues)
    assert [z.tipo for z in c.zonas] == ["suelo_a_construido"]
    assert c.hectareas("suelo_a_construido") == pytest.approx(2.0)


def test_suelo_mojado_no_pasa_por_techo():
    antes = _escena(SUELO)
    despues = _escena(SUELO_MOJADO)
    assert _cambio(antes, despues).zonas == []


def test_reverdecimiento_se_reporta_aparte_y_no_es_obra():
    antes = _escena(SUELO)
    despues = _escena(SUELO, [(slice(0, 10), slice(0, 10), VEGETACION)])
    c = _cambio(antes, despues)
    r = _construir(_esc("A"), _esc("B"), c)
    assert r["hectareas_por_tipo"]["reverdecimiento"] == pytest.approx(1.0)
    assert r["hectareas_posible_obra"] == 0


# --- Área mínima ----------------------------------------------------------

def test_area_minima_descarta_manchas_chicas():
    assert ix.AREA_MINIMA_PX == 50
    antes = _escena(VEGETACION)
    chica = _escena(VEGETACION, [(slice(0, 7), slice(0, 7), SUELO)])  # 49 px
    justa = _escena(VEGETACION, [(slice(0, 5), slice(0, 10), SUELO)])  # 50 px
    assert _cambio(antes, chica).zonas == []
    assert _cambio(antes, justa).hectareas() == pytest.approx(0.5)


def test_pixeles_sueltos_no_suman_aunque_en_total_pasen_el_area():
    antes = _escena(VEGETACION)
    tablero = [(slice(f, f + 1), slice(c, c + 1), SUELO) for f in range(0, N, 2) for c in range(0, N, 2)]
    despues = _escena(VEGETACION, tablero)  # 900 px de cambio, ninguno conectado
    assert (clasificar(antes, despues) == 1).sum() == 900
    assert _cambio(antes, despues).zonas == []


# --- Hectáreas ------------------------------------------------------------

def test_hectareas_son_pixeles_por_cero_punto_cero_uno():
    antes = _escena(VEGETACION)
    despues = _escena(VEGETACION, [(slice(0, 30), slice(0, 20), SUELO), (slice(40, 50), slice(40, 60), TECHO)])
    c = _cambio(antes, despues)
    assert sorted(z.pixeles for z in c.zonas) == [200, 600]
    assert c.hectareas() == pytest.approx(8.0)
    assert ix.HA_POR_PIXEL_10M == 0.01


def test_el_cambio_solo_cuenta_dentro_del_disco():
    antes = _escena(VEGETACION)
    despues = _escena(VEGETACION, [(slice(0, 10), slice(0, 10), SUELO)])  # esquina: fuera del círculo
    assert _cambio(antes, despues, disco(N, N)).zonas == []


# --- Nubes → no concluye --------------------------------------------------

def test_pixel_nublado_en_cualquier_fecha_nunca_cambia():
    antes = _escena(VEGETACION)
    despues = _escena(VEGETACION, [(slice(0, 20), slice(0, 20), SUELO)])
    despues.scl[0:20, 0:20] = 9  # nube alta justo donde "cambió"
    assert (clasificar(antes, despues) != 0).sum() == 0


def test_nubosidad_del_recorte_usa_scl_y_cuenta_sin_dato():
    scl = np.full((N, N), 4, np.uint8)
    scl[:, : N // 2] = 0  # media escena sin dato (fuera de la órbita)
    assert nubosidad(scl) == pytest.approx(0.5)
    for clase in ix.SCL_INVALIDAS:
        assert nubosidad(np.full((4, 4), clase, np.uint8)) == 1.0
    for clase in (2, 4, 5, 6, 7):
        assert nubosidad(np.full((4, 4), clase, np.uint8)) == 0.0


def test_recorte_nublado_no_concluye_y_no_da_hectareas():
    antes = _escena(VEGETACION)
    despues = _escena(VEGETACION, [(slice(0, 30), slice(0, 30), SUELO)])
    c = _cambio(antes, despues)
    assert c.hectareas() > 0  # el cálculo SÍ vería cambio...
    r = _construir(_esc("A", 0.0), _esc("B", ix.NUBOSIDAD_MAXIMA + 0.01), c)
    assert r["estado"] == "no_concluye"  # ...pero con nubes no se afirma
    assert r["hectareas_cambiadas"] is None and r["hectareas_posible_obra"] is None
    assert r["zonas"] == []
    assert "nubosidad" in r["motivo"]
    assert r["escenas_citadas"] == ["A", "B"]  # lo que se miró se cita igual


def test_nubosidad_justo_en_el_umbral_si_concluye():
    assert motivo_para_no_concluir(_esc("A", ix.NUBOSIDAD_MAXIMA), _esc("B", 0.0)) is None


# --- Nunca un cambio sin escenas citadas -----------------------------------

@pytest.mark.parametrize("faltante", ["antes", "despues", "las_dos"])
def test_sin_escena_no_concluye(faltante):
    c = _cambio(_escena(VEGETACION), _escena(SUELO))
    a = None if faltante in ("antes", "las_dos") else _esc("A")
    d = None if faltante in ("despues", "las_dos") else _esc("B")
    r = _construir(a, d, c)
    assert r["estado"] == "no_concluye"
    assert r["hectareas_cambiadas"] is None
    assert "sin escena" in r["motivo"]


def test_concluye_cita_las_dos_escenas_con_fecha():
    c = _cambio(_escena(VEGETACION), _escena(VEGETACION, [(slice(0, 10), slice(0, 10), SUELO)]))
    r = _construir(_esc("S2B_14RLP_20240119_0_L2A"), _esc("S2A_14RLP_20260813_0_L2A", fecha="2026-08-13T17:27:02Z"), c)
    assert r["estado"] == "concluye"
    assert r["escenas_citadas"] == ["S2B_14RLP_20240119_0_L2A", "S2A_14RLP_20260813_0_L2A"]
    assert r["antes"]["fecha"] and r["despues"]["fecha"]
    assert r["umbrales"]["area_minima_ha"] == 0.5


def test_assert_citado_rechaza_hectareas_sin_escena():
    falso = {"hectareas_cambiadas": 3.0, "antes": {"id": "A", "fecha": "2024"}, "despues": None,
             "escenas_citadas": ["A"]}
    with pytest.raises(ValueError):
        assert_citado(falso)
    assert_citado({"hectareas_cambiadas": None, "antes": None, "despues": None, "escenas_citadas": []})


# --- Avisos y dibujo ------------------------------------------------------

def test_ventanas_de_distinta_estacion_llevan_aviso():
    c = _cambio(_escena(VEGETACION), _escena(VEGETACION))
    misma = _construir(_esc("A"), _esc("B"), c)
    distinta = _construir(_esc("A"), _esc("B"), c, vd=("2026-07-01", "2026-09-30"))
    assert misma["avisos"] == []
    assert any("estación" in a for a in distinta["avisos"])


def test_png_se_dibuja_sin_red(tmp_path):
    antes = _escena(VEGETACION)
    despues = _escena(VEGETACION, [(slice(20, 40), slice(20, 40), SUELO)])
    c = _cambio(antes, despues, disco(N, N))
    ruta = dibujar(antes, despues, c.mapa, ("antes", "despues", "cambio"), str(tmp_path / "x.png"))
    from PIL import Image

    with Image.open(ruta) as im:
        assert im.width > 3 * N and im.mode == "RGB"
    # Y sin escenas también se dibuja (paneles vacíos), sin inventar nada.
    dibujar(None, None, None, ("a", "b", "NO CONCLUYE"), str(tmp_path / "y.png"))
