import asyncio
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .services.neo4j_service import neo4j_service
from .services.fraud_scorer import fraud_scorer
from .services.timeline_service import timeline_service
from .routers import (
    transactions,
    accounts,
    alerts,
    cases,
    reports,
    ws,
    fraud_scoring,
    enforcement,
    graph_analytics,
)

logger = structlog.get_logger()


async def _run_gds_once(reason: str) -> None:
    try:
        result = await neo4j_service.run_gds_analytics()
        logger.info("gds_analytics_run_complete", reason=reason, result=result)
    except Exception as exc:
        logger.warning("gds_analytics_run_failed", reason=reason, error=str(exc))


async def _gds_scheduler_loop() -> None:
    while True:
        await _run_gds_once("scheduled")
        await asyncio.sleep(max(60, int(settings.GDS_REFRESH_SECONDS)))


def _validate_non_demo_configuration() -> None:
    if settings.DEMO_MODE:
        return

    required_values = {
        "FINACLE_API_URL": settings.FINACLE_API_URL,
        "FINACLE_CLIENT_ID": settings.FINACLE_CLIENT_ID,
        "FINACLE_CLIENT_SECRET": settings.FINACLE_CLIENT_SECRET,
        "FIU_IND_API_URL": settings.FIU_IND_API_URL,
        "FIU_IND_MTLS_CERT_PATH": settings.FIU_IND_MTLS_CERT_PATH,
        "FIU_IND_MTLS_KEY_PATH": settings.FIU_IND_MTLS_KEY_PATH,
        "NCRP_API_URL": settings.NCRP_API_URL,
        "NCRP_API_KEY": settings.NCRP_API_KEY,
    }
    missing = [key for key, value in required_values.items() if not value]
    if missing:
        raise RuntimeError(
            "Non-demo mode requires provider configuration values: "
            + ", ".join(missing)
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("unigraph_starting", env=settings.APP_ENV)
    gds_scheduler_task: asyncio.Task | None = None
    env_name = settings.APP_ENV.strip().lower()
    _validate_non_demo_configuration()
    try:
        await neo4j_service.connect()
        await neo4j_service.initialize_schema()
        logger.info("neo4j_ready")

        if settings.ENABLE_GDS_SCHEDULER:
            if settings.GDS_RUN_ON_STARTUP:
                await _run_gds_once("startup")
            gds_scheduler_task = asyncio.create_task(_gds_scheduler_loop())
            logger.info(
                "gds_scheduler_started",
                refresh_seconds=max(60, int(settings.GDS_REFRESH_SECONDS)),
            )
    except Exception as e:
        logger.error("neo4j_connection_failed", error=str(e))
        logger.warning("running_without_neo4j_demo_will_use_fallback")

    should_seed_demo = (
        settings.ALLOW_DEMO_DATA
        and settings.DEMO_MODE
        and settings.DEMO_SEED_ON_STARTUP
        and env_name == "demo"
    )

    if should_seed_demo:
        try:
            logger.info("seeding_demo_data")
            asyncio.create_task(_seed_demo_data_async())
        except Exception as e:
            logger.error("demo_seed_failed", error=str(e))

    yield

    if gds_scheduler_task:
        gds_scheduler_task.cancel()
        try:
            await gds_scheduler_task
        except asyncio.CancelledError:
            pass

    await neo4j_service.close()
    await timeline_service.close()
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
app.include_router(
    graph_analytics.router,
    prefix="/api/v1/graph-analytics",
    tags=["graph-analytics"],
)


@app.get("/health")
async def health(response: Response):
    neo4j_ok = False
    ml_readiness = {
        "ml_service_reachable": False,
        "ml_service_url": settings.ML_SERVICE_URL,
        "fallback_mode_available": True,
    }
    try:
        stats = await neo4j_service.get_graph_stats()
        neo4j_ok = True
    except Exception:
        stats = {}

    try:
        ml_readiness = await fraud_scorer.get_ml_readiness()
    except Exception as exc:
        ml_readiness["ml_error"] = str(exc)

    ml_ok = bool(ml_readiness.get("ml_service_reachable"))
    if neo4j_ok and ml_ok:
        overall_status = "healthy"
        response.status_code = 200
    elif neo4j_ok:
        overall_status = "degraded"
        response.status_code = 200
    else:
        overall_status = "unhealthy"
        response.status_code = 503

    return {
        "status": overall_status,
        "version": "1.0.0",
        "neo4j": "connected" if neo4j_ok else "disconnected",
        "graph_stats": stats,
        "fraud_scoring": ml_readiness,
        "demo_mode": settings.DEMO_MODE,
    }


@app.get("/api/v1/demo/reset")
async def reset_demo():
    if not settings.ALLOW_DEMO_DATA or not settings.DEMO_MODE:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        import subprocess, sys, os

        seeder_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "scripts", "demo_seeder.py"
        )
        subprocess.run([sys.executable, seeder_path], check=True)
        return {"status": "demo_data_reset", "message": "3 fraud scenarios reloaded"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
