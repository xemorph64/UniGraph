from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from .config import settings
from .routers import transactions, accounts, alerts, cases, reports, ws, fraud_scoring, enforcement

app = FastAPI(
    title="UniGRAPH Backend API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.APP_CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(ws.router, prefix="/api/v1", tags=["websocket"])
app.include_router(fraud_scoring.router, prefix="/api/v1/fraud", tags=["fraud-scoring"])
app.include_router(enforcement.router, prefix="/api/v1/enforcement", tags=["enforcement"])

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}
