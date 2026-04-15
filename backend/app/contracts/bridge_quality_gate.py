from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


def compute_dropped_invalid_rate(
    stats: Mapping[str, Any], *, denominator_key: str = "enriched_seen"
) -> float:
    dropped_invalid = int(stats.get("dropped_invalid") or 0)
    denominator = int(stats.get(denominator_key) or 0)
    if denominator <= 0:
        return 0.0
    return dropped_invalid / denominator


def evaluate_dropped_invalid_policy(
    stats: Mapping[str, Any],
    *,
    max_dropped_invalid: int,
    max_dropped_invalid_rate: float,
    rate_denominator: str,
) -> tuple[list[str], float, int, int]:
    dropped_invalid = int(stats.get("dropped_invalid") or 0)
    denominator = int(stats.get(rate_denominator) or 0)
    drop_rate = compute_dropped_invalid_rate(stats, denominator_key=rate_denominator)

    failures: list[str] = []
    if max_dropped_invalid >= 0 and dropped_invalid > max_dropped_invalid:
        failures.append(
            "dropped_invalid threshold exceeded "
            f"({dropped_invalid} > {max_dropped_invalid})"
        )

    if max_dropped_invalid_rate >= 0 and drop_rate > max_dropped_invalid_rate:
        failures.append(
            "dropped_invalid rate threshold exceeded "
            f"({drop_rate:.6f} > {max_dropped_invalid_rate:.6f}) using denominator={rate_denominator}"
        )

    return failures, drop_rate, dropped_invalid, denominator


def build_bridge_quality_artifact(
    *,
    stats: Mapping[str, Any],
    max_dropped_invalid: int,
    max_dropped_invalid_rate: float,
    rate_denominator: str,
    policy_failures: list[str],
    exit_code: int,
) -> dict[str, Any]:
    drop_rate = compute_dropped_invalid_rate(stats, denominator_key=rate_denominator)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "generated_at": now,
        "exit_code": int(exit_code),
        "status": "PASS" if exit_code == 0 else "FAIL",
        "stats": dict(stats),
        "quality_gate": {
            "max_dropped_invalid": int(max_dropped_invalid),
            "max_dropped_invalid_rate": float(max_dropped_invalid_rate),
            "rate_denominator": rate_denominator,
            "observed_dropped_invalid": int(stats.get("dropped_invalid") or 0),
            "observed_denominator": int(stats.get(rate_denominator) or 0),
            "observed_dropped_invalid_rate": drop_rate,
            "policy_failures": list(policy_failures),
        },
    }
