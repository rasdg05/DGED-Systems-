"""Lo que gasta cada cliente en la API, y el tope que lo corta (invariante 5).

Precios por millón de tokens tomados de la skill `claude-api` (tabla cacheada
el 2026-10-06), no de memoria, como pide `docs/15-agente-a-la-medida.md`:

- `claude-opus-5-5`: entrada 4.00, salida 20.00, lectura de caché 0.20.
- `claude-haiku-5-5`: entrada 0.10, salida 0.50 con prompt de hasta 100K
  tokens (0.50 / 2.50 arriba); lectura de caché 0.1x de la entrada.
- Escritura de caché: 1.25x la entrada (TTL 5 min). Batch API: 50% de todo.

Si cambian, se cambia esta tabla y la fecha; un modelo que no está en la tabla
no se puede llamar (`PrecioDesconocido`): gastar sin poder contar es gastar a
ciegas.

El tope sale de `config.json` del espacio (`tope_usd_mes`) o de
`TENANT_TOPE_USD_MES`. Sin ninguno de los dos, el tope es 0: el agente no
llama a la API hasta que alguien diga cuánto puede gastar.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from .espacio import Espacio

PRECIOS_FECHA = "2026-10-06"
PRECIOS = {
    # modelo: (entrada, salida, lectura de caché) USD por millón de tokens
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
}
HAIKU_LARGO = (0.50, 2.50, 0.05)  # prompt de más de 100K tokens
ESCRITURA_CACHE = 1.25
DESCUENTO_LOTE = 0.5
ARCHIVO = "gasto.jsonl"
VARIABLE_TOPE = "TENANT_TOPE_USD_MES"


class PrecioDesconocido(KeyError):
    pass


class TopeAlcanzado(RuntimeError):
    pass


def costo_usd(modelo: str, *, entrada: int, salida: int, cache_lectura: int = 0,
              cache_escritura: int = 0, lote: bool = False) -> float:
    if modelo not in PRECIOS:
        raise PrecioDesconocido(modelo)
    p_in, p_out, p_cache = PRECIOS[modelo]
    if modelo == "claude-haiku-5-5" and entrada + cache_lectura + cache_escritura > 100_000:
        p_in, p_out, p_cache = HAIKU_LARGO
    usd = (entrada * p_in + salida * p_out + cache_lectura * p_cache
           + cache_escritura * p_in * ESCRITURA_CACHE) / 1_000_000
    return usd * (DESCUENTO_LOTE if lote else 1.0)


def _mes(cuando: datetime | None = None) -> str:
    return (cuando or datetime.now(timezone.utc)).strftime("%Y-%m")


def tope_usd(espacio: Espacio) -> float:
    valor = espacio.config().get("tope_usd_mes")
    if valor is None:
        valor = os.environ.get(VARIABLE_TOPE, "").strip() or 0
    try:
        return max(float(valor), 0.0)
    except (TypeError, ValueError):
        return 0.0


def gastado_usd(espacio: Espacio, mes: str | None = None) -> float:
    mes = mes or _mes()
    return sum(r["usd"] for r in espacio.leer_lineas(ARCHIVO) if r.get("mes") == mes)


def puede_gastar(espacio: Espacio) -> bool:
    return gastado_usd(espacio) < tope_usd(espacio)


def exigir_saldo(espacio: Espacio) -> None:
    if not puede_gastar(espacio):
        raise TopeAlcanzado(f"{espacio.cliente_id} llegó a su tope de USD {tope_usd(espacio):.2f} este mes")


def registrar(espacio: Espacio, modelo: str, uso, *, motivo: str, lote: bool = False) -> float:
    """Anota una llamada con su `usage` de la API. Devuelve lo que costó."""
    usd = costo_usd(
        modelo,
        entrada=getattr(uso, "input_tokens", 0) or 0,
        salida=getattr(uso, "output_tokens", 0) or 0,
        cache_lectura=getattr(uso, "cache_read_input_tokens", 0) or 0,
        cache_escritura=getattr(uso, "cache_creation_input_tokens", 0) or 0,
        lote=lote,
    )
    espacio.agregar_linea(ARCHIVO, {"mes": _mes(), "en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "modelo": modelo, "motivo": motivo, "lote": lote, "usd": round(usd, 6)})
    return usd


def estimar_mes(*, conversaciones: int, turnos_por_conversacion: float, fraccion_guardadas: float,
                perfil_tokens: int, historia_tokens: int, salida_tokens: int,
                fraccion_escala_grande: float, mensajes_historial: int, perfil_inicial: bool) -> dict:
    """Costo de un cliente típico en un mes, con supuestos explícitos (no es una medición)."""
    turnos_modelo = conversaciones * turnos_por_conversacion * (1 - fraccion_guardadas)
    # Turno de rutina en Haiku: el perfil se lee de caché salvo la primera escritura de cada conversación.
    turno = costo_usd("claude-haiku-5-5", entrada=historia_tokens, salida=salida_tokens,
                      cache_lectura=perfil_tokens)
    escritura = costo_usd("claude-haiku-5-5", entrada=0, salida=0, cache_escritura=perfil_tokens)
    rutina = turnos_modelo * turno + conversaciones * escritura
    grande = turnos_modelo * fraccion_escala_grande * costo_usd(
        "claude-opus-5-5", entrada=historia_tokens + perfil_tokens, salida=salida_tokens * 2)
    clasificacion = costo_usd("claude-haiku-5-5", entrada=mensajes_historial * 60 + 400,
                              salida=mensajes_historial * 8, lote=True)
    perfil = costo_usd("claude-opus-5-5", entrada=200_000, salida=16_000) if perfil_inicial else 0.0
    return {"rutina": rutina, "escala_a_opus": grande, "clasificacion_lote": clasificacion,
            "perfil_una_vez": perfil, "total": rutina + grande + clasificacion + perfil,
            "precios_de": PRECIOS_FECHA}
