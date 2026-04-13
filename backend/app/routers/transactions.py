from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from ..services.neo4j_service import neo4j_service
from ..services.fraud_scorer import fraud_scorer
from .ws import manager

router = APIRouter()


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
    scoring_source: Optional[str] = None


class TransactionNodeResponse(BaseModel):
    id: str
    from_account: str
    to_account: str
    amount: float
    channel: str
    timestamp: str
    risk_score: float = 0
    is_flagged: bool = False
    rule_violations: list[str] = Field(default_factory=list)
    primary_fraud_type: Optional[str] = None
    gnn_fraud_probability: Optional[float] = None
    if_anomaly_score: Optional[float] = None
    xgboost_risk_score: Optional[int] = None
    model_version: Optional[str] = None
    scoring_source: Optional[str] = None


class TransactionIngest(BaseModel):
    txn_id: Optional[str] = None
    from_account: str
    to_account: str
    amount: float
    channel: str = "IMPS"
    customer_id: Optional[str] = None
    description: Optional[str] = "Transfer"
    device_id: Optional[str] = None
    is_dormant: bool = False
    device_account_count: int = 1
    velocity_1h: int = 0
    velocity_24h: int = 0
    account_age_days: Optional[int] = None
    kyc_tier: Optional[int] = None
    transaction_count_30d: Optional[int] = None
    avg_txn_amount_30d: Optional[float] = None
    device_count_30d: Optional[int] = None
    ip_count_30d: Optional[int] = None
    customer_age: Optional[float] = None
    avg_monthly_balance: Optional[float] = None
    avg_txn_amount: Optional[float] = None
    std_txn_amount: Optional[float] = None
    max_txn_amount: Optional[float] = None
    min_txn_amount: Optional[float] = None
    hour_of_day: Optional[int] = None
    day_of_week: Optional[int] = None
    is_weekend: Optional[bool] = None
    is_holiday: Optional[bool] = None
    geo_distance_from_home: Optional[float] = None
    device_risk_flag: Optional[bool] = None
    counterparty_risk_score: Optional[float] = None
    is_international: Optional[bool] = None
    channel_switch_count: Optional[int] = None
    amount_zscore: Optional[float] = None


@router.get("/{txn_id}", response_model=TransactionNodeResponse)
async def get_transaction(txn_id: str):
    """Get transaction details with SHAP explanation."""
    txn = await neo4j_service.get_transaction(txn_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.get("/")
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    account_id: Optional[str] = None,
    channel: Optional[str] = None,
    min_risk_score: Optional[float] = Query(None, ge=0, le=100),
    txn_id_prefix: Optional[str] = None,
):
    """List transactions with pagination and filters."""
    result = await neo4j_service.get_transactions(
        page=page,
        page_size=page_size,
        account_id=account_id,
        channel=channel,
        min_risk_score=min_risk_score,
        txn_id_prefix=txn_id_prefix,
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
    txn_dict = txn.dict()
    txn_dict["txn_id"] = (
        txn_dict.get("txn_id") or f"TXN-{uuid.uuid4().hex[:12].upper()}"
    )
    txn_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    txn_dict["device_id"] = txn_dict.get("device_id") or "DEV-UNKNOWN"

    score_result = await fraud_scorer.score_transaction(txn_dict)
    txn_dict["risk_score"] = score_result["risk_score"]
    txn_dict["rule_violations"] = score_result["rule_violations"]
    txn_dict["primary_fraud_type"] = score_result.get("primary_fraud_type")
    txn_dict["is_flagged"] = score_result["risk_score"] >= 60
    txn_dict["gnn_fraud_probability"] = score_result.get("gnn_fraud_probability")
    txn_dict["if_anomaly_score"] = score_result.get("if_anomaly_score")
    txn_dict["xgboost_risk_score"] = score_result.get("xgboost_risk_score")
    txn_dict["model_version"] = score_result.get("model_version")
    txn_dict["scoring_source"] = score_result.get("scoring_source")

    await neo4j_service.upsert_account(
        txn.from_account,
        txn.customer_id or f"CUST-{txn.from_account}",
        is_dormant=txn.is_dormant,
        risk_score=score_result["risk_score"],
    )
    await neo4j_service.upsert_account(txn.to_account, f"CUST-{txn.to_account}")

    await neo4j_service.create_transaction_node(txn_dict)

    alert = None
    if await fraud_scorer.should_create_alert(score_result):
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

        await manager.broadcast_alert(
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
        scoring_source=score_result.get("scoring_source"),
    )
