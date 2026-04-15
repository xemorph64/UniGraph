from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, ConfigDict
import asyncio
import uuid
from datetime import datetime
import time

from ..services.neo4j_service import neo4j_service
from ..services.fraud_scorer import fraud_scorer, MLScoringRequiredError
from ..config import settings
from ..contracts.transaction_ingest_contract import (
    INGEST_CONTRACT_VERSION,
    SUPPORTED_INGEST_CHANNELS,
)
from ..contracts.transaction_ingest_payload import TransactionIngestPayload
from .ws import manager

router = APIRouter()


def _risk_level_and_recommendation(risk_score: float) -> tuple[str, str]:
    if risk_score >= 90:
        return "CRITICAL", "BLOCK"
    if risk_score >= 80:
        return "HIGH", "HOLD"
    if risk_score >= 60:
        return "MEDIUM", "REVIEW"
    return "LOW", "ALLOW"


def _to_transaction_response_payload(txn: dict) -> dict:
    txn_id = str(txn.get("txn_id") or txn.get("id") or "")
    risk_score = float(txn.get("risk_score", 0.0) or 0.0)

    risk_level = txn.get("risk_level")
    recommendation = txn.get("recommendation")
    if not risk_level or not recommendation:
        risk_level, recommendation = _risk_level_and_recommendation(risk_score)

    timestamp = txn.get("timestamp")
    if hasattr(timestamp, "isoformat"):
        timestamp = timestamp.isoformat()
    elif not timestamp:
        timestamp = datetime.utcnow().isoformat() + "Z"

    rule_violations = txn.get("rule_violations") or []
    if not isinstance(rule_violations, list):
        rule_violations = [str(rule_violations)]

    xgb_risk_score = txn.get("xgboost_risk_score")
    if xgb_risk_score is None:
        xgb_risk_score = int(round(risk_score))

    return {
        "txn_id": txn_id,
        "from_account": str(txn.get("from_account") or ""),
        "to_account": str(txn.get("to_account") or ""),
        "amount": float(txn.get("amount", 0.0) or 0.0),
        "channel": str(txn.get("channel") or "IMPS"),
        "timestamp": str(timestamp),
        "risk_score": risk_score,
        "risk_level": str(risk_level),
        "recommendation": str(recommendation),
        "rule_violations": [str(rule) for rule in rule_violations],
        "primary_fraud_type": txn.get("primary_fraud_type"),
        "is_flagged": bool(txn.get("is_flagged", risk_score >= 60)),
        "alert_id": txn.get("alert_id"),
        "gnn_fraud_probability": txn.get("gnn_fraud_probability"),
        "if_anomaly_score": txn.get("if_anomaly_score"),
        "xgboost_risk_score": int(xgb_risk_score),
        "model_version": txn.get("model_version"),
        "scoring_mode": txn.get("scoring_mode"),
    }


class TransactionResponse(BaseModel):
    txn_id: str
    from_account: str
    to_account: str
    amount: float
    channel: str
    timestamp: str
    risk_score: float
    risk_level: str
    recommendation: str
    rule_violations: list[str]
    primary_fraud_type: Optional[str] = None
    is_flagged: bool
    alert_id: Optional[str] = None
    gnn_fraud_probability: Optional[float] = None
    if_anomaly_score: Optional[float] = None
    xgboost_risk_score: Optional[int] = None
    model_version: Optional[str] = None
    scoring_mode: Optional[str] = None


class TransactionIngest(TransactionIngestPayload):
    pass


class BatchTransactionIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TransactionIngest]


def _alerts_enabled() -> bool:
    return (not settings.HIGH_THROUGHPUT_MODE) or settings.HIGH_THROUGHPUT_ALERTS_ENABLED


def _prepare_ingest_txn_dict(txn: TransactionIngest) -> dict:
    txn_dict = txn.model_dump()
    txn_dict["txn_id"] = (
        txn_dict.get("txn_id") or f"TXN-{uuid.uuid4().hex[:12].upper()}"
    )
    txn_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    txn_dict["device_id"] = txn_dict.get("device_id") or "DEV-UNKNOWN"
    return txn_dict


