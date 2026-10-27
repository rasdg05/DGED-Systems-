---
name: enjambre
description: Enjambre local de agentes de Claude Code que atiende las cotizaciones y pláticas pendientes de un negocio del agente a la medida (services/agente) sin gastar API. Úsalo cuando el dueño pida "corre el enjambre", "atiende los pendientes", "swarm de agentes contra los pendientes", "ronda" o "arma el perfil en local".
---

# Enjambre local (D-027)

Lo mismo que Gestor hace con `app/services/rondas.py`, llevado al agente a la
medida. Corre en la sesión de Claude Code: **no llama a la API de Anthropic**.
Producción solo recibe el resultado, lo revisa con candados y lo deja
esperando el sí de una persona del negocio.

## Antes de lanzar (todo esto es del dueño)

- Una orden escrita del dueño con fecha: va en `orden` de la ronda.
- `AGENTE_URL` y `TENANT_INTERNAL_TOKEN` (llave maestra) en el entorno.
- Para cotizar con cifra: **perfil aprobado** en producción. Sin perfil, la
  ronda solo puede pedir el dato que falta o dar seguimiento, sin números.

## Pasos

```bash
cd services/agente
python -m agente.local bajar <id>                    # copia local, tope 0, en sombra
python -m agente.local pendientes <id> --por-lote 10 # vara + lotes en datos/espacios/<id>/enjambre/<fecha>/
```

1. **Reparte**: un subagente (`Agent`, tipo general-purpose) por lote. Corren
   en paralelo; 143 pendientes en lotes de 10 son ~15 agentes.
2. **Cada agente** lee su lote y el perfil activo
   (`datos/espacios/<id>/perfil/v<activa>.json`) y devuelve, por plática, una
   entrada o un "no sale" con por qué. Instrucción para el subagente:

   > Lee cada plática completa. Redacta lo que la persona del negocio
   > contestaría hoy, con SU voz (frases de `voz` del perfil y de sus propios
   > mensajes en la plática), trato de usted si así escribe el negocio.
   > **Ningún número** en tus textos: ni precio, ni fecha con número, ni
   > cantidad con letra. Si hace falta cotizar y la plática trae propiedad,
   > fechas y personas, llena `cotizacion` y el código pega la cifra. Si falta
   > un dato, pídelo. No contestes reclamos, lo que ya cerró, lo que lleva una
   > persona ni lo que pide algo que solo el dueño sabe: ponlo en "no sale".
   > Copia `hilo` y `ultimo_id` tal cual del lote. Máximo 3 textos cortos.

3. **El orquestador revisa cada texto contra su plática** (Gestor: "comprueba que
   sean respuestas correctas y soluciones completas"): ¿contesta lo que el
   cliente preguntó?, ¿no promete nada que el perfil no dice?, ¿una persona ya
   lo atendió por otro lado? Lo dudoso sale de la ronda y va a la lista del dueño.
4. **Arma la ronda** en `datos/espacios/<id>/enjambre/<fecha>/ronda.json`:

   ```json
   {"nombre": "2026-10-28-am", "orden": "dueño, 2026-10-28: «...»", "autor": "enjambre local (Claude Code)",
    "entradas": [{"hilo": "...", "ultimo_id": "...", "resumen": "sin teléfono",
                  "textos": ["..."], "cotizacion": {"propiedad": "quinta", "llegada": "2026-11-09",
                  "salida": "2026-11-11", "personas": 8, "evento": false}}]}
   ```
   `cotizacion` es opcional.

5. **Valida en local**, luego **prueba contra producción** (no escribe nada):

   ```bash
   python -m agente.local validar <id> datos/espacios/<id>/enjambre/<fecha>/ronda.json
   python -m agente.local subir   <id> datos/espacios/<id>/enjambre/<fecha>/ronda.json
   ```
6. **Solo con el sí del dueño**: `subir ... --de-verdad`. Las aceptadas quedan
   esperando aprobación de una persona del negocio; **nada se envía desde aquí**.
   Sin conector oficial (`WHATSAPP_TOKEN` + `phone_number_id`) tampoco se envía
   después: el lector vinculado es de solo lectura (D-018).

## Candados que hace el código (no el criterio del agente)

`agente/rondas.py`, tests en `tests/test_agente_enjambre.py`:

- La plática se movió desde `ultimo_id` → no se carga, y si ya se cargó, no se envía.
- Solo pláticas en `espera` (`pendientes.py`): reclamos, medios y acuses, fuera.
- Cifra en el texto del enjambre (con número o con letra) → fuera. La cifra la
  pone el cotizador con el perfil aprobado.
- Voz ajena o "soy una persona" → fuera.
- Todo espera aprobación de una persona. Una ronda cargada no se recarga.

## Perfil en local (en vez de la pasada de Opus)

Los agentes leen el historial bajado y arman `{"nombre": "...", "perfil": {...}}`
con el esquema de `simbiosis.ESQUEMA_PERFIL`: cada renglón con
`origen = {tipo: "mensaje", id, cita}` y la cita copiada letra por letra.
`python -m agente.local proponer <id> perfil.json` dice qué se descartaría;
con `--de-verdad` queda como propuesta en producción y la enciende el dueño
del negocio en Asistente. Es la misma validación que la de Opus.

## Al terminar

Lo que quedó para el dueño, en una lista con el teléfono enmascarado
(`…1234`), y una línea en `MEMORY/ESTADO.md`. Los lotes y la ronda no se suben
a git: llevan datos de clientes finales (invariante 8).
