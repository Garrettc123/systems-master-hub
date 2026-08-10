FROM python:3.11-slim

WORKDIR /app

# Run as an unprivileged user rather than root.
RUN useradd --create-home --uid 10001 appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY orchestrator.py .

USER appuser

CMD ["python", "orchestrator.py"]
