import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from atlas.score import score_observation


def test_three_live_factors_publish():
    result = score_observation({
        "drought": "D0",
        "drought_as_of": "2026-09-30",
        "municipality": "Monterrey",
        "cvegeo": "19039",
        "flood_hit": False,
        "flood_known": True,
        "flood_layer": "c463",
        "land_known": True,
        "land_name": "ASENTAMIENTOS HUMANOS",
        "denue_count": None,
    })
    assert result["publishable"] is True
    assert result["factors"][0]["score"] == 78
    assert result["factors"][1]["score"] == 84
    assert result["factors"][2]["score"] == 70
    assert result["composite"] == round((78 * 0.4 + 84 * 0.3 + 70 * 0.3) * 10) / 10
    assert "concesión" in result["factors"][0]["caveats"][0]


def test_drought_year_floors_at_d2():
    base = score_observation({
        "drought": "D0",
        "flood_hit": False,
        "flood_known": True,
        "land_known": True,
        "land_name": "ZONA INDUSTRIAL",
    })
    dry = score_observation({
        "drought": "D0",
        "flood_hit": False,
        "flood_known": True,
        "land_known": True,
        "land_name": "ZONA INDUSTRIAL",
    }, drought_year=True)
    assert dry["factors"][0]["raw"]["used"] == "D2"
    assert dry["factors"][0]["score"] < base["factors"][0]["score"]
    assert dry["composite"] < base["composite"]


def test_missing_land_is_not_publishable():
    result = score_observation({
        "drought": "D1",
        "flood_hit": True,
        "flood_known": True,
        "land_known": False,
        "land_name": None,
    })
    assert result["publishable"] is False
    assert result["composite"] is not None


def test_denue_changes_weights():
    result = score_observation({
        "drought": "NONE",
        "flood_hit": False,
        "flood_known": True,
        "land_known": True,
        "land_name": "BOSQUE DE ENCINO",
        "denue_count": 0,
    })
    assert result["weights"]["establishments"] == 0.24
    assert result["publishable"] is True
    assert result["factors"][2]["score"] == 34


def test_municipality_html_ignores_the_banner_cell():
    from atlas.connectors.inegi import _td_cells, municipality_from_cells
    html = """
    <td colspan="5">Municipio/Delegación</td>
    <TD>999</TD><TD>19006</TD><TD>Apodaca</TD>
    """
    cvegeo, name = municipality_from_cells(_td_cells(html))
    assert cvegeo == "19006"
    assert name == "Apodaca"


def test_window_sample_does_not_change_the_number():
    base = score_observation({
        "drought": "D0",
        "flood_hit": False,
        "flood_known": True,
        "land_known": True,
        "land_name": "ASENTAMIENTOS HUMANOS",
    })
    window = score_observation({
        "drought": "D0",
        "flood_hit": False,
        "flood_known": True,
        "land_known": True,
        "land_name": "ASENTAMIENTOS HUMANOS",
        "denue_count": None,
        "denue_mode": "ventana",
        "denue_sample": [{"name": "EMPACADORA", "activity": "Congelación", "staff": "31 a 50 personas"}],
    })
    assert window["composite"] == base["composite"]
    assert window["weights"] == base["weights"]
    assert "no entra" in window["factors"][3]["caveats"][0]


def test_route_minutes_enter_only_when_present():
    slow = score_observation({
        "drought": "D0",
        "flood_hit": False,
        "flood_known": True,
        "land_known": True,
        "land_name": "ASENTAMIENTOS HUMANOS",
        "route_minutes": 200,
        "route_reference": "Puente Colombia",
    })
    fast = score_observation({
        "drought": "D0",
        "flood_hit": False,
        "flood_known": True,
        "land_known": True,
        "land_name": "ASENTAMIENTOS HUMANOS",
        "route_minutes": 30,
        "route_reference": "Puente Colombia",
    })
    assert "logistics" in fast["weights"]
    assert fast["composite"] > slow["composite"]


def test_point_in_polygon():
    from atlas.connectors.catgeo import contains
    square = {"type": "Polygon", "coordinates": [[[-100.2, 25.7], [-100.1, 25.7], [-100.1, 25.8], [-100.2, 25.8], [-100.2, 25.7]]]}
    assert contains(-100.15, 25.75, square) is True
    assert contains(-100.3, 25.75, square) is False


if __name__ == "__main__":
    test_three_live_factors_publish()
    test_drought_year_floors_at_d2()
    test_missing_land_is_not_publishable()
    test_denue_changes_weights()
    test_municipality_html_ignores_the_banner_cell()
    test_window_sample_does_not_change_the_number()
    test_route_minutes_enter_only_when_present()
    test_point_in_polygon()
    print("score ok")
