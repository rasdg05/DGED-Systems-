"""La única llamada que escribe a WhatsApp por el dispositivo vinculado (D-037).

Separada de `vinculado.py` para que el lector siga siendo de solo lectura en su
código fuente (lo revisa un test) y el envío tenga un solo lugar donde vive.
Manda texto plano a un número; qué y cuándo lo deciden `canal` y `enviador`.
"""
from __future__ import annotations


def de(client):  # pragma: no cover - necesita WhatsApp de verdad
    from neonize.utils import build_jid

    def mandar(hilo: str, texto: str) -> str | None:
        """Devuelve el ID que WhatsApp le dio al mensaje: con él, el eco que regrese
        por el historial no entra dos veces (lección de Gestor, `importador.eco_propio`)."""
        numero = "".join(c for c in str(hilo) if c.isdigit())
        if not numero:
            raise ValueError("hilo sin número")
        respuesta = client.send_message(build_jid(numero), texto)
        return getattr(respuesta, "ID", None) or None
    return mandar
