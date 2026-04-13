# GPU build (default): docker compose -f docker/docker-compose.yml build ml-service
# CPU build: ML_SERVING_REQUIREMENTS=requirements.cpu.txt docker compose -f docker/docker-compose.yml build ml-service
FROM python:3.11-slim

WORKDIR /app

ARG ML_SERVING_REQUIREMENTS=requirements.txt
COPY ml/serving/requirements*.txt ./ml/serving/
RUN pip install --no-cache-dir -r ./ml/serving/${ML_SERVING_REQUIREMENTS}

COPY ml/ ./ml/
COPY fraud_scenarios.sql ./fraud_scenarios.sql

ARG MODEL_URL
RUN mkdir -p /models

EXPOSE 8002

CMD ["uvicorn", "ml.serving.ml_service:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]