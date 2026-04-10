import asyncio
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .services.neo4j_service import neo4j_service
from .routers import (
    transactions,
    accounts,
    alerts,
    cases,
    reports,
    ws,
    fraud_scoring,
    enforcement,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("unigraph_starting", env=settings.APP_ENV)
    try:
        await neo4j_service.connect()
        await neo4j_service.initialize_schema()
        logger.info("neo4j_ready")
    except Exception as e:
        logger.error("neo4j_connection_failed", error=str(e))
        logger.warning("running_without_neo4j_demo_will_use_fallback")

    if settings.DEMO_SEED_ON_STARTUP and settings.DEMO_MODE:
        try:
            logger.info("seeding_demo_data")
            asyncio.create_task(_seed_demo_data_async())
        except Exception as e:
            logger.error("demo_seed_failed", error=str(e))

    yield

    await neo4j_service.close()
    logger.info("unigraph_shutdown")


async def _seed_demo_data_async():
    await asyncio.sleep(5)
    try:
        import subprocess
        import sys
        import os

        seeder_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "demo_seeder.py"
        )
        subprocess.run([sys.executable, seeder_path], check=True)
        logger.info("demo_data_seeded")
    except Exception as e:
        logger.error("demo_seed_background_failed", error=str(e))


app = FastAPI(
    title="UniGRAPH — AI-Powered Fraud Detection API",
    version="1.0.0",
    description="Graph-native fund flow tracking for Union Bank of India",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.APP_CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    Instrumentator().instrument(app).expose(app)
except Exception:
    pass

app.include_router(
    transactions.router, prefix="/api/v1/transactions", tags=["transactions"]
)
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(ws.router, prefix="/api/v1", tags=["websocket"])
app.include_router(fraud_scoring.router, prefix="/api/v1/fraud", tags=["fraud-scoring"])
app.include_router(
    enforcement.router, prefix="/api/v1/enforcement", tags=["enforcement"]
)


@app.get("/health")
async def health():
    neo4j_ok = False
    try:
        stats = await neo4j_service.get_graph_stats()
        neo4j_ok = True
    except Exception:
        stats = {}
    return {
        "status": "healthy",
        "version": "1.0.0",
        "neo4j": "connected" if neo4j_ok else "disconnected",
        "graph_stats": stats,
        "demo_mode": settings.DEMO_MODE,
    }


@app.get("/api/v1/demo/reset")
async def reset_demo():
    try:
        import subprocess, sys, os

        seeder_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "demo_seeder.py"
        )
        subprocess.run([sys.executable, seeder_path], check=True)
        return {"status": "demo_data_reset", "message": "3 fraud scenarios reloaded"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
