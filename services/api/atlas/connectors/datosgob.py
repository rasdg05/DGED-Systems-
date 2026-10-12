from atlas.connectors.http import fetch

SEARCH = "https://datos.gob.mx/api/3/action/package_search?q=acuiferos&rows=3"


def probe():
    result = fetch(SEARCH, timeout=15)
    text = result["body"][:240].decode("utf-8", "replace")
    return {
        "source": "datos.gob.mx",
        "url": SEARCH,
        "ok": result["ok"] and text.lstrip().startswith("{"),
        "status": result["status"],
        "error": result.get("error"),
        "excerpt": text,
        "note": (
            "El portal respondió JSON."
            if result["ok"] and text.lstrip().startswith("{")
            else "datos.gob.mx no entregó el API CKAN desde esta red (bloqueo o caída). No se sustituye con un mock."
        ),
    }
