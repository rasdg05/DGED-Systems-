"""Cribado en vivo atlas-live-0.1.0.

Tres variables que sí salen de fuentes públicas:
sequía municipal (SMN/CONAGUA), inundación (INEGI WMS) y uso de suelo (INEGI WMS).
DENUE entra solo con token y no se inventa si falta.
"""

MODEL_VERSION = "atlas-live-0.1.0"

DROUGHT_SCORE = {
    "NONE": 92,
    "D0": 78,
    "D1": 62,
    "D2": 46,
    "D3": 28,
    "D4": 12,
}
DROUGHT_RANK = ["NONE", "D0", "D1", "D2", "D3", "D4"]


def normalize_drought(value):
    if value is None:
        return None
    text = str(value).strip().upper().replace("Í", "I")
    if text in ("", "S", "SIN SEQUIA", "SIN SEQUÍA", "NONE", "NS"):
        return "NONE"
    if text in DROUGHT_SCORE:
        return text
    return None


def apply_drought_scenario(category, drought_year):
    if not drought_year or category is None:
        return category
    if DROUGHT_RANK.index(category) < DROUGHT_RANK.index("D2"):
        return "D2"
    return category


def land_score(name):
    if not name:
        return None
    text = name.upper()
    if "INDUSTR" in text:
        return 88
    if "ASENTAMIENTO" in text or "URBAN" in text:
        return 70
    if "AGRIC" in text or "PASTIZ" in text or "RIEGO" in text:
        return 52
    if any(token in text for token in ("BOSQUE", "SELVA", "MANGL", "CUERPO DE AGUA", "AGUA", "DESPROVISTO")):
        return 34
    return 48


def establishment_score(count):
    if count is None:
        return None
    if count <= 0:
        return 30
    if count <= 5:
        return 55
    if count <= 20:
        return 75
    return 90


def route_score(minutes):
    if minutes is None:
        return None
    if minutes <= 45:
        return 88
    if minutes <= 90:
        return 72
    if minutes <= 150:
        return 54
    if minutes <= 240:
        return 36
    return 20


def _round1(value):
    return round(value * 10) / 10


def _weights(has_denue, has_route):
    if has_denue and has_route:
        return {"drought": 0.28, "flood": 0.20, "land": 0.16, "establishments": 0.18, "logistics": 0.18}
    if has_denue:
        return {"drought": 0.34, "flood": 0.24, "land": 0.18, "establishments": 0.24}
    if has_route:
        return {"drought": 0.32, "flood": 0.24, "land": 0.22, "logistics": 0.22}
    return {"drought": 0.40, "flood": 0.30, "land": 0.30}


