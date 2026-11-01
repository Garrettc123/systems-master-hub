FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/garcar-forge

RUN groupadd --system app && useradd --system --gid app --home-dir /srv/garcar-forge app

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir .

RUN mkdir -p /data && chown -R app:app /srv/garcar-forge /data
USER app

ENV GARCAR_LEDGER_PATH=/data/garcar-forge.sqlite3
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/readyz', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
