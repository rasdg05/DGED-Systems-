"""Quién puede gastar recursos del servidor.

Dos reglas, heredadas de Gestor Morelos ("sin token, sin puerta"):

- El Oráculo gasta la clave de Anthropic del servidor en cada pregunta. Sin
  `ATLAS_ACCESS_TOKEN` configurado no hay puerta: responde 503 aunque exista
  `ANTHROPIC_API_KEY`. Con él, la petición debe traer `X-Atlas-Key` igual.
- Calificar consulta fuentes públicas (INEGI, SMN). Un tope por IP evita que
  una demo pública se vuelva un martillo contra ellas.

Los topes viven en memoria del proceso: alcanzan para una réplica. Con varias
réplicas cada una lleva su cuenta, y eso se declara, no se esconde.
"""
from __future__ import annotations

import hmac
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

HEADER = "X-Atlas-Key"

# acción -> (variable de entorno, tope por defecto, ventana en segundos)
LIMITS = {
    "score": ("ATLAS_SCORE_LIMIT", 30, 600),
    "oracle": ("ATLAS_ORACLE_LIMIT", 20, 3600),
}

_hits: dict[tuple[str, str], deque] = defaultdict(deque)
_lock = threading.Lock()


def access_token() -> str:
    return os.environ.get("ATLAS_ACCESS_TOKEN", "").strip()


def limit_for(action: str) -> tuple[int, int]:
    variable, default, window = LIMITS[action]
    raw = os.environ.get(variable, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(value, 0), window


def client_of(request: Request) -> str:
    return request.client.host if request.client else "desconocido"


def check_rate(action: str, client: str, now: float | None = None) -> None:
    limit, window = limit_for(action)
    now = time.monotonic() if now is None else now
    with _lock:
        hits = _hits[(action, client)]
        while hits and now - hits[0] >= window:
            hits.popleft()
        if len(hits) >= limit:
            retry = int(window - (now - hits[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Demasiadas peticiones; intenta en {retry} s.",
                headers={"Retry-After": str(retry)},
            )
        hits.append(now)


def reset() -> None:
    with _lock:
        _hits.clear()


def guard_score(request: Request) -> None:
    check_rate("score", client_of(request))


def guard_oracle(request: Request) -> None:
    expected = access_token()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="El Oráculo está cerrado: el servidor no tiene ATLAS_ACCESS_TOKEN. Sin llave no hay puerta.",
        )
    given = request.headers.get(HEADER, "")
    if not hmac.compare_digest(given.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Llave de acceso inválida o ausente.")
    check_rate("oracle", client_of(request))
