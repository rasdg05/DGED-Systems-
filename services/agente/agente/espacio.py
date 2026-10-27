"""Un espacio por cliente: lo único que el agente sabe de un negocio vive aquí.

Tres reglas (invariantes 4 y 8 de `docs/15-agente-a-la-medida.md`):

- Toda lectura y escritura de un cliente pasa por `Espacio.ruta`, que no deja
  salir de su carpeta. No hay otra forma de abrir un archivo de un cliente.
- La llave interna de cada cliente se deriva de `TENANT_INTERNAL_TOKEN` y del
  id del cliente: la de un negocio no abre a otro. Sin `TENANT_INTERNAL_TOKEN`
  no hay llave que sirva (mismo patrón que `ATLAS_ACCESS_TOKEN`).
- `borrar()` quita la carpeta completa al terminar el contrato: datos de los
  clientes finales incluidos, sin copia fuera del espacio.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
from pathlib import Path

ID_VALIDO = re.compile(r"^[a-z0-9][a-z0-9-]{2,39}$")
VARIABLE_LLAVE = "TENANT_INTERNAL_TOKEN"
VARIABLE_RAIZ = "AGENTE_DATOS"


class EspacioInvalido(ValueError):
    pass


def raiz_por_defecto() -> Path:
    return Path(os.environ.get(VARIABLE_RAIZ, "").strip() or "datos/espacios")


def llave_de(cliente_id: str, secreto: str | None = None) -> str:
    """La llave de un cliente. Vacía si no hay secreto: nadie entra."""
    secreto = os.environ.get(VARIABLE_LLAVE, "").strip() if secreto is None else secreto
    if not secreto:
        return ""
    return hmac.new(secreto.encode(), cliente_id.encode(), hashlib.sha256).hexdigest()


def llave_valida(cliente_id: str, llave: str | None) -> bool:
    """La llave del cliente abre su espacio. `TENANT_INTERNAL_TOKEN` mismo es la
    llave del dueño de DGED y abre todos; la derivada de un cliente no abre otro."""
    secreto = os.environ.get(VARIABLE_LLAVE, "").strip()
    if not secreto or not llave:
        return False
    return hmac.compare_digest(llave_de(cliente_id, secreto), llave) or hmac.compare_digest(secreto, llave)


def llave_maestra(llave: str | None) -> bool:
    """Solo `TENANT_INTERNAL_TOKEN`: la de DGED. Abre el taller (banco, sombra,
    historial crudo, la pasada del perfil), que la llave de un cliente no abre."""
    secreto = os.environ.get(VARIABLE_LLAVE, "").strip()
    return bool(secreto and llave) and hmac.compare_digest(secreto, llave or "")


def llave_de_vinculacion(cliente_id: str) -> str:
    """La llave del enlace que se le manda al negocio: abre SOLO la pantalla de
    vincular su WhatsApp (`/v/<id>`), no sus datos. Sale del mismo secreto."""
    return llave_de(f"{cliente_id}:vincular")[:24]


def vinculacion_valida(cliente_id: str, llave: str | None) -> bool:
    esperada = llave_de_vinculacion(cliente_id)
    return bool(esperada and llave) and hmac.compare_digest(esperada, llave or "")


class Espacio:
    def __init__(self, cliente_id: str, raiz: Path | None = None):
        if not ID_VALIDO.match(cliente_id or ""):
            raise EspacioInvalido(f"id de cliente inválido: {cliente_id!r}")
        self.cliente_id = cliente_id
        self.raiz = (raiz or raiz_por_defecto()).resolve()
        self.carpeta = self.raiz / cliente_id

    def ruta(self, nombre: str) -> Path:
        destino = (self.carpeta / nombre).resolve()
        if destino != self.carpeta and self.carpeta not in destino.parents:
            raise EspacioInvalido(f"{nombre!r} sale del espacio de {self.cliente_id}")
        return destino

    def existe(self, nombre: str) -> bool:
        return self.ruta(nombre).exists()

    def leer_json(self, nombre: str, defecto=None):
        ruta = self.ruta(nombre)
        if not ruta.exists():
            return defecto
        return json.loads(ruta.read_text(encoding="utf-8"))

    def escribir_json(self, nombre: str, datos) -> Path:
        ruta = self.ruta(nombre)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = ruta.with_suffix(ruta.suffix + ".tmp")
        tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(ruta)
        return ruta

    def agregar_linea(self, nombre: str, registro: dict) -> None:
        ruta = self.ruta(nombre)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n")

    def leer_lineas(self, nombre: str) -> list[dict]:
        ruta = self.ruta(nombre)
        if not ruta.exists():
            return []
        salida = []
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            try:
                salida.append(json.loads(linea))
            except json.JSONDecodeError:  # el lector vinculado puede estar a media línea
                continue
        return salida

    def borrar(self) -> None:
        """Fin del contrato: se va todo lo del cliente, sin respaldo aparte."""
        if self.carpeta.exists():
            shutil.rmtree(self.carpeta)

    def config(self) -> dict:
        return self.leer_json("config.json", {}) or {}
