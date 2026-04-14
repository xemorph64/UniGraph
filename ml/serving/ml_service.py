import os
import sys
import time
import json
import math
import re
import csv
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path
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
if_scaler = None

fallback_ready = False
fallback_version = "fallback-linear-v1"
fraud_coef = None
risk_coef = None
feature_mean = None
feature_std = None
serving_mode = "initializing"
STRICT_THREE_MODEL_MODE = str(
    os.getenv("ML_REQUIRE_ALL_MODELS", "true")
).strip().lower() in {"1", "true", "yes", "y", "on"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _all_three_models_loaded() -> bool:
    return gnn_model is not None and if_model is not None and xgb_model is not None


def _missing_required_models() -> list[str]:
    missing: list[str] = []
    if gnn_model is None:
        missing.append("gnn")
    if if_model is None:
        missing.append("if")
    if xgb_model is None:
        missing.append("xgb")
    return missing


def _channel_risk(channel: str) -> float:
    score_map = {
        "UPI": 0.30,
        "IMPS": 0.35,
        "NEFT": 0.40,
        "RTGS": 0.55,
        "SWIFT": 0.70,
        "CASH": 0.80,
    }
    return score_map.get(str(channel).upper(), 0.40)


def _build_feature_vector(txn: dict) -> list[float]:
    amount = float(txn.get("amount", 0.0) or 0.0)
    velocity_1h = float(txn.get("velocity_1h", 0) or 0)
    velocity_24h = float(txn.get("velocity_24h", 0) or 0)
    device_account_count = float(txn.get("device_account_count", 1) or 1)
    is_dormant = 1.0 if txn.get("is_dormant", False) else 0.0
    channel_risk = _channel_risk(txn.get("channel", "IMPS"))
    log_amount = math.log1p(max(amount, 0.0))

    # Intercept + compact feature basis for quick local model fitting.
    return [
        1.0,
        log_amount,
        channel_risk,
        velocity_1h,
        velocity_24h,
        device_account_count,
        is_dormant,
    ]


def _to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y", "t"}


NOW_INTERVAL_RE = re.compile(
    r"NOW\(\)\s*-\s*INTERVAL\s*'(?P<value>\d+)\s+(?P<unit>minute|minutes|hour|hours|day|days)'",
    re.IGNORECASE,
)


def _split_sql_row(row: str) -> list[str]:
    values = []
    buff = []
    in_quote = False
    paren_depth = 0
    i = 0

    while i < len(row):
        ch = row[i]

        if ch == "'":
            if in_quote and i + 1 < len(row) and row[i + 1] == "'":
                buff.append("''")
                i += 2
                continue
            in_quote = not in_quote
            buff.append(ch)
            i += 1
            continue

        if not in_quote:
            if ch == "(":
                paren_depth += 1
            elif ch == ")" and paren_depth > 0:
                paren_depth -= 1
            elif ch == "," and paren_depth == 0:
                values.append("".join(buff).strip())
                buff = []
                i += 1
                continue

        buff.append(ch)
        i += 1

    if buff:
        values.append("".join(buff).strip())

    return values


def _parse_now_expr(token: str, now_ref: datetime) -> datetime:
    token = token.strip()
    if token.upper() == "NOW()":
        return now_ref

    match = NOW_INTERVAL_RE.fullmatch(token)
    if not match:
        return now_ref

    value = int(match.group("value"))
    unit = match.group("unit").lower()
    if unit.startswith("minute"):
        return now_ref - timedelta(minutes=value)
    if unit.startswith("hour"):
        return now_ref - timedelta(hours=value)
    return now_ref - timedelta(days=value)


def _parse_sql_literal(token: str, now_ref: datetime):
    token = token.strip()
    upper = token.upper()

    if upper == "NULL":
        return None
    if upper == "TRUE":
        return True
    if upper == "FALSE":
        return False
    if upper.startswith("NOW()"):
        return _parse_now_expr(token, now_ref)
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if re.fullmatch(r"-?\d+\.\d+", token):
        return float(token)
    return token


def _extract_insert_blocks(sql_text: str, table: str) -> list[str]:
    pattern = re.compile(
        rf"INSERT\s+INTO\s+{re.escape(table)}\s+VALUES\s*(?P<body>.*?);",
        re.IGNORECASE | re.DOTALL,
    )
    return [match.group("body") for match in pattern.finditer(sql_text)]


def _extract_insert_rows(block: str) -> list[str]:
    rows = []
    depth = 0
    start_idx = None

    for idx, ch in enumerate(block):
        if ch == "(":
            if depth == 0:
                start_idx = idx + 1
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start_idx is not None:
                rows.append(block[start_idx:idx].strip())
                start_idx = None

    return rows


def _has_recent_path(history: list[dict], current_ts: datetime, source: str, target: str, max_depth: int = 5) -> bool:
    if not source or not target:
        return False

    lower_bound = current_ts - timedelta(hours=24)
    adjacency = {}
    for txn in history:
        if txn["txn_timestamp"] < lower_bound:
            continue
        adjacency.setdefault(txn["sender_account"], set()).add(txn["receiver_account"])

    queue = deque([(source, 0)])
    visited = {source}

    while queue:
        node, depth = queue.popleft()
        if depth > max_depth:
            continue
        for nxt in adjacency.get(node, set()):
            if nxt == target:
                return True
            if nxt in visited:
                continue
            visited.add(nxt)
            queue.append((nxt, depth + 1))

    return False


def _load_training_rows_from_fraud_scenarios(sql_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    text = sql_path.read_text(encoding="utf-8")
    now_ref = datetime.now(timezone.utc)

    dormant_accounts = {}
    expected_alert_txns = set()
    expected_alert_scores = {}

    for block in _extract_insert_blocks(text, "accounts"):
        for row in _extract_insert_rows(block):
            cols = [_parse_sql_literal(value, now_ref) for value in _split_sql_row(row)]
            if len(cols) < 6:
                continue
            account_id = str(cols[0])
            dormant_accounts[account_id] = bool(cols[5])

    for block in _extract_insert_blocks(text, "alerts"):
        for row in _extract_insert_rows(block):
            cols = [_parse_sql_literal(value, now_ref) for value in _split_sql_row(row)]
            if len(cols) < 5:
                continue
            txn_id = str(cols[1])
            expected_alert_txns.add(txn_id)
            if isinstance(cols[4], (int, float)):
                expected_alert_scores[txn_id] = float(cols[4])

    txns = []
    for block in _extract_insert_blocks(text, "transactions"):
        for row in _extract_insert_rows(block):
            cols = [_parse_sql_literal(value, now_ref) for value in _split_sql_row(row)]
            if len(cols) < 12:
                continue
            ts = cols[5] if isinstance(cols[5], datetime) else now_ref
            txns.append(
                {
                    "txn_id": str(cols[0]),
                    "sender_account": str(cols[1]),
                    "receiver_account": str(cols[2]),
                    "amount": float(cols[3] or 0.0),
                    "channel": str(cols[4] or "IMPS").upper(),
                    "txn_timestamp": ts,
                    "device_id": str(cols[6] or "DEV-UNKNOWN"),
                    "narration": str(cols[11] or "Transfer"),
                }
            )

    txns.sort(key=lambda item: item["txn_timestamp"])

    x_rows = []
    y_fraud = []
    y_risk = []
    history = []
    seen_device_accounts = {}

    for txn in txns:
        current_ts = txn["txn_timestamp"]
        window_1h = current_ts - timedelta(hours=1)
        window_24h = current_ts - timedelta(hours=24)

        sender_participation_1h = sum(
            1
            for prev in history
            if prev["txn_timestamp"] >= window_1h
            and (
                prev["sender_account"] == txn["sender_account"]
                or prev["receiver_account"] == txn["sender_account"]
            )
        )
        sender_participation_24h = sum(
            1
            for prev in history
            if prev["txn_timestamp"] >= window_24h
            and (
                prev["sender_account"] == txn["sender_account"]
                or prev["receiver_account"] == txn["sender_account"]
            )
        )
        receiver_structuring_count_24h = sum(
            1
            for prev in history
            if prev["txn_timestamp"] >= window_24h
            and prev["receiver_account"] == txn["receiver_account"]
            and 40000 <= prev["amount"] < 50000
        )
        if 40000 <= txn["amount"] < 50000:
            receiver_structuring_count_24h += 1

        round_trip_closure = _has_recent_path(
            history=history,
            current_ts=current_ts,
            source=txn["receiver_account"],
            target=txn["sender_account"],
        )

        description = txn["narration"]
        if round_trip_closure and "ROUND_TRIP" not in description.upper():
            description = f"{description} ROUND_TRIP"

        dormant_sender = bool(dormant_accounts.get(txn["sender_account"], False))
        dormant_receiver = bool(dormant_accounts.get(txn["receiver_account"], False))
        is_dormant = dormant_sender or dormant_receiver

        existing_accounts = seen_device_accounts.get(txn["device_id"], set())
        device_accounts = set(existing_accounts)
        device_accounts.update({txn["sender_account"], txn["receiver_account"]})
        seen_device_accounts[txn["device_id"]] = device_accounts

        velocity_1h = sender_participation_1h + 1
        velocity_24h = max(sender_participation_24h + 1, receiver_structuring_count_24h)
        device_account_count = max(1, len(device_accounts))

        enriched = {
            "amount": txn["amount"],
            "channel": txn["channel"],
            "velocity_1h": velocity_1h,
            "velocity_24h": velocity_24h,
            "device_account_count": device_account_count,
            "is_dormant": is_dormant,
            "description": description,
        }

        txn_id = txn["txn_id"]
        is_fraud = 1.0 if txn_id in expected_alert_txns else 0.0

        if txn_id in expected_alert_scores:
            risk_score = float(expected_alert_scores[txn_id])
        elif txn_id in expected_alert_txns:
            risk_score = 75.0
        else:
            risk_score = 22.0
            if enriched["velocity_1h"] >= 2 and enriched["amount"] >= 500000:
                risk_score += 14
            if 40000 <= enriched["amount"] < 50000 and enriched["velocity_24h"] >= 3:
                risk_score += 10
            if enriched["is_dormant"]:
                risk_score += 8
            risk_score = min(risk_score, 59.0)

        x_rows.append(_build_feature_vector(enriched))
        y_fraud.append(is_fraud)
        y_risk.append(risk_score)
        history.append(txn)

    if not x_rows:
        raise RuntimeError("No parseable rows in fraud_scenarios SQL training file")

    return (
        np.array(x_rows, dtype=np.float64),
        np.array(y_fraud, dtype=np.float64),
        np.array(y_risk, dtype=np.float64),
    )


def _load_training_rows_from_csv(csv_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x_rows = []
    y_fraud = []
    y_risk = []

    with csv_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            try:
                amount = float(row.get("amount") or 0.0)
                channel = str(row.get("channel") or "IMPS")
                risk_score = float(row.get("risk_score") or 0.0)
                ml_score = float(row.get("ml_score") or 0.0)
                is_fraud = 1.0 if _to_bool(row.get("is_fraud", "")) else 0.0
                is_flagged = _to_bool(row.get("is_flagged", ""))
                high_risk = is_flagged or is_fraud > 0.0 or risk_score >= 70 or ml_score >= 70

                enriched = {
                    "amount": amount,
                    "channel": channel,
                    "velocity_1h": 5 if high_risk else (3 if risk_score >= 50 else 0),
                    "velocity_24h": 10 if high_risk else (5 if risk_score >= 50 else 0),
                    "device_account_count": 4 if high_risk else 1,
                    "is_dormant": bool(high_risk and amount >= 200000 and channel in {"RTGS", "SWIFT"}),
                }
                x_rows.append(_build_feature_vector(enriched))
                y_fraud.append(is_fraud)
                y_risk.append(risk_score)
            except Exception:
                continue

    if not x_rows:
        raise RuntimeError("No parseable rows in CSV training file")
    return np.array(x_rows, dtype=np.float64), np.array(y_fraud, dtype=np.float64), np.array(y_risk, dtype=np.float64)


def _load_training_rows_from_sql(sql_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    text = sql_path.read_text(encoding="utf-8")
    rows = re.findall(r"INSERT INTO transactions VALUES \((.*?)\);", text, re.DOTALL)
    x_rows = []
    y_fraud = []
    y_risk = []
    for row in rows:
        parts = [p.strip().strip("'").strip('"') for p in row.split(",")]
        if len(parts) < 24:
            continue
        try:
            amount = float(parts[6]) if parts[6] else 0.0
            channel = parts[8] if parts[8] else "IMPS"
            risk_score = float(parts[18]) if parts[18] else 0.0
            is_fraud = 1.0 if parts[22].strip().lower() in {"true", "1", "yes", "y", "t"} else 0.0
            is_flagged = parts[20].strip().lower() in {"true", "1", "yes", "y", "t"}
            ml_score = float(parts[19]) if parts[19] else 0.0
            high_risk = is_flagged or is_fraud > 0.0 or risk_score >= 70 or ml_score >= 70

            enriched = {
                "amount": amount,
                "channel": channel,
                "velocity_1h": 5 if high_risk else (3 if risk_score >= 50 else 0),
                "velocity_24h": 10 if high_risk else (5 if risk_score >= 50 else 0),
                "device_account_count": 4 if high_risk else 1,
                "is_dormant": bool(high_risk and amount >= 200000 and channel in {"RTGS", "SWIFT"}),
            }
            x_rows.append(_build_feature_vector(enriched))
            y_fraud.append(is_fraud)
            y_risk.append(risk_score)
        except Exception:
            continue

    if not x_rows:
        raise RuntimeError("No parseable rows in SQL training file")
    return np.array(x_rows, dtype=np.float64), np.array(y_fraud, dtype=np.float64), np.array(y_risk, dtype=np.float64)


def _sigmoid(arr: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-arr))


def _build_runtime_xgb_feature_row(
    gnn_score: float,
    if_score: float,
    default_graph: dict,
    default_txn: dict,
    default_acct: dict,
    rule_violations: list[str],
) -> list[float]:
    amount = float(default_txn.get("amount", 0.0) or 0.0)
    is_dormant = 1.0 if bool(default_txn.get("is_dormant", False)) else 0.0

    return [
        1.0,
        math.log1p(max(amount, 0.0)),
        _channel_risk(default_txn.get("channel", "IMPS")),
        float(default_txn.get("velocity_1h", 0) or 0),
        float(default_txn.get("velocity_24h", 0) or 0),
        float(default_txn.get("device_account_count", 1) or 1),
        is_dormant,
        float(gnn_score),
        float(if_score),
        float(default_graph.get("connected_suspicious_nodes", 0) or 0),
        float(default_graph.get("community_risk_score", 0.0) or 0.0),
        float(default_graph.get("pagerank", 0.0) or 0.0),
        float(default_graph.get("betweenness_centrality", 0.0) or 0.0),
        float(default_graph.get("in_degree_24h", 0) or 0),
        float(default_graph.get("out_degree_24h", 0) or 0),
        float(default_graph.get("shortest_path_to_fraud", 0.0) or 0.0),
        float(default_graph.get("neighbor_fraud_ratio", 0.0) or 0.0),
        float(default_acct.get("customer_age", 0.0) or 0.0),
        float(default_acct.get("account_age_days", 0) or 0),
        float(default_acct.get("kyc_tier", 1) or 1),
        float(default_acct.get("avg_monthly_balance", 0.0) or 0.0),
        float(default_txn.get("transaction_count_30d", 0) or 0),
        float(default_txn.get("avg_txn_amount_30d", 0.0) or 0.0),
        float(default_txn.get("device_count_30d", 0) or 0),
        float(default_txn.get("ip_count_30d", 0) or 0),
        float(default_txn.get("avg_txn_amount", 0.0) or 0.0),
        float(default_txn.get("std_txn_amount", 0.0) or 0.0),
        float(default_txn.get("max_txn_amount", 0.0) or 0.0),
        float(default_txn.get("min_txn_amount", 0.0) or 0.0),
        float(default_txn.get("hour_of_day", 0) or 0),
        float(default_txn.get("day_of_week", 0) or 0),
        float(bool(default_txn.get("is_weekend", False))),
        float(bool(default_txn.get("is_holiday", False))),
        float(default_txn.get("geo_distance_from_home", 0.0) or 0.0),
        float(bool(default_txn.get("device_risk_flag", False))),
        float(default_txn.get("counterparty_risk_score", 0.0) or 0.0),
        float(bool(default_txn.get("is_international", False))),
        float(default_txn.get("channel_switch_count", 0) or 0),
        float(len(rule_violations or [])),
    ]


class _LocalIsolationForestAdapter:
    def __init__(self, model, scaler=None):
        self.model = model
        self.scaler = scaler

    def score_to_0_100(self, features: np.ndarray) -> float:
        arr = np.asarray(features, dtype=np.float64)
        if self.scaler is not None:
            arr = self.scaler.transform(arr)

        if hasattr(self.model, "score_samples"):
            raw = self.model.score_samples(arr)
        elif hasattr(self.model, "decision_function"):
            raw = self.model.decision_function(arr)
        else:
            raise RuntimeError("Isolation model does not support score_samples")

        raw = np.asarray(raw, dtype=np.float64).reshape(-1)
        normalized = _sigmoid(raw * 8.0)
        return float(np.clip(np.mean(normalized) * 100.0, 0.0, 100.0))


class _LocalXGBoostAdapter:
    def __init__(self, model):
        self.model = model

    def prepare_features(
        self,
        gnn_score: float,
        if_score: float,
        default_graph: dict,
        default_txn: dict,
        default_acct: dict,
        rule_violations: list[str],
    ) -> np.ndarray:
        row = _build_runtime_xgb_feature_row(
            gnn_score,
            if_score,
            default_graph,
            default_txn,
            default_acct,
            rule_violations,
        )
        return np.asarray([row], dtype=np.float64)

    def predict_risk_score(self, features: np.ndarray) -> int:
        arr = np.asarray(features, dtype=np.float64)

        if hasattr(self.model, "predict_proba"):
            probs = np.asarray(self.model.predict_proba(arr), dtype=np.float64)
            if probs.ndim == 2 and probs.shape[1] >= 2:
                score = float(probs[0, 1]) * 100.0
            else:
                score = float(probs.reshape(-1)[0]) * 100.0
        elif hasattr(self.model, "predict"):
            pred = float(np.asarray(self.model.predict(arr), dtype=np.float64).reshape(-1)[0])
            score = pred * 100.0 if pred <= 1.0 else pred
        else:
            score = 50.0

        return int(np.clip(round(score), 0, 100))


def _bootstrap_tabular_models(*, bootstrap_if: bool, bootstrap_xgb: bool) -> bool:
    global if_model, xgb_model, if_scaler, model_version

    if not bootstrap_if and not bootstrap_xgb:
        return True

    data_source = _repo_root() / "fraud_scenarios.sql"
    if not data_source.exists():
        print(f"Bootstrap source not found: {data_source}")
        return False

    try:
        x, y_fraud, y_risk = _load_training_rows_from_fraud_scenarios(data_source)

        if bootstrap_if:
            from sklearn.ensemble import IsolationForest
            from sklearn.preprocessing import StandardScaler

            x_no_bias = x[:, 1:]
            scaler = StandardScaler()
            x_scaled = scaler.fit_transform(x_no_bias)

            contamination = float(np.clip(np.mean(y_fraud), 0.01, 0.35))
            if_estimator = IsolationForest(
                n_estimators=200,
                contamination=contamination,
                random_state=42,
            )
            if_estimator.fit(x_scaled)

            if_scaler = scaler
            if_model = _LocalIsolationForestAdapter(if_estimator, scaler)

        if bootstrap_xgb:
            y_class = (y_fraud >= 0.5).astype(np.int64)
            if np.unique(y_class).size < 2:
                y_class = (y_risk >= 60.0).astype(np.int64)
            if np.unique(y_class).size < 2:
                median_risk = float(np.median(y_risk))
                y_class = (y_risk >= median_risk).astype(np.int64)

            model_tag = "xgb"
            estimator = None
            try:
                from xgboost import XGBClassifier

                estimator = XGBClassifier(
                    n_estimators=120,
                    max_depth=4,
                    learning_rate=0.08,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    objective="binary:logistic",
                    eval_metric="logloss",
                    random_state=42,
                    n_jobs=1,
                    verbosity=0,
                )
            except Exception:
                from sklearn.ensemble import GradientBoostingClassifier

                estimator = GradientBoostingClassifier(random_state=42)
                model_tag = "gb"

            estimator.fit(x, y_class)
            xgb_model = _LocalXGBoostAdapter(estimator)
            model_version = (
                f"unigraph-ml-service-bootstrap-{model_tag}-v1-fraud-scenarios"
            )

        print(
            "Bootstrapped tabular models from "
            f"{data_source} with {x.shape[0]} rows "
            f"(bootstrap_if={bootstrap_if}, bootstrap_xgb={bootstrap_xgb})"
        )
        return True
    except Exception as exc:
        print(f"Could not bootstrap tabular models: {exc}")
        return False


def _bootstrap_gnn_model() -> bool:
    global gnn_model, model_version

    data_source = _repo_root() / "fraud_scenarios.sql"
    if not data_source.exists():
        print(f"Graph bootstrap source not found: {data_source}")
        return False

    try:
        import torch
        from ml.models.graphsage.model import GraphSAGEFraudDetector

        x, y_fraud, y_risk = _load_training_rows_from_fraud_scenarios(data_source)
        x_features = x[:, 1:] if x.shape[1] > 1 else x

        y_class = (y_fraud >= 0.5).astype(np.float32)
        if np.unique(y_class).size < 2:
            y_class = (y_risk >= 60.0).astype(np.float32)
        if np.unique(y_class).size < 2:
            median_risk = float(np.median(y_risk))
            y_class = (y_risk >= median_risk).astype(np.float32)

        in_features = int(x_features.shape[1])
        model = GraphSAGEFraudDetector(
            in_features=in_features,
            hidden_dim=64,
            out_features=32,
            num_layers=2,
            dropout=0.1,
        )

        x_tensor = torch.tensor(x_features, dtype=torch.float32)
        y_tensor = torch.tensor(y_class, dtype=torch.float32).view(-1, 1)

        optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)
        criterion = torch.nn.BCELoss()

        model.train()
        epochs = min(200, max(40, int(2000 / max(1, x_tensor.size(0)))))
        for _ in range(epochs):
            optimizer.zero_grad()
            preds = model(x_tensor, edge_index=None)
            loss = criterion(preds, y_tensor)
            loss.backward()
            optimizer.step()

        model.eval()
        gnn_model = model

        if model_version == "unigraph-v1.0.0":
            model_version = "unigraph-ml-service-bootstrap-graphsage-v1-fraud-scenarios"

        print(
            "Bootstrapped GraphSAGE model from "
            f"{data_source} with {x_features.shape[0]} rows"
        )
        return True
    except Exception as exc:
        print(f"Could not bootstrap GraphSAGE model: {exc}")
        return False


def _align_xgb_features(features: np.ndarray) -> np.ndarray:
    """Align feature width to trained XGBoost expectation.

    Some legacy artifacts were trained with 39 features while newer runtime
    paths build a 26-feature vector. To preserve compatibility, we pad/truncate
    to the trained model width when available.
    """
    if xgb_model is None or not hasattr(xgb_model, "model"):
        return features

    expected = getattr(xgb_model.model, "n_features_in_", None)
    if expected is None:
        return features

    expected = int(expected)
    current = int(features.shape[1])

    if current == expected:
        return features
    if current < expected:
        padding = np.zeros((features.shape[0], expected - current), dtype=features.dtype)
        return np.hstack([features, padding])
    return features[:, :expected]


def _align_if_features(features: np.ndarray) -> np.ndarray:
    """Align IF feature width to scaler/model expectation."""
    expected = None

    if if_scaler is not None and hasattr(if_scaler, "n_features_in_"):
        expected = int(getattr(if_scaler, "n_features_in_"))
    elif if_model is not None and hasattr(if_model, "model"):
        expected = int(getattr(if_model.model, "n_features_in_", features.shape[1]))

    if expected is None:
        return features

    current = int(features.shape[1])
    if current == expected:
        return features
    if current < expected:
        padding = np.zeros((features.shape[0], expected - current), dtype=features.dtype)
        return np.hstack([features, padding])
    return features[:, :expected]


def _train_fallback_models() -> None:
    global fallback_ready, fraud_coef, risk_coef, feature_mean, feature_std
    global model_version, serving_mode
    data_source = _repo_root() / "fraud_scenarios.sql"

    if not data_source.exists():
        return

    x, y_fraud, y_risk = _load_training_rows_from_fraud_scenarios(data_source)

    x_no_bias = x[:, 1:]

    # Closed-form least squares fits for fast startup and deterministic scoring.
    fraud_coef = np.linalg.pinv(x) @ y_fraud
    risk_coef = np.linalg.pinv(x) @ y_risk

    feature_mean = x_no_bias.mean(axis=0)
    feature_std = x_no_bias.std(axis=0)
    feature_std[feature_std < 1e-6] = 1.0

    fallback_ready = True
    serving_mode = "fallback_linear"
    model_version = f"unigraph-ml-service-{fallback_version}-fraud-scenarios"
    print(f"Trained fallback models from {data_source} with {x.shape[0]} rows")


class MLScoringRequest(BaseModel):
    enriched_transaction: dict
    graph_features: Optional[dict] = None
    graph_subgraph: Optional[dict] = None


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
    global if_scaler, fallback_ready, serving_mode

    # Reset state on startup/reload to avoid stale globals from previous attempts.
    gnn_model = None
    if_model = None
    xgb_model = None
    shap_explainer = None
    feature_engineer = None
    if_scaler = None
    fallback_ready = False
    serving_mode = "initializing"

    artifact_if_loaded = False
    artifact_xgb_loaded = False

    try:
        import torch
        from ml.models.graphsage.model import GraphSAGEFraudDetector

        gnn_path = os.path.join(model_dir, "graphsage_model.pt")
        if not os.path.exists(gnn_path):
            alt_gnn_path = os.path.join(model_dir, "graphsage.pt")
            if os.path.exists(alt_gnn_path):
                gnn_path = alt_gnn_path
        if os.path.exists(gnn_path):
            checkpoint = torch.load(gnn_path, map_location="cpu")
            loaded_gnn_model = GraphSAGEFraudDetector(
                in_features=checkpoint.get("config", {}).get("in_features", 32),
                hidden_dim=checkpoint.get("config", {}).get("hidden_dim", 128),
                out_features=checkpoint.get("config", {}).get("out_features", 64),
            )
            loaded_gnn_model.load_state_dict(checkpoint["model_state_dict"])
            loaded_gnn_model.eval()
            gnn_model = loaded_gnn_model
            print("Loaded GraphSAGE model")
    except Exception as e:
        gnn_model = None
        print(f"Could not load GNN model: {e}")

    if gnn_model is None:
        _bootstrap_gnn_model()

    try:
        if_path = os.path.join(model_dir, "isolation_forest_model.pkl")
        if os.path.exists(if_path):
            import pickle

            with open(if_path, "rb") as f:
                payload = pickle.load(f)

            candidate_model = payload
            candidate_scaler = None
            if isinstance(payload, dict):
                candidate_model = payload.get("model")
                candidate_scaler = payload.get("scaler")

            if candidate_model is None:
                raise RuntimeError("Isolation Forest payload missing model")

            if hasattr(candidate_model, "score_to_0_100"):
                if_model = candidate_model
                if_scaler = candidate_scaler
            elif hasattr(candidate_model, "score_samples") or hasattr(
                candidate_model, "decision_function"
            ):
                if_model = _LocalIsolationForestAdapter(
                    candidate_model,
                    candidate_scaler,
                )
                if_scaler = candidate_scaler
            else:
                raise RuntimeError("Unsupported Isolation Forest payload type")

            artifact_if_loaded = True
            print("Loaded Isolation Forest model")
        else:
            print(f"Isolation Forest artifact not found at {if_path}")
    except Exception as e:
        print(f"Could not load IF model: {e}")

    try:
        xgb_path = os.path.join(model_dir, "xgboost_model.pkl")
        if os.path.exists(xgb_path):
            import pickle

            with open(xgb_path, "rb") as f:
                payload = pickle.load(f)

            candidate_model = payload
            if isinstance(payload, dict):
                candidate_model = payload.get("model")
                explain = payload.get("shap_explainer")
                if shap_explainer is None and hasattr(explain, "explain"):
                    shap_explainer = explain

            if candidate_model is None:
                raise RuntimeError("XGBoost payload missing model")

            if hasattr(candidate_model, "prepare_features") and hasattr(
                candidate_model,
                "predict_risk_score",
            ):
                xgb_model = candidate_model
            elif hasattr(candidate_model, "predict_proba") or hasattr(
                candidate_model,
                "predict",
            ):
                xgb_model = _LocalXGBoostAdapter(candidate_model)
            else:
                raise RuntimeError("Unsupported XGBoost payload type")

            artifact_xgb_loaded = True
            print("Loaded XGBoost model")
        else:
            print(f"XGBoost artifact not found at {xgb_path}")
    except Exception as e:
        print(f"Could not load XGBoost model: {e}")

    try:
        from ml.data.feature_engineering import FeatureEngineer

        feature_engineer = FeatureEngineer()
        print("Loaded Feature Engineer")
    except Exception as e:
        print(f"Could not load Feature Engineer: {e}")

    # First preference: artifact models. Second preference: in-memory bootstrap.
    # Last resort: deterministic linear fallback.
    if if_model is None or xgb_model is None:
        bootstrap_ok = _bootstrap_tabular_models(
            bootstrap_if=if_model is None,
            bootstrap_xgb=xgb_model is None,
        )
        if not bootstrap_ok and (if_model is None or xgb_model is None):
            try:
                _train_fallback_models()
            except Exception as e:
                print(f"Could not train fallback models: {e}")

    all_three_loaded = _all_three_models_loaded()
    missing_required_models = _missing_required_models()

    if STRICT_THREE_MODEL_MODE and not all_three_loaded:
        serving_mode = "strict_blocked_missing_models"
    elif all_three_loaded:
        if artifact_if_loaded and artifact_xgb_loaded:
            serving_mode = "artifact_models"
        elif artifact_if_loaded or artifact_xgb_loaded:
            serving_mode = "mixed_artifact_bootstrap"
        else:
            serving_mode = "bootstrap_tabular"
    elif if_model is not None and xgb_model is not None:
        if artifact_if_loaded and artifact_xgb_loaded:
            serving_mode = "artifact_models_tabular_only"
        elif artifact_if_loaded or artifact_xgb_loaded:
            serving_mode = "mixed_artifact_bootstrap_tabular_only"
        else:
            serving_mode = "bootstrap_tabular_only"
    elif fallback_ready:
        serving_mode = "fallback_linear"
    else:
        serving_mode = "heuristic_only"

    print(
        "ML service operating mode: "
        f"{serving_mode}, model_version={model_version}, "
        f"strict_three_model_mode={STRICT_THREE_MODEL_MODE}, "
        f"missing_required_models={missing_required_models}"
    )


async def score_transaction(
    enriched_txn: dict,
    graph_features: Optional[dict] = None,
    graph_subgraph: Optional[dict] = None,
) -> dict:
    if STRICT_THREE_MODEL_MODE:
        missing_required_models = _missing_required_models()
        if missing_required_models:
            raise RuntimeError(
                "strict_three_model_mode_enabled_missing_models:"
                + ",".join(missing_required_models)
            )

    start_time = time.time()

    txn_id = enriched_txn.get("txn_id", "unknown")

    gnn_score = 0.5
    if gnn_model is not None:
        try:
            import torch

            if graph_subgraph and graph_subgraph.get("node_features"):
                node_features = graph_subgraph.get("node_features") or []
                edge_pairs = graph_subgraph.get("edge_index") or []
                center_index = int(graph_subgraph.get("center_index", 0) or 0)

                x_tensor = torch.FloatTensor(node_features)
                edge_tensor = None
                if edge_pairs:
                    edge_tensor = torch.LongTensor(edge_pairs).t().contiguous()

                with torch.no_grad():
                    probs = gnn_model.predict_proba(x_tensor, edge_index=edge_tensor)
                    if probs.dim() == 0:
                        gnn_score = float(probs.item())
                    else:
                        safe_center_index = max(0, min(center_index, probs.shape[0] - 1))
                        gnn_score = float(probs[safe_center_index].item())
            else:
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
            tx_array = np.array([tx_features], dtype=np.float64)
            tx_array = _align_if_features(tx_array)

            if hasattr(if_model, "score_to_0_100"):
                if_score_0_100 = float(if_model.score_to_0_100(tx_array))
                if_score = float(np.clip(if_score_0_100 / 100.0, 0.0, 1.0))
            else:
                model_input = tx_array
                if if_scaler is not None:
                    model_input = if_scaler.transform(model_input)

                if hasattr(if_model, "score_samples"):
                    raw_scores = if_model.score_samples(model_input)
                elif hasattr(if_model, "decision_function"):
                    raw_scores = if_model.decision_function(model_input)
                else:
                    raise RuntimeError("Unsupported IF scorer type")

                raw_score = float(np.asarray(raw_scores, dtype=np.float64).reshape(-1)[0])
                if_score = float(np.clip(1.0 / (1.0 + np.exp(12.0 * raw_score)), 0.0, 1.0))
        except Exception as e:
            print(f"IF scoring error: {e}")

    compact_features = np.array(_build_feature_vector(enriched_txn), dtype=np.float64)
    tx_features = extract_tx_features(enriched_txn)
    default_graph = graph_features or {}
    default_txn = {
        "amount": enriched_txn.get("amount", 0.0),
        "channel": enriched_txn.get("channel", "IMPS"),
        "velocity_1h": enriched_txn.get("velocity_1h", 0),
        "velocity_24h": enriched_txn.get("velocity_24h", 0),
        "device_account_count": enriched_txn.get("device_account_count", 1),
        "is_dormant": bool(enriched_txn.get("is_dormant", False)),
        "transaction_count_30d": enriched_txn.get("transaction_count_30d", 0),
        "avg_txn_amount_30d": enriched_txn.get("avg_txn_amount_30d", 0.0),
        "device_count_30d": enriched_txn.get("device_count_30d", 0),
        "ip_count_30d": enriched_txn.get("ip_count_30d", 0),
        "avg_txn_amount": enriched_txn.get("avg_txn_amount", 0.0),
        "std_txn_amount": enriched_txn.get("std_txn_amount", 0.0),
        "max_txn_amount": enriched_txn.get("max_txn_amount", 0.0),
        "min_txn_amount": enriched_txn.get("min_txn_amount", 0.0),
        "hour_of_day": enriched_txn.get("hour_of_day", 0),
        "day_of_week": enriched_txn.get("day_of_week", 0),
        "is_weekend": bool(enriched_txn.get("is_weekend", False)),
        "is_holiday": bool(enriched_txn.get("is_holiday", False)),
        "geo_distance_from_home": enriched_txn.get("geo_distance_from_home", 0.0),
        "device_risk_flag": bool(enriched_txn.get("device_risk_flag", False)),
        "counterparty_risk_score": enriched_txn.get("counterparty_risk_score", 0.0),
        "is_international": bool(enriched_txn.get("is_international", False)),
        "amount_zscore": enriched_txn.get("amount_zscore", 0.0),
        "channel_switch_count": enriched_txn.get("channel_switch_count", 0),
    }
    default_acct = {
        "customer_age": enriched_txn.get("customer_age", 0.0),
        "account_age_days": enriched_txn.get("account_age_days", 0),
        "kyc_tier": enriched_txn.get("kyc_tier", 1),
        "avg_monthly_balance": enriched_txn.get("avg_monthly_balance", 0.0),
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
            xgb_features = _align_xgb_features(xgb_features)
            risk_score = xgb_model.predict_risk_score(xgb_features)
        except Exception as e:
            print(f"XGBoost scoring error: {e}")
            risk_score = int((gnn_score * 0.4 + if_score * 0.2 + 0.5 * 0.4) * 100)
    else:
        if fallback_ready and fraud_coef is not None and risk_coef is not None:
            linear_fraud = float(compact_features @ fraud_coef)
            gnn_score = float(np.clip(linear_fraud, 0.0, 1.0))

            if feature_mean is not None and feature_std is not None:
                z = np.abs((compact_features[1:] - feature_mean) / feature_std)
                if_score = float(np.clip(np.mean(z) / 3.0, 0.0, 1.0))

            linear_risk = float(compact_features @ risk_coef)
            blended_risk = 0.75 * np.clip(linear_risk, 0.0, 100.0) + 25.0 * if_score
            risk_score = int(np.clip(round(blended_risk), 0, 100))
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
            xgb_features = _align_xgb_features(xgb_features)
            shap_result = shap_explainer.explain(xgb_features)
            shap_top3 = shap_result.get("shap_top3", [])
        except Exception as e:
            print(f"SHAP error: {e}")

    if not shap_top3 and fallback_ready:
        shap_top3 = [
            f"amount_log: {round(float(compact_features[1]), 3)}",
            f"channel_risk: {round(float(compact_features[2]), 3)}",
            f"velocity_1h: {int(compact_features[3])}",
        ]

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
        "avg_txn_amount_30d",
        "device_count_30d",
        "ip_count_30d",
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
    if STRICT_THREE_MODEL_MODE:
        missing_required_models = _missing_required_models()
        if missing_required_models:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "strict_three_model_mode_enabled",
                    "missing_models": missing_required_models,
                    "serving_mode": serving_mode,
                },
            )

    result = await score_transaction(
        request.enriched_transaction,
        request.graph_features,
        request.graph_subgraph,
    )
    return MLScoringResponse(**result)


@app.post("/api/v1/ml/score/batch")
async def score_batch(requests: list[MLScoringRequest]):
    if STRICT_THREE_MODEL_MODE:
        missing_required_models = _missing_required_models()
        if missing_required_models:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "strict_three_model_mode_enabled",
                    "missing_models": missing_required_models,
                    "serving_mode": serving_mode,
                },
            )

    results = []
    for req in requests:
        result = await score_transaction(
            req.enriched_transaction,
            req.graph_features,
            req.graph_subgraph,
        )
        results.append(result)
    return {"results": results, "count": len(results)}


@app.get("/api/v1/ml/health")
async def health():
    missing_required_models = _missing_required_models()
    if STRICT_THREE_MODEL_MODE:
        ready_for_scoring = len(missing_required_models) == 0
    else:
        ready_for_scoring = (
            _all_three_models_loaded()
            or (if_model is not None and xgb_model is not None)
            or fallback_ready
        )

    return {
        "status": "healthy" if ready_for_scoring else "degraded",
        "model_version": model_version,
        "serving_mode": serving_mode,
        "strict_three_model_mode": STRICT_THREE_MODEL_MODE,
        "required_models": ["gnn", "if", "xgb"],
        "missing_required_models": missing_required_models,
        "ready_for_scoring": ready_for_scoring,
        "gnn_loaded": gnn_model is not None,
        "if_loaded": if_model is not None,
        "xgb_loaded": xgb_model is not None,
        "fallback_ready": fallback_ready,
    }


@app.get("/metrics")
async def metrics():
    return {
        "model_version": model_version,
        "serving_mode": serving_mode,
        "strict_three_model_mode": STRICT_THREE_MODEL_MODE,
        "all_three_models_loaded": _all_three_models_loaded(),
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
