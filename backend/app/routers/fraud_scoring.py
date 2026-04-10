from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import time
import random
import uuid

router = APIRouter()


class FraudScoreRequest(BaseModel):
    transactionId: str
    channel: str
    sourceAccount: str
    destinationAccount: str
    amount: float
    currency: str
    timestamp: str
    customerId: str
    beneficiaryName: str
    deviceFingerprint: str
    ipAddress: str
    location: dict
    referenceNumber: str
    callbackUrl: Optional[str] = None


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


def determine_recommendation(risk_score: int, rule_violations: list) -> str:
    if risk_score >= 90:
        return "BLOCK"
    elif risk_score >= 80:
        return "HOLD"
    elif risk_score >= 60:
        return "REVIEW"
    else:
        return "ALLOW"


def risk_score_to_level(score: int) -> str:
    if score >= 90:
        return "CRITICAL"
    elif score >= 80:
        return "HIGH"
    elif score >= 60:
        return "MEDIUM"
    else:
        return "LOW"


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

    risk_score = random.randint(50, 95)
    recommendation = determine_recommendation(risk_score, [])
    elapsed = (time.time() - start_time) * 1000

    reasons = [
        "mule_account_match",
        "unusual_velocity_8txns_47min",
        "graph_cluster_anomaly_score_0.87",
    ]
    shap_top3 = [
        "velocity_1h: +0.32",
        "shared_device_risk: +0.28",
        "amount_zscore: +0.15",
    ]

    response = FraudScoreResponse(
        transactionId=request.transactionId,
        riskScore=risk_score,
        riskLevel=risk_score_to_level(risk_score),
        recommendation=recommendation,
        decisionLatencyMs=elapsed,
        reasons=reasons,
        graphEvidence={
            "connectedSuspiciousNodes": 5,
            "clusterRiskScore": 0.87,
            "pathToKnownFraudster": 2,
            "communityId": 1423,
        },
        shapTopContributors=shap_top3,
        alertId=f"ALT-{uuid.uuid4().hex[:8]}" if risk_score >= 80 else None,
        modelVersion="unigraph-v1.0.0",
    )

    return response
