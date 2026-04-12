from backend.app.services.rule_evaluator import rule_evaluator


def test_structuring_rule_for_near_ctr_amount():
    result = rule_evaluator.evaluate(
        {
            "amount": 900000.0,
            "channel": "NEFT",
            "velocity_1h": 1,
            "velocity_24h": 3,
            "is_dormant": False,
            "device_account_count": 1,
        }
    )

    assert "STRUCTURING" in result.rule_violations
    assert result.risk_score >= 22


def test_smurfing_rule_for_repeated_sub_threshold_amounts():
    result = rule_evaluator.evaluate(
        {
            "amount": 49000.0,
            "channel": "UPI",
            "velocity_1h": 1,
            "velocity_24h": 7,
            "is_dormant": False,
            "device_account_count": 1,
        }
    )

    assert "STRUCTURING" in result.rule_violations
    assert result.risk_score >= 60


def test_round_tripping_rule_marker():
    result = rule_evaluator.evaluate(
        {
            "from_account": "ACC-01",
            "to_account": "ACC-02",
            "description": "Settlement ROUND_TRIP",
            "amount": 300000.0,
            "channel": "IMPS",
            "velocity_1h": 1,
            "velocity_24h": 1,
            "is_dormant": False,
            "device_account_count": 1,
        }
    )

    assert "ROUND_TRIPPING" in result.rule_violations
    assert result.risk_score >= 50


def test_multiple_rules_trigger_for_high_velocity_and_device_sharing():
    result = rule_evaluator.evaluate(
        {
            "amount": 250000.0,
            "channel": "UPI",
            "velocity_1h": 6,
            "velocity_24h": 12,
            "is_dormant": False,
            "device_account_count": 5,
        }
    )

    assert "RAPID_LAYERING" in result.rule_violations
    assert "MULE_NETWORK" in result.rule_violations