@router.get("/{txn_id}", response_model=TransactionResponse)
async def get_transaction(txn_id: str):
    """Get transaction details with SHAP explanation."""
    txn = await neo4j_service.get_transaction(txn_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse(**_to_transaction_response_payload(txn))


@router.get("/")
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    account_id: Optional[str] = None,
    channel: Optional[str] = None,
    min_risk_score: Optional[float] = Query(None, ge=0, le=100),
):
    """List transactions with pagination and filters."""
    result = await neo4j_service.get_transactions(
        page=page,
        page_size=page_size,
        account_id=account_id,
        channel=channel,
        min_risk_score=min_risk_score,
    )
    return {
        "items": result["items"],
        "total": result["total"],
        "page": page,
        "page_size": page_size,
    }


@router.post("/ingest", response_model=TransactionResponse)
async def ingest_transaction(txn: TransactionIngest):
    """Ingest a transaction and run fraud scoring pipeline."""
    txn_dict = _prepare_ingest_txn_dict(txn)

    try:
        score_result = await fraud_scorer.score_transaction(txn_dict)
    except MLScoringRequiredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    txn_dict["risk_score"] = score_result["risk_score"]
    txn_dict["rule_violations"] = score_result["rule_violations"]
    txn_dict["primary_fraud_type"] = score_result.get("primary_fraud_type")
    txn_dict["is_flagged"] = score_result["risk_score"] >= 60
    txn_dict["model_version"] = score_result.get("model_version")
    txn_dict["scoring_mode"] = score_result.get("scoring_mode")
    txn_dict["from_customer_id"] = txn.customer_id or f"CUST-{txn.from_account}"
    txn_dict["to_customer_id"] = f"CUST-{txn.to_account}"
    txn_dict["from_is_dormant"] = txn.is_dormant

    await neo4j_service.create_transaction_node(txn_dict)

    alert = None
    if _alerts_enabled() and await fraud_scorer.should_create_alert(score_result):
        alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
        alert = await neo4j_service.create_alert(
            {
                "alert_id": alert_id,
                "transaction_id": txn_dict["txn_id"],
                "account_id": txn.from_account,
                "risk_score": score_result["risk_score"],
                "risk_level": score_result["risk_level"],
                "shap_top3": score_result["shap_top3"],
                "rule_flags": score_result["rule_violations"],
                "primary_fraud_type": score_result.get("primary_fraud_type"),
                "recommendation": score_result["recommendation"],
            }
        )

        created_at = alert.get("created_at") if alert else None
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()

        asyncio.create_task(
            manager.broadcast_alert(
                {
                    "alert": {
                        "id": alert_id,
                        "transaction_id": txn_dict["txn_id"],
                        "account_id": txn.from_account,
                        "risk_score": score_result["risk_score"],
                        "risk_level": score_result["risk_level"],
                        "recommendation": score_result["recommendation"],
                        "rule_flags": score_result["rule_violations"],
                        "primary_fraud_type": score_result.get("primary_fraud_type"),
                        "shap_top3": score_result["shap_top3"],
                        "status": "OPEN",
                        "created_at": created_at,
                    }
                }
            )
        )

    return TransactionResponse(
        txn_id=txn_dict["txn_id"],
        from_account=txn.from_account,
        to_account=txn.to_account,
        amount=txn.amount,
        channel=txn.channel,
        timestamp=txn_dict["timestamp"],
        risk_score=score_result["risk_score"],
        risk_level=score_result["risk_level"],
        recommendation=score_result["recommendation"],
        rule_violations=score_result["rule_violations"],
        primary_fraud_type=score_result.get("primary_fraud_type"),
        is_flagged=txn_dict["is_flagged"],
        alert_id=alert["id"] if alert else None,
        gnn_fraud_probability=score_result.get("gnn_fraud_probability"),
        if_anomaly_score=score_result.get("if_anomaly_score"),
        xgboost_risk_score=score_result.get("xgboost_risk_score"),
        model_version=score_result.get("model_version"),
        scoring_mode=score_result.get("scoring_mode"),
    )


