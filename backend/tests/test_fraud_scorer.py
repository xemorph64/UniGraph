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
