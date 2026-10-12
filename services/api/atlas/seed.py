"""Puntos candidatos públicos. El municipio lo pone INEGI en la consulta, no este archivo."""

SITES = [
    {
        "id": "apodaca-industrial",
        "name": "Apodaca, corredor industrial",
        "corridor": "norte",
        "lat": 25.7789,
        "lon": -100.1886,
        "note": "Punto candidato en el oriente del área metropolitana de Monterrey.",
    },
    {
        "id": "pesqueria-kia",
        "name": "Pesquería, corredor KIA",
        "corridor": "norte",
        "lat": 25.7835,
        "lon": -100.0005,
        "note": "Punto candidato sobre el corredor de Pesquería.",
    },
    {
        "id": "salinas-hofusan",
        "name": "Salinas Victoria, norte",
        "corridor": "norte",
        "lat": 25.8690,
        "lon": -100.2140,
        "note": "Punto candidato hacia el norte del área metropolitana.",
    },
    {
        "id": "garcia-poniente",
        "name": "García, poniente",
        "corridor": "norte",
        "lat": 25.8010,
        "lon": -100.5720,
        "note": "Punto candidato en el poniente metropolitano.",
    },
    {
        "id": "ramos-arizpe",
        "name": "Ramos Arizpe",
        "corridor": "norte",
        "lat": 25.5450,
        "lon": -100.9500,
        "note": "Punto candidato en el corredor Saltillo–Ramos Arizpe.",
    },
    {
        "id": "puerto-interior",
        "name": "Puerto Interior, Silao",
        "corridor": "bajio",
        "lat": 20.9665,
        "lon": -101.4690,
        "note": "Punto candidato en el clúster del Puerto Interior.",
    },
    {
        "id": "el-marques",
        "name": "El Marqués, Querétaro",
        "corridor": "bajio",
        "lat": 20.5950,
        "lon": -100.3120,
        "note": "Punto candidato en el corredor aeropuerto de Querétaro.",
    },
    {
        "id": "celaya",
        "name": "Celaya, corredor industrial",
        "corridor": "bajio",
        "lat": 20.5560,
        "lon": -100.8400,
        "note": "Punto candidato en Celaya.",
    },
    {
        "id": "slp-industrial",
        "name": "San Luis Potosí, zona industrial",
        "corridor": "bajio",
        "lat": 22.1400,
        "lon": -100.9320,
        "note": "Punto candidato al sur de la ciudad de San Luis Potosí.",
    },
    {
        "id": "leon-sur",
        "name": "León, sur",
        "corridor": "bajio",
        "lat": 21.0800,
        "lon": -101.6500,
        "note": "Punto candidato al sur de León.",
    },
]

CORRIDORS = {
    "norte": {
        "id": "norte",
        "name": "Norte industrial",
        "summary": "Monterrey, su anillo y Ramos Arizpe.",
    },
    "bajio": {
        "id": "bajio",
        "name": "Bajío",
        "summary": "Querétaro, Guanajuato y San Luis Potosí.",
    },
}
