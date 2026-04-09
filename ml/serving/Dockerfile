FROM python:3.11-slim

WORKDIR /app

COPY ml/serving/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ml/ ./ml/

ARG MODEL_URL
RUN mkdir -p /models

EXPOSE 8002

CMD ["uvicorn", "ml.serving.ml_service:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]