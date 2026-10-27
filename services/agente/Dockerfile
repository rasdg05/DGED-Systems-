# Agente a la medida (services/agente). Se construye desde la RAÍZ del repo:
#   docker build -f services/agente/Dockerfile .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 \
    AGENTE_DATOS=/data/espacios

# libmagic para neonize (igual que el worker de Gestor).
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY services/agente/requirements.txt services/agente/requirements-vinculado.txt /tmp/
RUN pip install -r /tmp/requirements.txt -r /tmp/requirements-vinculado.txt
COPY services/agente /srv

EXPOSE 8080
CMD ["sh", "/srv/arrancar.sh"]