def score_observation(observation, drought_year=False):
    """observation keys: drought, flood_hit, flood_known, land_name, land_known, denue_count."""
    category = normalize_drought(observation.get("drought"))
    used = apply_drought_scenario(category, drought_year)
    factors = []

    if used is None:
        factors.append({
            "key": "drought",
            "label": "Sequía municipal",
            "score": None,
            "missing": True,
            "raw": None,
            "caveats": ["Sin corte del monitor de sequía para el municipio que devolvió INEGI."],
        })
    else:
        factors.append({
            "key": "drought",
            "label": "Sequía municipal",
            "score": DROUGHT_SCORE[used],
            "missing": False,
            "raw": {
                "observed": category,
                "used": used,
                "asOf": observation.get("drought_as_of"),
                "municipality": observation.get("municipality"),
                "cvegeo": observation.get("cvegeo"),
            },
            "caveats": [
                "Monitor de Sequía de México, resolución municipal. No es el balance hídrico del predio ni una concesión.",
            ],
        })

    if not observation.get("flood_known"):
        factors.append({
            "key": "flood",
            "label": "Inundación",
            "score": None,
            "missing": True,
            "raw": None,
            "caveats": ["INEGI no respondió la consulta de la capa de inundación."],
        })
    else:
        hit = bool(observation.get("flood_hit"))
        factors.append({
            "key": "flood",
            "label": "Inundación",
            "score": 22 if hit else 84,
            "missing": False,
            "raw": {"hit": hit, "layer": observation.get("flood_layer")},
            "caveats": [
                "Cruce del punto con la capa de inundación del acervo INEGI (WMS). No es tirante, periodo de retorno ni pérdida esperada.",
            ],
        })

    land = land_score(observation.get("land_name")) if observation.get("land_known") else None
    if land is None:
        factors.append({
            "key": "land",
            "label": "Uso de suelo",
            "score": None,
            "missing": True,
            "raw": None,
            "caveats": ["Sin clase de uso de suelo serie VII en el punto."],
        })
    else:
        factors.append({
            "key": "land",
            "label": "Uso de suelo",
            "score": land,
            "missing": False,
            "raw": {"class": observation.get("land_name")},
            "caveats": [
                "Uso de suelo y vegetación serie VII en el punto. Una clase regional no describe el lote ni la factibilidad de cambio de uso.",
            ],
        })

    denue = observation.get("denue_count")
    denue_score = establishment_score(denue)
    sample = observation.get("denue_sample") or []
    if denue_score is None:
        factors.append({
            "key": "establishments",
            "label": "Establecimientos",
            "score": None,
            "missing": True,
            "raw": {
                "mode": observation.get("denue_mode") or "ausente",
                "reason": observation.get("denue_reason"),
                "window": [
                    {"name": row.get("name"), "activity": row.get("activity"), "staff": row.get("staff")}
                    for row in sample[:5]
                ],
            },
            "caveats": [
                "La muestra de la ventana no es un conteo en 1.5 km, así que no entra al número. El conteo sigue esperando INEGI_TOKEN.",
            ],
        })
    else:
        factors.append({
            "key": "establishments",
            "label": "Establecimientos",
            "score": denue_score,
            "missing": False,
            "raw": {"manufacturingWithinM": denue, "radiusM": observation.get("denue_radius_m") or 1500},
            "caveats": [
                "Conteo DENUE de la búsqueda en el radio. Densidad no es oficio disponible ni salario.",
            ],
        })

    minutes = observation.get("route_minutes")
    logistics = route_score(minutes)
    if logistics is None:
        factors.append({
            "key": "logistics",
            "label": "Ruta",
            "score": None,
            "missing": True,
            "raw": {"reason": observation.get("route_reason") or "SAKBE_TOKEN ausente", "reference": observation.get("route_reference")},
            "caveats": [
                "SAKBÉ calcula minutos sobre la Red Nacional de Caminos. Sin SAKBE_TOKEN este factor no entra al número.",
            ],
        })
    else:
        factors.append({
            "key": "logistics",
            "label": "Ruta",
            "score": logistics,
            "missing": False,
            "raw": {
                "minutes": minutes,
                "kilometers": observation.get("route_kilometers"),
                "reference": observation.get("route_reference"),
                "vehicle": observation.get("route_vehicle") or "automóvil",
            },
            "caveats": [
                "Minutos de la ruta sugerida entre la línea de red más cercana al punto y la del sitio de referencia. No es el tiempo de un tractocamión ni del portón del predio.",
            ],
        })

    weights = _weights(denue_score is not None, logistics is not None)

    present = 0.0
    acc = 0.0
    total = sum(weights.values())
    by_key = {factor["key"]: factor for factor in factors}
    for key, weight in weights.items():
        factor = by_key[key]
        if factor["score"] is None:
            continue
        present += weight
        acc += weight * factor["score"]
    composite = _round1(acc / present) if present else None
    coverage = _round1(present / total) if total else 0
    publishable = (
        composite is not None
        and by_key["drought"]["score"] is not None
        and by_key["flood"]["score"] is not None
        and by_key["land"]["score"] is not None
    )
    return {
        "modelVersion": MODEL_VERSION,
        "composite": composite,
        "risk": _round1(100 - composite) if composite is not None else None,
        "coverage": coverage,
        "publishable": publishable,
        "factors": factors,
        "weights": weights,
        "scenario": {"droughtYear": bool(drought_year)},
    }
