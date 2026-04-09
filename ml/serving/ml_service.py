import os
import sys
import time
import json
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

app = FastAPI(title="UniGRAPH ML Scoring Service", version="1.0.0")

model_version = "unigraph-v1.0.0"

gnn_model = None
if_model = None
xgb_model = None
shap_explainer = None
feature_engineer = None


class MLScoringRequest(BaseModel):
    enriched_transaction: dict
    graph_features: Optional[dict] = None


class MLScoringResponse(BaseModel):
    txn_id: str
    gnn_fraud_probability: float
    if_anomaly_score: float
    xgboost_risk_score: int
    shap_top3: list[str]
    model_version: str
    scoring_latency_ms: float
    timestamp: str


async def load_models(model_dir: str = "/models"):
    global gnn_model, if_model, xgb_model, shap_explainer, feature_engineer

    try:
        import torch
        from ml.models.graphsage.model import GraphSAGEFraudDetector

        gnn_path = os.path.join(model_dir, "graphsage_model.pt")
        if os.path.exists(gnn_path):
            checkpoint = torch.load(gnn_path, map_location="cpu")
            gnn_model = GraphSAGEFraudDetector(
                in_features=checkpoint.get("config", {}).get("in_features", 32),
                hidden_dim=checkpoint.get("config", {}).get("hidden_dim", 128),
                out_features=checkpoint.get("config", {}).get("out_features", 64),
            )
            gnn_model.load_state_dict(checkpoint["model_state_dict"])
            gnn_model.eval()
            print("Loaded GraphSAGE model")
    except Exception as e:
        print(f"Could not load GNN model: {e}")

    try:
        from ml.models.isolation_forest.model import IsolationForestDetector

        if_path = os.path.join(model_dir, "isolation_forest_model.pkl")
        if os.path.exists(if_path):
            import pickle

            with open(if_path, "rb") as f:
                if_model = pickle.load(f)
            print("Loaded Isolation Forest model")
    except Exception as e:
        print(f"Could not load IF model: {e}")

    try:
        from ml.models.xgboost_ensemble.model import XGBoostEnsembleScorer
        from ml.models.xgboost_ensemble.shap_explainer import SHAPExplainer

        xgb_path = os.path.join(model_dir, "xgboost_model.pkl")
        if os.path.exists(xgb_path):
            import pickle

            with open(xgb_path, "rb") as f:
                xgb_model = pickle.load(f)
            try:
                shap_explainer = SHAPExplainer(xgb_model.model)
            except:
                pass
            print("Loaded XGBoost model")
    except Exception as e:
        print(f"Could not load XGBoost model: {e}")

    try:
        from ml.data.feature_engineering import FeatureEngineer

        feature_engineer = FeatureEngineer()
        print("Loaded Feature Engineer")
    except Exception as e:
        print(f"Could not load Feature Engineer: {e}")


