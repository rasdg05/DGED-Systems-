FROM python:3.12-slim

WORKDIR /srv
COPY services/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt "psycopg[binary]==3.2.9"
COPY services/api /srv
COPY ontology /ontology
ENV ONTOLOGY_PATH=/ontology/atlas.ontology.json
ENV ATLAS_CACHE=/var/cache/atlas
RUN mkdir -p /var/cache/atlas
EXPOSE 8080
# Railway (y casi toda nube) asigna el puerto en $PORT; en local queda 8080.
CMD ["sh", "-c", "exec uvicorn atlas.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
