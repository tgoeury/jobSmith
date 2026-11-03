# Image de production pour l'Assistant Emploi (servie par gunicorn).
FROM python:3.11-slim

# Sorties Python non bufferisées + pas de .pyc.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ASSISTANT_EMPLOI_DATA_DIR=/data

WORKDIR /app

# Dépendances d'abord (meilleure mise en cache des couches).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Chromium headless pour les annonces rendues en JavaScript (+ dépendances système).
RUN playwright install --with-deps chromium

# Code de l'application.
COPY assistant_emploi ./assistant_emploi
COPY assets ./assets
COPY config.json ./config.json

# Les données persistent dans /data (à monter en volume).
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8050

# La base vide est créée automatiquement au premier démarrage
# (init_db() est appelé à l'import de assistant_emploi.app).
# 1 worker : SQLite n'autorise qu'un seul écrivain ; les threads gèrent la concurrence.
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "1", "--threads", "4", \
     "--timeout", "120", "assistant_emploi.app:server"]