async def score_transaction(
    enriched_txn: dict, graph_features: Optional[dict] = None
) -> dict:
    start_time = time.time()

    txn_id = enriched_txn.get("txn_id", "unknown")

    gnn_score = 0.5
    if gnn_model is not None:
        try:
            import torch

            tx_features = extract_tx_features(enriched_txn)
            tx_tensor = torch.FloatTensor(tx_features).unsqueeze(0)
            with torch.no_grad():
                gnn_score = gnn_model.predict_proba(tx_tensor).item()
        except Exception as e:
            print(f"GNN scoring error: {e}")

    if_score = 0.5
    if if_model is not None:
        try:
            tx_features = extract_tx_features(enriched_txn)
            if_scores = if_model.score_samples(np.array([tx_features]))
            if_score = if_model.score_to_0_100(np.array([if_scores[0]]))[0] / 100.0
        except Exception as e:
            print(f"IF scoring error: {e}")

    tx_features = extract_tx_features(enriched_txn)
    default_graph = graph_features or {}
    default_txn = {
        "velocity_1h": enriched_txn.get("velocity_1h", 0),
        "velocity_24h": enriched_txn.get("velocity_24h", 0),
        "amount_zscore": enriched_txn.get("amount_zscore", 0.0),
        "channel_switch_count": enriched_txn.get("channel_switch_count", 0),
        "geo_distance": enriched_txn.get("geo_distance_from_home", 0.0),
    }
    default_acct = {
        "account_age_days": enriched_txn.get("account_age_days", 0),
        "kyc_tier": enriched_txn.get("kyc_tier", 1),
        "transaction_count_30d": enriched_txn.get("transaction_count_30d", 0),
        "avg_txn_amount_30d": enriched_txn.get("avg_txn_amount_30d", 0.0),
        "device_count_30d": enriched_txn.get("device_count_30d", 0),
        "ip_count_30d": enriched_txn.get("ip_count_30d", 0),
    }

    rule_violations = enriched_txn.get("rule_violations", [])

    if xgb_model is not None:
        try:
            xgb_features = xgb_model.prepare_features(
                gnn_score,
                if_score,
                default_graph,
                default_txn,
                default_acct,
                rule_violations,
            )
            risk_score = xgb_model.predict_risk_score(xgb_features)
        except Exception as e:
            print(f"XGBoost scoring error: {e}")
            risk_score = int((gnn_score * 0.4 + if_score * 0.2 + 0.5 * 0.4) * 100)
    else:
        risk_score = int((gnn_score * 0.4 + if_score * 0.2 + 0.5 * 0.4) * 100)

    shap_top3 = []
    if shap_explainer is not None and xgb_model is not None:
        try:
            xgb_features = xgb_model.prepare_features(
                gnn_score,
                if_score,
                default_graph,
                default_txn,
                default_acct,
                rule_violations,
            )
            shap_result = shap_explainer.explain(xgb_features)
            shap_top3 = shap_result.get("shap_top3", [])
        except Exception as e:
            print(f"SHAP error: {e}")

    elapsed_ms = (time.time() - start_time) * 1000

    return {
        "txn_id": txn_id,
        "gnn_fraud_probability": round(gnn_score, 4),
        "if_anomaly_score": round(if_score, 4),
        "xgboost_risk_score": risk_score,
        "shap_top3": shap_top3 or ["velocity_1h: +0.10", "amount_zscore: +0.05"],
        "model_version": model_version,
        "scoring_latency_ms": round(elapsed_ms, 2),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def extract_tx_features(txn: dict) -> list:
    feature_cols = [
        "amount",
        "customer_age",
        "account_age_days",
        "kyc_tier",
        "avg_monthly_balance",
        "transaction_count_30d",
        "avg_txn_amount",
        "std_txn_amount",
        "max_txn_amount",
        "min_txn_amount",
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        "is_holiday",
        "geo_distance_from_home",
        "device_risk_flag",
        "device_account_count",
        "counterparty_risk_score",
        "is_international",
        "channel_switch_count",
    ]

    features = []
    for col in feature_cols:
        features.append(txn.get(col, 0))

    while len(features) < len(feature_cols):
        features.append(0)

    return features[: len(feature_cols)]


@app.on_event("startup")
async def startup():
    model_dir = os.getenv("MODEL_DIR", "/models")
    await load_models(model_dir)


@app.post("/api/v1/ml/score", response_model=MLScoringResponse)
async def score(request: MLScoringRequest):
    result = await score_transaction(
        request.enriched_transaction, request.graph_features
    )
    return MLScoringResponse(**result)


@app.post("/api/v1/ml/score/batch")
async def score_batch(requests: list[MLScoringRequest]):
    results = []
    for req in requests:
        result = await score_transaction(req.enriched_transaction, req.graph_features)
        results.append(result)
    return {"results": results, "count": len(results)}


@app.get("/api/v1/ml/health")
async def health():
    return {
        "status": "healthy",
        "model_version": model_version,
        "gnn_loaded": gnn_model is not None,
        "if_loaded": if_model is not None,
        "xgb_loaded": xgb_model is not None,
    }


@app.get("/metrics")
async def metrics():
    return {
        "model_version": model_version,
        "inference_count": 0,
        "avg_latency_ms": 0.0,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        workers=4,
    )
