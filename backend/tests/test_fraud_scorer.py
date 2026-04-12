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
