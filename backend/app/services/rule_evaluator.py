"""Deterministic Python rule evaluator for fraud typology detection.

This replaces external Drools rule evaluation with in-process, testable Python
logic while preserving rule outputs consumed by the scoring pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuleEvaluation:
    risk_score: float
    rule_violations: list[str]
    shap_contributions: list[str]


class PythonRuleEvaluator:
    """Evaluate deterministic fraud rules and return scoring primitives."""

    def evaluate(self, txn: dict) -> RuleEvaluation:
        risk_score = 0.0
        rule_violations: list[str] = []
        shap_contributions: list[str] = []

        amount = float(txn.get("amount", 0.0) or 0.0)
        channel = str(txn.get("channel", "IMPS") or "IMPS")
        from_account = str(txn.get("from_account", "") or "")
        to_account = str(txn.get("to_account", "") or "")
        description = str(txn.get("description", "") or "").upper()
        is_dormant = bool(txn.get("is_dormant", False))
        device_account_count = int(txn.get("device_account_count", 1) or 1)
        velocity_1h = int(txn.get("velocity_1h", 0) or 0)
        velocity_24h = int(txn.get("velocity_24h", 0) or 0)
        round_trip_marker = "ROUND_TRIP" in description

        if amount > 500000:
            risk_score += 25
            shap_contributions.append(f"high_amount_₹{amount / 100000:.1f}L: +25")
        elif amount > 100000:
            risk_score += 15
            shap_contributions.append(f"elevated_amount_₹{amount / 100000:.1f}L: +15")

        if velocity_1h >= 5:
            risk_score += 35
            rule_violations.append("RAPID_LAYERING")
            shap_contributions.append(f"velocity_1h_{velocity_1h}_txns: +35")
        elif velocity_1h >= 3:
            risk_score += 20
            shap_contributions.append(f"elevated_velocity_1h_{velocity_1h}: +20")

        # High-value transfers moving with bursty velocity indicate layering.
        if amount >= 100000 and velocity_1h >= 2 and not is_dormant:
            risk_score += 30
            if "RAPID_LAYERING" not in rule_violations:
                rule_violations.append("RAPID_LAYERING")
            shap_contributions.append(
                f"high_value_multi_hop_velocity_1h_{velocity_1h}: +30"
            )

        if 800000 <= amount <= 990000:
            risk_score += 25
            rule_violations.append("STRUCTURING")
            shap_contributions.append("amount_near_ctr_threshold: +25")

        # Smurfing signal for repeated sub-threshold transfers in a day.
        if 30000 <= amount < 50000 and velocity_24h >= 2:
            structuring_boost = min(70, 30 + max(0, velocity_24h - 2) * 12)
            risk_score += structuring_boost
            if "STRUCTURING" not in rule_violations:
                rule_violations.append("STRUCTURING")
            shap_contributions.append(
                f"repeated_sub_threshold_transfers_{velocity_24h}_in_24h: +{structuring_boost}"
            )

        if is_dormant:
            risk_score += 45
            rule_violations.append("DORMANT_AWAKENING")
            shap_contributions.append("dormant_account_activity: +45")

        if device_account_count > 3:
            risk_score += 30
            rule_violations.append("MULE_NETWORK")
            shap_contributions.append(
                f"device_shared_{device_account_count}_accounts: +30"
            )

        if channel in ["CASH", "SWIFT"]:
            risk_score += 8
            shap_contributions.append(f"high_risk_channel_{channel}: +8")

        # Round-tripping marker used by synthetic and replay ingestion flows.
        if (from_account and to_account and from_account == to_account) or round_trip_marker:
            risk_score += 35
            if "ROUND_TRIPPING" not in rule_violations:
                rule_violations.append("ROUND_TRIPPING")
            shap_contributions.append("round_tripping_pattern: +35")
            if amount >= 250000:
                risk_score += 15
                shap_contributions.append("high_value_round_trip: +15")

        if velocity_24h >= 10:
            risk_score += 15
            shap_contributions.append(f"velocity_24h_{velocity_24h}_txns: +15")

        return RuleEvaluation(
            risk_score=risk_score,
            rule_violations=rule_violations,
            shap_contributions=shap_contributions,
        )


rule_evaluator = PythonRuleEvaluator()
