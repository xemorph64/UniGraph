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
from .rule_evaluator import rule_evaluator
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

TYPOLOGY_PRIORITY = [
    "MULE_NETWORK",
    "DORMANT_AWAKENING",
    "RAPID_LAYERING",
    "ROUND_TRIPPING",
    "STRUCTURING",
]


class FraudScorer:
    def __init__(self):
        self._ml_score_url = f"{settings.ML_SERVICE_URL.rstrip('/')}/api/v1/ml/score"
        self._ml_health_url = f"{settings.ML_SERVICE_URL.rstrip('/')}/api/v1/ml/health"

    @staticmethod
    def _base_graph_features(txn: dict) -> dict:
        return {
            "connected_suspicious_nodes": int(txn.get("connected_suspicious_nodes", 0)),
            "community_risk_score": float(txn.get("community_risk_score", 0.0)),
            "community_id": int(txn.get("community_id", 0)),
            "pagerank": float(txn.get("pagerank", 0.0)),
            "betweenness_centrality": float(txn.get("betweenness_centrality", 0.0)),
        }

    async def _build_graph_features(self, txn: dict) -> dict:
        graph_features = self._base_graph_features(txn)
        from_account = txn.get("from_account", "")

        if not from_account:
            return graph_features

        try:
            extracted = await neo4j_service.get_scoring_graph_features(from_account)
            graph_features.update(extracted)
        except Exception as exc:
            logger.warning(
                "graph_feature_extraction_failed",
                account_id=from_account,
                error=str(exc),
            )

        return graph_features

    @staticmethod
    def _blend_ml_with_rules(
        ml_result: dict,
        rule_based_score: int,
        rule_violations: list[str],
        shap_contributions: list[str],
    ) -> dict:
        ml_score = max(0, min(100, int(round(float(ml_result.get("xgboost_risk_score", 0))))))

        # Blend learned score with deterministic rule signals to preserve typology explainability.
        risk_score = min(100, round(ml_score * 0.8 + rule_based_score * 0.2))

        # If deterministic rules already indicate an alert-worthy pattern,
        # preserve that floor even when ML predicts lower risk.
        if rule_violations and rule_based_score >= 60:
            risk_score = max(risk_score, rule_based_score)

        return {
            "risk_score": risk_score,
            "gnn_fraud_probability": float(
                ml_result.get("gnn_fraud_probability", min(risk_score / 100, 1.0))
            ),
            "if_anomaly_score": float(
                ml_result.get("if_anomaly_score", min(risk_score / 120, 1.0))
            ),
            "xgboost_risk_score": ml_score,
            "shap_top3": list(ml_result.get("shap_top3") or shap_contributions[:3]),
            "model_version": str(ml_result.get("model_version", "ml-service-unknown")),
            "scoring_timestamp": str(
                ml_result.get(
                    "timestamp",
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                )
            ),
        }

    @staticmethod
    def _fallback_rule_only(
        rule_based_score: int,
        shap_contributions: list[str],
    ) -> dict:
        risk_score = rule_based_score
        return {
            "risk_score": risk_score,
            "gnn_fraud_probability": min(risk_score / 100, 1.0),
            "if_anomaly_score": min(risk_score / 120, 1.0),
            "xgboost_risk_score": risk_score,
            "shap_top3": shap_contributions[:3],
            "model_version": "unigraph-demo-v1.0",
            "scoring_timestamp": datetime.now(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
        }

    @staticmethod
    def _risk_level_and_recommendation(risk_score: int) -> tuple[str, str]:
        if risk_score >= 90:
            return "CRITICAL", "BLOCK"
        if risk_score >= 80:
            return "HIGH", "HOLD"
        if risk_score >= 60:
            return "MEDIUM", "REVIEW"
        return "LOW", "ALLOW"

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
        rule_eval = rule_evaluator.evaluate(txn)
        risk_score = rule_eval.risk_score
        rule_violations = list(rule_eval.rule_violations)
        shap_contributions = list(rule_eval.shap_contributions)

        rule_based_score = min(round(risk_score), 100)
        graph_features = await self._build_graph_features(txn)

        txn_for_ml = dict(txn)
        txn_for_ml.update(graph_features)

        ml_result = await self._score_with_ml_service(txn_for_ml, rule_violations)
        if ml_result:
            blended = self._blend_ml_with_rules(
                ml_result=ml_result,
                rule_based_score=rule_based_score,
                rule_violations=rule_violations,
                shap_contributions=shap_contributions,
            )
            risk_score = blended["risk_score"]
            gnn_fraud_probability = blended["gnn_fraud_probability"]
            if_anomaly_score = blended["if_anomaly_score"]
            xgboost_risk_score = blended["xgboost_risk_score"]
            shap_top3 = blended["shap_top3"]
            model_version = blended["model_version"]
            scoring_timestamp = blended["scoring_timestamp"]
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
            fallback = self._fallback_rule_only(
                rule_based_score=rule_based_score,
                shap_contributions=shap_contributions,
            )
            risk_score = fallback["risk_score"]
            gnn_fraud_probability = fallback["gnn_fraud_probability"]
            if_anomaly_score = fallback["if_anomaly_score"]
            xgboost_risk_score = fallback["xgboost_risk_score"]
            shap_top3 = fallback["shap_top3"]
            model_version = fallback["model_version"]
            scoring_timestamp = fallback["scoring_timestamp"]

        risk_level, recommendation = self._risk_level_and_recommendation(risk_score)

        primary_fraud_type = self._select_primary_fraud_type(rule_violations)

        result = {
            "txn_id": txn.get("txn_id", str(uuid.uuid4())),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "rule_violations": rule_violations,
            "primary_fraud_type": primary_fraud_type,
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

    @staticmethod
    def _select_primary_fraud_type(rule_violations: list[str]) -> Optional[str]:
        if not rule_violations:
            return None

        unique_rules = set(rule_violations)
        for typology in TYPOLOGY_PRIORITY:
            if typology in unique_rules:
                return typology

        # Preserve backward compatibility for any unknown future rule names.
        return rule_violations[0]

    async def should_create_alert(self, score_result: dict) -> bool:
        return score_result["risk_score"] >= 60


fraud_scorer = FraudScorer()
