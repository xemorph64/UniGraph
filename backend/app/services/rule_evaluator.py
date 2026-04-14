"""Deterministic Python rule evaluator for fraud typology detection.

This replaces external Drools rule evaluation with in-process, testable Python
logic while preserving rule outputs consumed by the scoring pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


@dataclass
class RuleEvaluation:
    risk_score: float
    rule_violations: list[str]
    shap_contributions: list[str]
    typology_contributions: dict[str, float] = field(default_factory=dict)


class PythonRuleEvaluator:
    """Evaluate deterministic fraud rules and return scoring primitives."""

    def evaluate(self, txn: dict) -> RuleEvaluation:
        risk_score = 0.0
        rule_violations: list[str] = []
        shap_contributions: list[str] = []
        typology_contributions: dict[str, float] = {}

        def add_typology_contribution(typology: str, score_delta: float) -> None:
            if typology not in rule_violations:
                rule_violations.append(typology)
            typology_contributions[typology] = (
                typology_contributions.get(typology, 0.0) + score_delta
            )

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
            risk_score += 20
            shap_contributions.append(
                f"High transfer amount (₹{amount / 100000:.1f}L): +20"
            )
        elif amount > 100000:
            risk_score += 10
            shap_contributions.append(
                f"Elevated transfer amount (₹{amount / 100000:.1f}L): +10"
            )

        if velocity_1h >= 5:
            risk_score += 25
            add_typology_contribution("RAPID_LAYERING", 25)
            shap_contributions.append(
                f"High 1-hour transaction velocity ({velocity_1h} txns): +25"
            )
        elif velocity_1h >= 3:
            risk_score += 12
            shap_contributions.append(
                f"Elevated 1-hour transaction velocity ({velocity_1h} txns): +12"
            )

        # High-value transfers moving with bursty velocity indicate layering.
        if amount >= 500000 and velocity_1h >= 2 and not is_dormant:
            risk_score += 40
            add_typology_contribution("RAPID_LAYERING", 40)
            shap_contributions.append(
                f"High-value multi-hop burst ({velocity_1h} txns in 1h): +40"
            )

        if 800000 <= amount <= 990000:
            risk_score += 22
            add_typology_contribution("STRUCTURING", 22)
            shap_contributions.append("Amount near CTR reporting threshold: +22")

        # Smurfing signal for repeated sub-threshold transfers in a day.
        if 40000 <= amount < 50000 and velocity_24h >= 3:
            structuring_boost = min(65, 24 + max(0, velocity_24h - 3) * 9)
            risk_score += structuring_boost
            add_typology_contribution("STRUCTURING", structuring_boost)
            shap_contributions.append(
                f"Repeated sub-threshold transfers ({velocity_24h} in 24h): +{structuring_boost}"
            )

        if is_dormant:
            risk_score += 45
            add_typology_contribution("DORMANT_AWAKENING", 45)
            shap_contributions.append("Dormant account reactivation: +45")

        if device_account_count > 3:
            risk_score += 30
            add_typology_contribution("MULE_NETWORK", 30)
            shap_contributions.append(
                f"Shared device across {device_account_count} accounts: +30"
            )

        if channel in ["CASH", "SWIFT"]:
            risk_score += 8
            shap_contributions.append(f"High-risk channel usage ({channel}): +8")

        # Round-tripping marker used by synthetic and replay ingestion flows.
        if (from_account and to_account and from_account == to_account) or round_trip_marker:
            risk_score += 35
            add_typology_contribution("ROUND_TRIPPING", 35)
            shap_contributions.append("Round-tripping movement pattern: +35")
            if amount >= 250000:
                risk_score += 15
                add_typology_contribution("ROUND_TRIPPING", 15)
                shap_contributions.append("High-value round-trip amount: +15")

        if velocity_24h >= 10:
            risk_score += 15
            shap_contributions.append(
                f"High 24-hour transaction velocity ({velocity_24h} txns): +15"
            )

        return RuleEvaluation(
            risk_score=risk_score,
            rule_violations=rule_violations,
            shap_contributions=shap_contributions,
            typology_contributions=typology_contributions,
        )


rule_evaluator = PythonRuleEvaluator()
