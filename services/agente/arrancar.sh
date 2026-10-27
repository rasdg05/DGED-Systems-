#!/bin/sh
# Un contenedor, dos procesos que comparten el volumen de /data:
# - el lector vinculado (solo lectura), que se reinicia solo si se cae;
# - el servidor web en $PORT (Railway lo asigna; si no, 8080 como Atlas).
# Van juntos porque en Railway un volumen se monta en UN servicio.
set -eu
mkdir -p "${AGENTE_DATOS:-/data/espacios}"
(
  while true; do
    python -u -m agente.vinculado || true
    echo "lector vinculado terminó; reinicio en 5 s"
    sleep 5
  done
) &
exec uvicorn agente.app:app --host 0.0.0.0 --port "${PORT:-8080}"
