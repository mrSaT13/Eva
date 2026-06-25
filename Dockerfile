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

RUN mkdir -p /eva/config /eva/data && chown -R 1001:1001 /eva

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
COPY --chown=1001:1001 docker-config ./config

COPY --link --from=frontend-builder --chown=1001:1001 /home/frontend/dist/ ./eva_plugin_web_face_frontend/frontend-dist/
COPY --chown=1001:1001 resources/ico.png ./eva_plugin_web_face_frontend/frontend-dist/ico.png

EXPOSE 8086

VOLUME ["/eva/config", "/eva/data"]
ENV EVA_HOME=/eva/data

ENTRYPOINT ["python", "-m", "eva", "-T", "web"]
