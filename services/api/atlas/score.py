"""Cribado en vivo atlas-live-0.2.0.

Tres variables que sí salen de fuentes públicas y deciden si se publica:
sequía municipal (SMN/CONAGUA), inundación (INEGI WMS) y uso de suelo (INEGI WMS).
DENUE y SAKBÉ entran solo con token. Desde 0.2.0 (D-009) entran también, solo si
respondieron, la sismicidad registrada (USGS FDSN) y la distancia a vía férrea
(OSM Overpass). Sin su respuesta los pesos son exactamente los de 0.1.0.
El clima (NASA POWER) y la subestación (OSM) se muestran y no puntúan.
"""

MODEL_VERSION = "atlas-live-0.2.0"

# D-009: pesos fijos de las capas nuevas. El resto se escala por (1 - suma).
EXTRA_WEIGHTS = {"seismic": 0.08, "rail": 0.10}

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


def seismic_score(max_magnitude, known):
    """Magnitud máxima registrada en 100 km y 50 años. Sin respuesta: None."""
    if not known:
        return None
    if max_magnitude is None:
        return 90
    if max_magnitude < 4.5:
        return 82
    if max_magnitude < 5.0:
        return 76
    if max_magnitude < 5.5:
        return 62
    if max_magnitude < 6.0:
        return 46
    if max_magnitude < 6.5:
        return 30
    return 16


def rail_score(distance_km, known):
    """Km a la vía férrea mapeada más cercana. `known` con distancia None = nada en 10 km."""
    if not known:
        return None
    if distance_km is None:
        return 36
    if distance_km <= 2:
        return 88
    if distance_km <= 5:
        return 74
    return 56


def _round1(value):
    return round(value * 10) / 10


def _base_weights(has_denue, has_route):
    if has_denue and has_route:
        return {"drought": 0.28, "flood": 0.20, "land": 0.16, "establishments": 0.18, "logistics": 0.18}
    if has_denue:
        return {"drought": 0.34, "flood": 0.24, "land": 0.18, "establishments": 0.24}
    if has_route:
        return {"drought": 0.32, "flood": 0.24, "land": 0.22, "logistics": 0.22}
    return {"drought": 0.40, "flood": 0.30, "land": 0.30}


def _weights(has_denue, has_route, has_seismic=False, has_rail=False):
    base = _base_weights(has_denue, has_route)
    extra = {}
    if has_seismic:
        extra["seismic"] = EXTRA_WEIGHTS["seismic"]
    if has_rail:
        extra["rail"] = EXTRA_WEIGHTS["rail"]
    if not extra:
        return base
    scale = 1 - sum(extra.values())
    weights = {key: round(value * scale, 4) for key, value in base.items()}
    weights.update(extra)
    return weights


def score_observation(observation, drought_year=False):
    """observation keys: drought, flood_hit, flood_known, land_name, land_known, denue_count,
    route_minutes, seismic_known, seismic_max_magnitude, rail_known, rail_distance_km."""
    category = normalize_drought(observation.get("drought"))
    used = apply_drought_scenario(category, drought_year)
    factors = []

    if used is None:
        factors.append({
            "key": "drought",
            "label": "Sequía municipal",
            "score": None,
            "missing": True,
            "raw": {"reason": observation.get("drought_reason")} if observation.get("drought_reason") else None,
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

    seismic = seismic_score(observation.get("seismic_max_magnitude"), observation.get("seismic_known"))
    if seismic is None:
        factors.append({
            "key": "seismic",
            "label": "Sismicidad",
            "score": None,
            "missing": True,
            "raw": {"reason": observation.get("seismic_reason") or "USGS no respondió"},
            "caveats": ["Sin respuesta del catálogo FDSN de USGS: el factor no entra al número."],
        })
    else:
        factors.append({
            "key": "seismic",
            "label": "Sismicidad",
            "score": seismic,
            "missing": False,
            "raw": {
                "count": observation.get("seismic_count"),
                "maxMagnitude": observation.get("seismic_max_magnitude"),
                "strongest": observation.get("seismic_strongest"),
                "radiusKm": observation.get("seismic_radius_km") or 100,
                "years": observation.get("seismic_years") or 50,
            },
            "caveats": [
                "Sismos M4 o más registrados por USGS en 100 km y 50 años. No es la regionalización sísmica de CFE ni un espectro de diseño; antes de los noventa el catálogo de M4 en México está incompleto.",
            ],
        })

    rail = rail_score(observation.get("rail_distance_km"), observation.get("rail_known"))
    if rail is None:
        factors.append({
            "key": "rail",
            "label": "Vía férrea",
            "score": None,
            "missing": True,
            "raw": {"reason": observation.get("rail_reason") or "Overpass no respondió"},
            "caveats": ["Sin respuesta de Overpass: el factor no entra al número."],
        })
    else:
        factors.append({
            "key": "rail",
            "label": "Vía férrea",
            "score": rail,
            "missing": False,
            "raw": {
                "distanceKm": observation.get("rail_distance_km"),
                "withinKm": observation.get("rail_radius_km") or 10,
                "name": observation.get("rail_name"),
                "operator": observation.get("rail_operator"),
                "service": observation.get("rail_service"),
            },
            "caveats": [
                "Distancia en línea recta a la vía mapeada en OpenStreetMap (railway=rail), que puede estar incompleto. No es un ramal concesionado al predio ni una tarifa de carga.",
            ],
        })

    weights = _weights(
        denue_score is not None,
        logistics is not None,
        seismic is not None,
        rail is not None,
    )

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
