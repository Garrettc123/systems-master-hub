# Staging-only heartbeat canary for Systems Master Hub.
# This container does not run the dashboard, ZEUS entrypoints, agents, or control plane.
FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY mesh_heartbeat.py /app/mesh_heartbeat.py
USER 65532:65532
CMD ["sh", "-c", "while true; do python -u /app/mesh_heartbeat.py; sleep 300; done"]
