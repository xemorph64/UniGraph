from backend.app.contracts.bridge_quality_gate import (
    build_bridge_quality_artifact,
    compute_dropped_invalid_rate,
    evaluate_dropped_invalid_policy,
)


def test_compute_dropped_invalid_rate_with_enriched_denominator():
    stats = {"dropped_invalid": 2, "enriched_seen": 100}
    assert compute_dropped_invalid_rate(stats, denominator_key="enriched_seen") == 0.02


def test_compute_dropped_invalid_rate_with_zero_denominator_is_zero():
    stats = {"dropped_invalid": 7, "enriched_seen": 0}
    assert compute_dropped_invalid_rate(stats, denominator_key="enriched_seen") == 0.0


def test_evaluate_dropped_invalid_policy_reports_failures():
    stats = {"dropped_invalid": 3, "enriched_seen": 100, "messages_total": 120}
    failures, drop_rate, dropped_invalid, denominator = evaluate_dropped_invalid_policy(
        stats,
        max_dropped_invalid=1,
        max_dropped_invalid_rate=0.02,
        rate_denominator="enriched_seen",
    )

    assert len(failures) == 2
    assert drop_rate == 0.03
    assert dropped_invalid == 3
    assert denominator == 100


def test_build_bridge_quality_artifact_contains_expected_fields():
    stats = {"dropped_invalid": 0, "enriched_seen": 10, "messages_total": 10}
    artifact = build_bridge_quality_artifact(
        stats=stats,
        max_dropped_invalid=0,
        max_dropped_invalid_rate=0.0,
        rate_denominator="enriched_seen",
        policy_failures=[],
        exit_code=0,
    )

    assert artifact["status"] == "PASS"
    assert artifact["quality_gate"]["observed_dropped_invalid"] == 0
    assert artifact["quality_gate"]["observed_dropped_invalid_rate"] == 0.0
