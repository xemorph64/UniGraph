from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import Optional
import time
import uuid

from ..services.fraud_scorer import fraud_scorer

router = APIRouter()


class FraudScoreRequest(BaseModel):
    transactionId: str
    channel: str = "IMPS"
    sourceAccount: str
    destinationAccount: str
    amount: float
    currency: str = "INR"
    timestamp: str
    customerId: str
    beneficiaryName: str
    deviceFingerprint: str = ""
    ipAddress: str = ""
    location: dict = {}
    referenceNumber: str = ""
    callbackUrl: Optional[str] = None
    is_dormant: bool = False
    device_account_count: int = 1
    velocity_1h: int = 0
    velocity_24h: int = 0


class FraudScoreResponse(BaseModel):
    transactionId: str
    riskScore: int
    riskLevel: str
    recommendation: str
    decisionLatencyMs: float
    reasons: list[str]
    graphEvidence: dict
    shapTopContributors: list[str]
    alertId: Optional[str]
    modelVersion: str
    scoringMode: str


@router.post("/score", response_model=FraudScoreResponse)
async def score_fraud(
    request: FraudScoreRequest,
    x_request_id: str = Header(...),
    x_idempotency_key: str = Header(...),
):
    """
    Real-time fraud scoring for Finacle payment processing.
    SLA: <200ms P99 latency.
    """
    start_time = time.time()

    txn_dict = {
        "txn_id": request.transactionId,
        "from_account": request.sourceAccount,
        "to_account": request.destinationAccount,
        "amount": request.amount,
        "channel": request.channel,
        "timestamp": request.timestamp,
        "is_dormant": request.is_dormant,
        "device_account_count": request.device_account_count,
        "velocity_1h": request.velocity_1h,
        "velocity_24h": request.velocity_24h,
    }

    score_result = await fraud_scorer.score_transaction(txn_dict)
    elapsed = (time.time() - start_time) * 1000

    response = FraudScoreResponse(
        transactionId=request.transactionId,
        riskScore=score_result["risk_score"],
        riskLevel=score_result["risk_level"],
        recommendation=score_result["recommendation"],
        decisionLatencyMs=elapsed,
        reasons=score_result["rule_violations"],
        graphEvidence={
            "connectedSuspiciousNodes": 0,
            "clusterRiskScore": 0.0,
            "pathToKnownFraudster": 0,
            "communityId": 0,
        },
        shapTopContributors=score_result["shap_top3"],
        alertId=f"ALT-{uuid.uuid4().hex[:8].upper()}"
        if score_result["risk_score"] >= 60
        else None,
        modelVersion=score_result["model_version"],
        scoringMode=score_result.get("scoring_mode", "unknown"),
    )

    return response
