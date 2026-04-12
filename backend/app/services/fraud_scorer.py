"""
Fraud scoring pipeline that combines rule-based and ML signals.
In demo mode, uses simplified heuristics when ML service is unavailable.
"""

import asyncio
import random
import uuid
import httpx
from datetime import datetime
from datetime import timezone
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
    def __init__(self):
        self._ml_score_url = f"{settings.ML_SERVICE_URL.rstrip('/')}/api/v1/ml/score"
        self._ml_health_url = f"{settings.ML_SERVICE_URL.rstrip('/')}/api/v1/ml/health"

    async def _score_with_ml_service(self, txn: dict, rule_violations: list[str]) -> Optional[dict]:
        payload = {
            "enriched_transaction": {
                "txn_id": txn.get("txn_id"),
                "amount": float(txn.get("amount", 0.0)),
                "channel": txn.get("channel", "IMPS"),
                "velocity_1h": int(txn.get("velocity_1h", 0)),
                "velocity_24h": int(txn.get("velocity_24h", 0)),
                "device_account_count": int(txn.get("device_account_count", 1)),
                "is_dormant": bool(txn.get("is_dormant", False)),
                "rule_violations": rule_violations,
            },
            "graph_features": {
                "connected_suspicious_nodes": int(txn.get("connected_suspicious_nodes", 0)),
                "community_risk_score": float(txn.get("community_risk_score", 0.0)),
                "community_id": int(txn.get("community_id", 0)),
                "pagerank": float(txn.get("pagerank", 0.0)),
                "betweenness_centrality": float(txn.get("betweenness_centrality", 0.0)),
            },
        }
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.post(self._ml_score_url, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.warning(
                "ml_service_unavailable_fallback_to_rules",
                endpoint=self._ml_score_url,
                error=str(exc),
            )
            return None

    async def get_ml_readiness(self) -> dict:
        """Return current ML readiness state for health probes."""
        readiness = {
            "ml_service_reachable": False,
            "ml_service_url": settings.ML_SERVICE_URL,
            "ml_model_version": None,
            "fallback_mode_available": True,
        }

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(self._ml_health_url)
                response.raise_for_status()
                payload = response.json()
                readiness.update(
                    {
                        "ml_service_reachable": payload.get("status") == "healthy",
                        "ml_model_version": payload.get("model_version"),
                        "ml_health": payload,
                    }
                )
        except Exception as exc:
            readiness["ml_error"] = str(exc)

        return readiness

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
        to_account = txn.get("to_account", "")
        description = str(txn.get("description", "")).upper()
        is_dormant = txn.get("is_dormant", False)
        device_account_count = txn.get("device_account_count", 1)
        velocity_1h = txn.get("velocity_1h", 0)
        velocity_24h = txn.get("velocity_24h", 0)

        if amount > 500000:
            risk_score += 20
            shap_contributions.append(f"high_amount_₹{amount / 100000:.1f}L: +20")
        elif amount > 100000:
            risk_score += 10
            shap_contributions.append(f"elevated_amount_₹{amount / 100000:.1f}L: +10")

        if velocity_1h >= 5:
            risk_score += 25
            rule_violations.append("RAPID_LAYERING")
            shap_contributions.append(f"velocity_1h_{velocity_1h}_txns: +25")
        elif velocity_1h >= 3:
            risk_score += 12
            shap_contributions.append(f"elevated_velocity_1h_{velocity_1h}: +12")

        if 800000 <= amount <= 990000:
            risk_score += 22
            rule_violations.append("STRUCTURING")
            shap_contributions.append("amount_near_ctr_threshold: +22")

        if is_dormant:
            risk_score += 35
            rule_violations.append("DORMANT_AWAKENING")
            shap_contributions.append("dormant_account_activity: +35")

        if device_account_count > 3:
            risk_score += 30
            rule_violations.append("MULE_NETWORK")
            shap_contributions.append(
                f"device_shared_{device_account_count}_accounts: +30"
            )

        if channel in ["CASH", "SWIFT"]:
            risk_score += 8
            shap_contributions.append(f"high_risk_channel_{channel}: +8")

        # Round-tripping indicator used in synthetic and replay tests.
        if (from_account and to_account and from_account == to_account) or (
            "ROUND_TRIP" in description
        ):
            risk_score += 28
            if "ROUND_TRIPPING" not in rule_violations:
                rule_violations.append("ROUND_TRIPPING")
            shap_contributions.append("round_tripping_pattern: +28")

        if velocity_24h >= 10:
            risk_score += 15
            shap_contributions.append(f"velocity_24h_{velocity_24h}_txns: +15")

        rule_based_score = min(round(risk_score), 100)

        graph_features = {
            "connected_suspicious_nodes": int(txn.get("connected_suspicious_nodes", 0)),
            "community_risk_score": float(txn.get("community_risk_score", 0.0)),
            "community_id": int(txn.get("community_id", 0)),
            "pagerank": float(txn.get("pagerank", 0.0)),
            "betweenness_centrality": float(txn.get("betweenness_centrality", 0.0)),
        }

        if from_account:
            try:
                extracted = await neo4j_service.get_scoring_graph_features(from_account)
                graph_features.update(extracted)
            except Exception as exc:
                logger.warning(
                    "graph_feature_extraction_failed",
                    account_id=from_account,
                    error=str(exc),
                )

        txn_for_ml = dict(txn)
        txn_for_ml.update(graph_features)

        ml_result = await self._score_with_ml_service(txn_for_ml, rule_violations)
        if ml_result:
            ml_score = max(0, min(100, int(round(float(ml_result.get("xgboost_risk_score", 0))))))
            # Blend learned score with deterministic rule signals to preserve typology explainability.
            risk_score = min(100, round(ml_score * 0.8 + rule_based_score * 0.2))
            gnn_fraud_probability = float(ml_result.get("gnn_fraud_probability", min(risk_score / 100, 1.0)))
            if_anomaly_score = float(ml_result.get("if_anomaly_score", min(risk_score / 120, 1.0)))
            xgboost_risk_score = ml_score
            shap_top3 = list(ml_result.get("shap_top3") or shap_contributions[:3])
            model_version = str(ml_result.get("model_version", "ml-service-unknown"))
            scoring_timestamp = str(ml_result.get("timestamp", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")))
            logger.info(
                "ml_service_score_applied",
                txn_id=txn.get("txn_id"),
                model_version=model_version,
                connected_suspicious_nodes=graph_features.get(
                    "connected_suspicious_nodes", 0
                ),
                community_risk_score=graph_features.get("community_risk_score", 0.0),
            )
        else:
            risk_score = rule_based_score
            gnn_fraud_probability = min(risk_score / 100, 1.0)
            if_anomaly_score = min(risk_score / 120, 1.0)
            xgboost_risk_score = risk_score
            shap_top3 = shap_contributions[:3]
            model_version = "unigraph-demo-v1.0"
            scoring_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

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
            "shap_top3": shap_top3,
            "gnn_fraud_probability": gnn_fraud_probability,
            "if_anomaly_score": if_anomaly_score,
            "xgboost_risk_score": xgboost_risk_score,
            "model_version": model_version,
            "scoring_timestamp": scoring_timestamp,
            "graph_features": graph_features,
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
