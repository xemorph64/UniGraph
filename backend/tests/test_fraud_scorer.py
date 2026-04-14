import asyncio

from backend.app.services.fraud_scorer import fraud_scorer


def test_structuring_rule_is_flagged_for_near_ctr_amount():
    txn = {
        "txn_id": "TXN-TEST-001",
        "from_account": "ACC-001",
        "to_account": "ACC-002",
        "amount": 900000.0,
        "channel": "NEFT",
        "velocity_1h": 1,
        "velocity_24h": 3,
        "is_dormant": False,
        "device_account_count": 1,
    }

    result = asyncio.run(fraud_scorer.score_transaction(txn))

    assert "STRUCTURING" in result["rule_violations"]
    assert result["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_should_create_alert_above_threshold():
    should_alert = asyncio.run(fraud_scorer.should_create_alert({"risk_score": 60}))
    should_not_alert = asyncio.run(
        fraud_scorer.should_create_alert({"risk_score": 59})
    )

    assert should_alert is True
    assert should_not_alert is False


def test_structuring_smurfing_repeated_sub_threshold_transfers_trigger_alert():
    txn = {
        "txn_id": "TXN-ST-007",
        "from_account": "ACC-ST-SND-007",
        "to_account": "ACC-ST-RECV-001",
        "amount": 49000.0,
        "channel": "UPI",
        "velocity_1h": 1,
        "velocity_24h": 7,
        "is_dormant": False,
        "device_account_count": 1,
    }

    result = asyncio.run(fraud_scorer.score_transaction(txn))

    assert "STRUCTURING" in result["rule_violations"]
    assert result["risk_score"] >= 60


def test_primary_fraud_type_uses_priority_when_multiple_rules_trigger():
    txn = {
        "txn_id": "TXN-MULTI-001",
        "from_account": "ACC-MULTI-001",
        "to_account": "ACC-MULTI-002",
        "amount": 250000.0,
        "channel": "UPI",
        "velocity_1h": 6,
        "velocity_24h": 12,
        "is_dormant": False,
        "device_account_count": 5,
    }

    result = asyncio.run(fraud_scorer.score_transaction(txn))

    assert "RAPID_LAYERING" in result["rule_violations"]
    assert "MULE_NETWORK" in result["rule_violations"]
    assert result["primary_fraud_type"] == "MULE_NETWORK"


def test_primary_fraud_type_is_none_when_no_typology_rules_fire():
    txn = {
        "txn_id": "TXN-LOW-001",
        "from_account": "ACC-LOW-001",
        "to_account": "ACC-LOW-002",
        "amount": 5000.0,
        "channel": "UPI",
        "velocity_1h": 1,
        "velocity_24h": 1,
        "is_dormant": False,
        "device_account_count": 1,
    }

    result = asyncio.run(fraud_scorer.score_transaction(txn))

    assert result["rule_violations"] == []
    assert result["primary_fraud_type"] is None


def test_primary_fraud_type_uses_strongest_typology_contribution():
    txn = {
        "txn_id": "TXN-CONTRIB-001",
        "from_account": "ACC-CONTRIB-001",
        "to_account": "ACC-CONTRIB-002",
        "amount": 49000.0,
        "channel": "UPI",
        "velocity_1h": 1,
        "velocity_24h": 7,
        "is_dormant": False,
        "device_account_count": 5,
    }

    result = asyncio.run(fraud_scorer.score_transaction(txn))

    assert "STRUCTURING" in result["rule_violations"]
    assert "MULE_NETWORK" in result["rule_violations"]
    assert result["primary_fraud_type"] == "STRUCTURING"


def test_primary_fraud_type_tie_break_uses_priority_order():
    selected = fraud_scorer._select_primary_fraud_type(
        ["RAPID_LAYERING", "DORMANT_AWAKENING"],
        typology_contributions={
            "RAPID_LAYERING": 45.0,
            "DORMANT_AWAKENING": 45.0,
        },
    )

    assert selected == "DORMANT_AWAKENING"


def test_score_transaction_marks_ml_blended_source(monkeypatch):
    async def fake_graph_features(_txn):
        return {}

    async def fake_graph_subgraph(_txn):
        return None

    async def fake_ml_result(_txn, _rule_violations, graph_features=None, graph_subgraph=None):
        return {
            "gnn_fraud_probability": 0.81,
            "if_anomaly_score": 0.22,
            "xgboost_risk_score": 72,
            "shap_top3": ["amount_log", "velocity_1h", "pagerank"],
            "model_version": "test-ml-v1",
            "timestamp": "2026-04-13T00:00:00Z",
        }

    monkeypatch.setattr(fraud_scorer, "_build_graph_features", fake_graph_features)
    monkeypatch.setattr(fraud_scorer, "_build_graph_subgraph", fake_graph_subgraph)
    monkeypatch.setattr(fraud_scorer, "_score_with_ml_service", fake_ml_result)

    txn = {
        "txn_id": "TXN-SOURCE-ML",
        "from_account": "ACC-SOURCE-001",
        "to_account": "ACC-SOURCE-002",
        "amount": 120000.0,
        "channel": "IMPS",
        "velocity_1h": 1,
        "velocity_24h": 1,
        "is_dormant": False,
        "device_account_count": 1,
    }

    result = asyncio.run(fraud_scorer.score_transaction(txn))

    assert result["scoring_source"] == "ml_blended"
    assert result["model_version"] == "test-ml-v1"


def test_score_transaction_marks_rules_fallback_source(monkeypatch):
    async def fake_graph_features(_txn):
        return {}

    async def fake_graph_subgraph(_txn):
        return None

    async def fake_ml_unavailable(_txn, _rule_violations, graph_features=None, graph_subgraph=None):
        return None

    monkeypatch.setattr(fraud_scorer, "_build_graph_features", fake_graph_features)
    monkeypatch.setattr(fraud_scorer, "_build_graph_subgraph", fake_graph_subgraph)
    monkeypatch.setattr(fraud_scorer, "_score_with_ml_service", fake_ml_unavailable)

    txn = {
        "txn_id": "TXN-SOURCE-FALLBACK",
        "from_account": "ACC-SOURCE-003",
        "to_account": "ACC-SOURCE-004",
        "amount": 75000.0,
        "channel": "UPI",
        "velocity_1h": 1,
        "velocity_24h": 1,
        "is_dormant": False,
        "device_account_count": 1,
    }

    result = asyncio.run(fraud_scorer.score_transaction(txn))

    assert result["scoring_source"] == "rules_fallback"
    assert result["model_version"] == "unigraph-demo-v1.0"
