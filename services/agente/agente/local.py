"""El taller en local (D-027): se desarrolla sin gastar API; producción solo recibe y revisa.

    cd services/agente
    export AGENTE_URL=https://<servicio>.up.railway.app TENANT_INTERNAL_TOKEN=<llave maestra>
    python -m agente.local bajar finca-quinta          # historial + espejo a datos/espacios/
    python -m agente.local pendientes finca-quinta     # la vara, y lotes para el enjambre
    python -m agente.local validar finca-quinta ronda.json
    python -m agente.local subir finca-quinta ronda.json              # prueba en producción
    python -m agente.local subir finca-quinta ronda.json --de-verdad  # quedan por aprobar
    python -m agente.local proponer finca-quinta perfil.json [--de-verdad]
    python -m agente.local servidor finca-quinta       # el panel en local, con la copia

**La copia local nunca llama a la API**: `bajar` deja `tope_usd_mes` en 0 y el
espacio en sombra; `gasto.exigir_saldo` corta antes de cualquier llamada. Lo
que se redacta en local lo redacta el enjambre de Claude Code
(`.claude/skills/enjambre/SKILL.md`), que corre en la sesión de código.

Los datos bajados son de clientes finales: viven en `datos/espacios/` (fuera
de git, invariante 8) y no salen de la máquina. Solo stdlib + el paquete.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import historial, pendientes, perfil, rondas
from .espacio import Espacio

RAIZ_LOCAL = Path(__file__).resolve().parent.parent / "datos" / "espacios"
MENSAJES_POR_PLATICA = 40


def _espacio(cliente_id: str) -> Espacio:
    return Espacio(cliente_id, Path(os.environ.get("AGENTE_DATOS_LOCAL", "") or RAIZ_LOCAL))


def _pedir(metodo: str, ruta: str, cuerpo: dict | None = None, **params) -> bytes:
    base = os.environ.get("AGENTE_URL", "").strip().rstrip("/")
    llave = os.environ.get("TENANT_INTERNAL_TOKEN", "").strip()
    if not base or not llave:
        raise SystemExit("falta AGENTE_URL o TENANT_INTERNAL_TOKEN en el entorno")
    url = f"{base}{ruta}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    datos = json.dumps(cuerpo, ensure_ascii=False).encode() if cuerpo is not None else None
    pedido = urllib.request.Request(url, data=datos, method=metodo, headers={
        "X-Tenant-Key": llave, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(pedido, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as error:
        raise SystemExit(f"{metodo} {ruta}: HTTP {error.code} {error.read()[:400].decode(errors='replace')}") from error


def enmascarar(hilo: str) -> str:
    return f"…{hilo[-4:]}" if len(hilo) > 4 else hilo


# --------------------------------------------------------------------------- #
def bajar(cliente_id: str) -> dict:
    espacio = _espacio(cliente_id)
    crudo = _pedir("GET", f"/espacios/{cliente_id}/historial.jsonl")
    espejo = json.loads(_pedir("GET", f"/espacios/{cliente_id}/espejo.json"))
    espacio.carpeta.mkdir(parents=True, exist_ok=True)
    espacio.ruta(historial.ARCHIVO).write_bytes(crudo)
    espacio.escribir_json("alta.json", espejo.get("alta") or {})
    for n, version in (espejo.get("versiones") or {}).items():
        espacio.escribir_json(f"perfil/v{int(n):04d}.json", version)
    if espejo.get("activa"):
        espacio.escribir_json("perfil/activa.json", {"version": espejo["activa"]})
    for archivo, filas in (("salidas.jsonl", espejo.get("salidas")),
                           ("aprobaciones_salida.jsonl", espejo.get("aprobaciones_salida"))):
        espacio.ruta(archivo).write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in filas or []),
                                         encoding="utf-8")
    # La copia local no gasta: tope 0 y en sombra, pase lo que pase en el entorno.
    espacio.escribir_json("config.json", {"tope_usd_mes": 0, "encendido": "sombra",
                                          "bajado": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return {"mensajes": crudo.count(b"\n"), "versiones": len(espejo.get("versiones") or {}),
            "activa": espejo.get("activa"), "carpeta": str(espacio.carpeta)}


def lotes(cliente_id: str, por_lote: int = 10) -> tuple[dict, list[Path]]:
    """La vara sobre la copia local y, para cada `espera`, su plática completa en lotes."""
    espacio = _espacio(cliente_id)
    hilos = historial.hilos(espacio)
    lista = pendientes.leer(hilos)
    espera = [p for p in lista if p.estado == "espera"]
    carpeta = espacio.ruta(f"enjambre/{datetime.now(timezone.utc):%Y-%m-%dT%H%M}")
    carpeta.mkdir(parents=True, exist_ok=True)
    escritos = []
    for i in range(0, len(espera), por_lote):
        platicas = [{**p.a_dict(), "mensajes": [
            {"id": m.id, "de": "negocio" if m.del_negocio else "cliente", "ts": m.ts, "tipo": m.tipo, "texto": m.texto}
            for m in hilos[p.hilo][-MENSAJES_POR_PLATICA:]]} for p in espera[i:i + por_lote]]
        ruta = carpeta / f"lote-{i // por_lote + 1:02d}.json"
        ruta.write_text(json.dumps({"cliente_id": cliente_id, "perfil_activo": perfil.version_activa(espacio),
                                    "platicas": platicas}, ensure_ascii=False, indent=1), encoding="utf-8")
        escritos.append(ruta)
    return pendientes.resumen(lista), escritos


def _leer(ruta: str) -> dict:
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m agente.local", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="orden", required=True)
    for nombre in ("bajar", "pendientes", "servidor"):
        sub.add_parser(nombre).add_argument("cliente_id")
    sub.choices["pendientes"].add_argument("--por-lote", type=int, default=10)
    for nombre in ("validar", "subir", "proponer"):
        s = sub.add_parser(nombre)
        s.add_argument("cliente_id")
        s.add_argument("archivo")
        if nombre != "validar":
            s.add_argument("--de-verdad", action="store_true", help="sin esto, solo se prueba")
    a = p.parse_args(argv)

    if a.orden == "bajar":
        print(json.dumps(bajar(a.cliente_id), ensure_ascii=False, indent=1))
    elif a.orden == "pendientes":
        resumen, escritos = lotes(a.cliente_id, a.por_lote)
        print(json.dumps(resumen, ensure_ascii=False, indent=1))
        for ruta in escritos:
            print(f"· {ruta}")
    elif a.orden == "validar":
        aceptadas, descartadas = rondas.validar(_espacio(a.cliente_id), _leer(a.archivo))
        print(f"aceptadas: {len(aceptadas)}")
        for d in descartadas:
            print(f"· {enmascarar(str(d.get('hilo', '')))}: {d['motivo']}")
        return 0 if not descartadas else 1
    elif a.orden == "subir":
        r = _pedir("POST", f"/espacios/{a.cliente_id}/rondas", _leer(a.archivo),
                   probar="false" if a.de_verdad else "true")
        print(r.decode())
    elif a.orden == "proponer":
        propuesta = _leer(a.archivo)
        _, descartados = perfil.validar(_espacio(a.cliente_id), propuesta.get("perfil") or {})
        print(f"descartados en local: {len(descartados)}")
        for d in descartados[:30]:
            print(f"· {d['seccion']}: {d['motivo']}")
        if a.de_verdad:
            print(_pedir("POST", f"/espacios/{a.cliente_id}/propuestas", propuesta).decode())
    elif a.orden == "servidor":
        print(f'AGENTE_DATOS={RAIZ_LOCAL} ANTHROPIC_API_KEY= uvicorn agente.app:app --port 8090\n'
              f"→ http://localhost:8090/espacios/{a.cliente_id}?llave=$TENANT_INTERNAL_TOKEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
