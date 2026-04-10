from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_CORS_ORIGINS: str = "http://localhost:5173"

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "unigraph_dev"

    REDIS_URL: str = "redis://localhost:6379/0"

    CASSANDRA_CONTACT_POINTS: str = "localhost"
    CASSANDRA_KEYSPACE: str = "unigraph_ts"

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_SCHEMA_REGISTRY_URL: str = "http://localhost:8081"

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 480

    ML_SERVICE_URL: str = "http://localhost:8002"

    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.1-70b-versatile"
    GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"

    FINACLE_API_URL: str = ""
    FINACLE_CLIENT_ID: str = ""
    FINACLE_CLIENT_SECRET: str = ""

    FIU_IND_API_URL: str = ""
    FIU_IND_MTLS_CERT_PATH: str = ""
    NCRP_API_URL: str = ""
    NCRP_API_KEY: str = ""

    DEMO_MODE: bool = True
    DEMO_SEED_ON_STARTUP: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