@router.post("/ingest/batch")
async def ingest_transactions_batch(batch: BatchTransactionIngestRequest):
    """Ingest transactions in batch for high-throughput use cases."""
    if not batch.items:
        return {
            "received": 0,
            "ingested": 0,
            "flagged": 0,
            "alerts_created": 0,
            "duration_ms": 0.0,
            "throughput_tps": 0.0,
        }

    if len(batch.items) > settings.MAX_BATCH_INGEST_SIZE:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Batch size {len(batch.items)} exceeds MAX_BATCH_INGEST_SIZE="
                f"{settings.MAX_BATCH_INGEST_SIZE}"
            ),
        )

    started = time.perf_counter()
    semaphore = asyncio.Semaphore(max(1, settings.BATCH_INGEST_SCORE_CONCURRENCY))

    async def _score_one(txn: TransactionIngest) -> tuple[dict, dict]:
        async with semaphore:
            txn_dict = _prepare_ingest_txn_dict(txn)
            try:
                score_result = await fraud_scorer.score_transaction(txn_dict)
            except MLScoringRequiredError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc

            txn_dict["risk_score"] = score_result["risk_score"]
            txn_dict["rule_violations"] = score_result["rule_violations"]
            txn_dict["primary_fraud_type"] = score_result.get("primary_fraud_type")
            txn_dict["is_flagged"] = score_result["risk_score"] >= 60
            txn_dict["model_version"] = score_result.get("model_version")
            txn_dict["scoring_mode"] = score_result.get("scoring_mode")
            txn_dict["from_customer_id"] = txn.customer_id or f"CUST-{txn.from_account}"
            txn_dict["to_customer_id"] = f"CUST-{txn.to_account}"
            txn_dict["from_is_dormant"] = txn.is_dormant
            return txn_dict, score_result

    scored = await asyncio.gather(*(_score_one(txn) for txn in batch.items))
    txn_payloads = [txn_dict for txn_dict, _ in scored]
    ingested = await neo4j_service.bulk_upsert_transactions(txn_payloads)

    alerts_created = 0
    if _alerts_enabled():
        for txn_dict, score_result in scored:
            if not await fraud_scorer.should_create_alert(score_result):
                continue

            alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
            alert = await neo4j_service.create_alert(
                {
                    "alert_id": alert_id,
                    "transaction_id": txn_dict["txn_id"],
                    "account_id": txn_dict["from_account"],
                    "risk_score": score_result["risk_score"],
                    "risk_level": score_result["risk_level"],
                    "shap_top3": score_result["shap_top3"],
                    "rule_flags": score_result["rule_violations"],
                    "primary_fraud_type": score_result.get("primary_fraud_type"),
                    "recommendation": score_result["recommendation"],
                }
            )

            created_at = alert.get("created_at") if alert else None
            if hasattr(created_at, "isoformat"):
                created_at = created_at.isoformat()

            asyncio.create_task(
                manager.broadcast_alert(
                    {
                        "alert": {
                            "id": alert_id,
                            "transaction_id": txn_dict["txn_id"],
                            "account_id": txn_dict["from_account"],
                            "risk_score": score_result["risk_score"],
                            "risk_level": score_result["risk_level"],
                            "recommendation": score_result["recommendation"],
                            "rule_flags": score_result["rule_violations"],
                            "primary_fraud_type": score_result.get("primary_fraud_type"),
                            "shap_top3": score_result["shap_top3"],
                            "status": "OPEN",
                            "created_at": created_at,
                        }
                    }
                )
            )
            alerts_created += 1

    elapsed_seconds = max(0.0001, time.perf_counter() - started)
    flagged = sum(1 for txn_dict, _ in scored if txn_dict.get("is_flagged"))

    return {
        "received": len(batch.items),
        "ingested": ingested,
        "flagged": flagged,
        "alerts_created": alerts_created,
        "duration_ms": round(elapsed_seconds * 1000.0, 2),
        "throughput_tps": round(ingested / elapsed_seconds, 2),
    }
