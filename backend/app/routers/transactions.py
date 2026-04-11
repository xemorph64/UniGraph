from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
import uuid
from datetime import datetime

from ..services.neo4j_service import neo4j_service
from ..services.fraud_scorer import fraud_scorer

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
    is_flagged: bool
    alert_id: Optional[str] = None
    probability: Optional[float] = None


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


@router.get("/{txn_id}", response_model=TransactionResponse)
async def get_transaction(txn_id: str):
    """Get transaction details with SHAP explanation."""
    txn = await neo4j_service.get_transaction(txn_id)
    if not txn:
        return {"error": "Transaction not found"}
    return txn


@router.get("/")
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    account_id: Optional[str] = None,
    channel: Optional[str] = None,
):
    """List transactions with pagination and filters."""
    return {"items": [], "page": page, "page_size": page_size}


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
    txn_dict["is_flagged"] = score_result["risk_score"] >= 60

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
                "recommendation": score_result["recommendation"],
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
        is_flagged=txn_dict["is_flagged"],
        alert_id=alert["id"] if alert else None,
        probability=score_result["risk_score"] / 100.0,
    )
