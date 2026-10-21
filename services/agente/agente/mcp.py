"""MCP de afinación: un agente de código lee y propone sobre UN espacio, nunca enciende.

    AGENTE_ESPACIO=<cliente> AGENTE_LLAVE=<llave> TENANT_INTERNAL_TOKEN=... \\
        python -m agente.mcp

Servidor MCP por stdio (JSON-RPC 2.0, una línea por mensaje), sin dependencias.
El espacio se fija al arrancar con su llave (`espacio.llave_valida`): las
herramientas no reciben id de cliente, así que no pueden mirar a otro
(invariante 4). Hay herramienta para proponer y ninguna para aprobar: una
propuesta queda como versión nueva con nombre y la enciende el dueño del
negocio (invariante 6).
"""
from __future__ import annotations

import json
import os
import sys

from . import agente, perfil, sombra
from .espacio import Espacio, llave_valida

PROTOCOLO = "2025-06-18"

HERRAMIENTAS = [
    {"name": "leer_perfil", "description": "El perfil activo del negocio y la lista de versiones.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "ver_sombra", "description": "Las últimas salidas del agente (borrador, vía y motivo).",
     "inputSchema": {"type": "object", "properties": {"ultimas": {"type": "integer", "minimum": 1, "maximum": 200}},
                     "additionalProperties": False}},
    {"name": "ver_metricas", "description": "La vara: cobertura, acierto, errores de cifra, tiempos. Holdout sellado.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "proponer_cambio",
     "description": ("Propone una versión nueva del perfil a partir de la activa: agrega renglones (con origen) "
                     "y quita renglones por índice. No la enciende: la aprueba el dueño del negocio."),
     "inputSchema": {"type": "object", "properties": {
         "nombre": {"type": "string"}, "motivo": {"type": "string"},
         "agregar": {"type": "object"}, "quitar": {"type": "object"}},
         "required": ["nombre", "motivo"], "additionalProperties": False}},
]


class Servidor:
    def __init__(self, espacio: Espacio):
        self.espacio = espacio

    def leer_perfil(self, _args: dict) -> dict:
        return {"activa": perfil.version_activa(self.espacio), "versiones": perfil.versiones(self.espacio),
                "perfil": perfil.activo(self.espacio)}

    def ver_sombra(self, args: dict) -> dict:
        ultimas = int(args.get("ultimas", 20))
        return {"salidas": [s.a_dict() for s in agente.salidas(self.espacio)[-ultimas:]]}

    def ver_metricas(self, _args: dict) -> dict:
        return sombra.medir(self.espacio, abrir_holdout=False)

    def proponer_cambio(self, args: dict) -> dict:
        base = perfil.activo(self.espacio) or {}
        nuevo = {k: v for k, v in base.items()}
        for seccion in perfil.SECCIONES:
            filas = list(base.get(seccion, []) or [])
            quitar = set((args.get("quitar") or {}).get(seccion, []) or [])
            filas = [f for i, f in enumerate(filas) if i not in quitar]
            filas += list((args.get("agregar") or {}).get(seccion, []) or [])
            nuevo[seccion] = filas
        n, descartados = perfil.proponer(self.espacio, nuevo, autor="agente de código (MCP)",
                                         nombre=f"{args['nombre']} — {args['motivo']}")
        return {"version": n, "estado": "propuesta: la enciende el dueño del negocio", "descartados": descartados}

    def atender(self, pedido: dict) -> dict | None:
        metodo, ident = pedido.get("method"), pedido.get("id")
        if ident is None:  # notificación
            return None
        if metodo == "initialize":
            resultado = {"protocolVersion": PROTOCOLO, "capabilities": {"tools": {}},
                         "serverInfo": {"name": "dged-agente-afinacion", "version": "0.1.0"}}
        elif metodo == "tools/list":
            resultado = {"tools": HERRAMIENTAS}
        elif metodo == "tools/call":
            nombre = (pedido.get("params") or {}).get("name")
            args = (pedido.get("params") or {}).get("arguments") or {}
            if nombre not in {h["name"] for h in HERRAMIENTAS}:
                return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32602, "message": f"herramienta desconocida: {nombre}"}}
            try:
                datos = getattr(self, nombre)(args)
                resultado = {"content": [{"type": "text", "text": json.dumps(datos, ensure_ascii=False, default=str)}]}
            except Exception as error:  # se le dice al agente qué falló; el servidor sigue vivo
                resultado = {"content": [{"type": "text", "text": f"{type(error).__name__}: {error}"}], "isError": True}
        elif metodo == "ping":
            resultado = {}
        else:
            return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": f"método no soportado: {metodo}"}}
        return {"jsonrpc": "2.0", "id": ident, "result": resultado}


def abrir() -> Servidor:
    cliente_id = os.environ.get("AGENTE_ESPACIO", "").strip()
    if not llave_valida(cliente_id, os.environ.get("AGENTE_LLAVE", "").strip()):
        raise PermissionError("sin TENANT_INTERNAL_TOKEN o con una llave que no es de este espacio: no se abre")
    return Servidor(Espacio(cliente_id))


def main() -> int:
    try:
        servidor = abrir()
    except PermissionError as error:
        print(str(error), file=sys.stderr)
        return 2
    for linea in sys.stdin:
        if not linea.strip():
            continue
        try:
            respuesta = servidor.atender(json.loads(linea))
        except json.JSONDecodeError:
            respuesta = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON inválido"}}
        if respuesta is not None:
            sys.stdout.write(json.dumps(respuesta, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
