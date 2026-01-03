FROM python:3.11-slim

WORKDIR /app

RUN pip install fastapi uvicorn aiohttp pydantic

COPY orchestrator.py .

EXPOSE 8302

CMD ["python", "orchestrator.py"]
