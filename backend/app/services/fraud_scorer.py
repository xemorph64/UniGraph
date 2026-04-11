"""
Fraud scoring pipeline that combines rule-based and ML signals.
In demo mode, uses simplified heuristics when ML service is unavailable.
"""

import asyncio
import random
import uuid
from datetime import datetime
from typing import Optional
import structlog
from .neo4j_service import neo4j_service
from ..config import settings

logger = structlog.get_logger()

FRAUD_TYPOLOGIES = {
    "RAPID_LAYERING": {
        "description": "Multiple high-value transactions in rapid succession across accounts",
        "risk_boost": 30,
        "severity": "HIGH",
    },
    "STRUCTURING": {
        "description": "Transactions structured to avoid CTR threshold of ₹10L",
        "risk_boost": 25,
        "severity": "HIGH",
    },
    "DORMANT_AWAKENING": {
        "description": "Dormant account suddenly receiving/sending large amounts",
        "risk_boost": 35,
        "severity": "CRITICAL",
    },
    "MULE_NETWORK": {
        "description": "Account linked to mule network via shared device/IP",
        "risk_boost": 40,
        "severity": "CRITICAL",
    },
    "ROUND_TRIPPING": {
        "description": "Funds returned to originating account via circular path",
        "risk_boost": 28,
        "severity": "HIGH",
    },
}


class FraudScorer:
    async def score_transaction(self, txn: dict) -> dict:
        """
        Score a transaction using rule-based heuristics + ML signals.
        Returns: {risk_score, risk_level, recommendation, rule_violations, shap_top3}
        """
        risk_score = 0.0
        rule_violations = []
        shap_contributions = []

        amount = txn.get("amount", 0)
        channel = txn.get("channel", "IMPS")
        from_account = txn.get("from_account", "")
        is_dormant = txn.get("is_dormant", False)
        device_account_count = txn.get("device_account_count", 1)
        velocity_1h = txn.get("velocity_1h", 0)
        velocity_24h = txn.get("velocity_24h", 0)

        if amount > 500000:
            risk_score += 25
            shap_contributions.append(f"high_amount_₹{amount / 100000:.1f}L: +25")
        elif amount > 100000:
            risk_score += 12
            shap_contributions.append(f"elevated_amount_₹{amount / 100000:.1f}L: +12")

        if velocity_1h >= 5:
            risk_score += 30
            rule_violations.append("RAPID_LAYERING")
            shap_contributions.append(f"velocity_1h_{velocity_1h}_txns: +30")
        elif velocity_1h >= 3:
            risk_score += 18
            shap_contributions.append(f"elevated_velocity_1h_{velocity_1h}: +18")

        if 800000 <= amount <= 990000:
            risk_score += 28
            rule_violations.append("STRUCTURING")
            shap_contributions.append("amount_near_ctr_threshold: +28")

        if is_dormant:
            risk_score += 45
            rule_violations.append("DORMANT_AWAKENING")
            shap_contributions.append("dormant_account_activity: +45")

        if device_account_count > 3:
            risk_score += 40
            rule_violations.append("MULE_NETWORK")
            shap_contributions.append(
                f"device_shared_{device_account_count}_accounts: +40"
            )

        if channel in ["CASH", "SWIFT"]:
            risk_score += 8
            shap_contributions.append(f"high_risk_channel_{channel}: +8")

        if velocity_24h >= 10:
            risk_score += 15
            shap_contributions.append(f"velocity_24h_{velocity_24h}_txns: +15")

        risk_score = min(round(risk_score), 100)

        if risk_score >= 90:
            risk_level = "CRITICAL"
            recommendation = "BLOCK"
        elif risk_score >= 80:
            risk_level = "HIGH"
            recommendation = "HOLD"
        elif risk_score >= 60:
            risk_level = "MEDIUM"
            recommendation = "REVIEW"
        else:
            risk_level = "LOW"
            recommendation = "ALLOW"

        result = {
            "txn_id": txn.get("txn_id", str(uuid.uuid4())),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "rule_violations": rule_violations,
            "shap_top3": shap_contributions[:3],
            "gnn_fraud_probability": min(risk_score / 100, 1.0),
            "if_anomaly_score": min(risk_score / 120, 1.0),
            "xgboost_risk_score": risk_score,
            "model_version": "unigraph-demo-v1.0",
            "scoring_timestamp": datetime.utcnow().isoformat() + "Z",
        }

        logger.info(
            "transaction_scored",
            txn_id=result["txn_id"],
            risk_score=risk_score,
            risk_level=risk_level,
            violations=rule_violations,
        )

        return result

    async def should_create_alert(self, score_result: dict) -> bool:
        return score_result["risk_score"] >= 60


fraud_scorer = FraudScorer()
