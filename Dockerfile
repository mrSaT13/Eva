# Eva Voice Assistant - Dockerfile
# Multi-stage build: frontend + backend

# --- Stage 1: Build frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /home/frontend
COPY ./frontend/package*.json ./
RUN npm ci
COPY ./frontend .
RUN npm run build-only

# --- Stage 2: Python backend ---
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 libatomic1 libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1001 eva && useradd --create-home eva --uid 1001 --gid eva

RUN mkdir -p /eva/data && chown -R 1001:1001 /eva

COPY ./requirements.txt /tmp/requirements.txt
COPY ./eva_plugin_llm/requirements.txt /tmp/eva_plugin_llm_requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/eva_plugin_llm_requirements.txt && rm /tmp/requirements.txt /tmp/eva_plugin_llm_requirements.txt

USER eva:eva
WORKDIR /home/eva

COPY --chown=1001:1001 eva ./eva
COPY --chown=1001:1001 eva_plugin_web_face ./eva_plugin_web_face
COPY --chown=1001:1001 eva_plugin_web_face_frontend ./eva_plugin_web_face_frontend
COPY --chown=1001:1001 eva_plugin_llm ./eva_plugin_llm
COPY --chown=1001:1001 eva_plugin_local_speech_face ./eva_plugin_local_speech_face
COPY --chown=1001:1001 eva_plugin_ntp ./eva_plugin_ntp
COPY --chown=1001:1001 eva_plugin_telegram_face ./eva_plugin_telegram_face
COPY --chown=1001:1001 eva_plugin_discord_face ./eva_plugin_discord_face
COPY --chown=1001:1001 eva_plugin_translate ./eva_plugin_translate
COPY --chown=1001:1001 docker-config ./config

COPY --from=frontend-builder --chown=1001:1001 /home/frontend/dist/ ./eva_plugin_web_face_frontend/frontend-dist/

EXPOSE 8086

VOLUME ["/eva/data"]
ENV EVA_HOME=/eva/data PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8086/api/config/configs/web_face_frontend', timeout=4)" || exit 1

ENTRYPOINT ["python", "-m", "eva", "-T", "web", "-d", "/home/eva/config"]
