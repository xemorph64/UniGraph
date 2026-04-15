#!/usr/bin/env python3
"""Verify strict replay bridge stats artifact against malformed-drop thresholds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.contracts.bridge_quality_gate import (  # noqa: E402
    build_bridge_quality_artifact,
    evaluate_dropped_invalid_policy,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify bridge replay artifact malformed-drop thresholds"
    )
    parser.add_argument("--stats-file", type=Path, required=True)
    parser.add_argument("--max-dropped-invalid", type=int, default=0)
    parser.add_argument("--max-dropped-invalid-rate", type=float, default=0.0)
    parser.add_argument(
        "--dropped-invalid-rate-denominator",
        default="enriched_seen",
        choices=["enriched_seen", "messages_total"],
    )
    args = parser.parse_args()

    if args.max_dropped_invalid < -1:
        print("FAIL: --max-dropped-invalid must be >= -1")
        return 1
    if args.max_dropped_invalid_rate < -1.0:
        print("FAIL: --max-dropped-invalid-rate must be >= -1")
        return 1

    if not args.stats_file.exists():
        print(f"FAIL: stats file does not exist: {args.stats_file}")
        return 1

    try:
        payload = json.loads(args.stats_file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: unable to read stats JSON: {exc}")
        return 1

    stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else payload
    if not isinstance(stats, dict):
        print("FAIL: stats payload must be an object")
        return 1

    failures, drop_rate, dropped_invalid, denominator = evaluate_dropped_invalid_policy(
        stats,
        max_dropped_invalid=args.max_dropped_invalid,
        max_dropped_invalid_rate=args.max_dropped_invalid_rate,
        rate_denominator=args.dropped_invalid_rate_denominator,
    )

    exit_code = 0 if not failures else 1
    result = build_bridge_quality_artifact(
        stats=stats,
        max_dropped_invalid=args.max_dropped_invalid,
        max_dropped_invalid_rate=args.max_dropped_invalid_rate,
        rate_denominator=args.dropped_invalid_rate_denominator,
        policy_failures=failures,
        exit_code=exit_code,
    )
    result["source_stats_file"] = str(args.stats_file)

    print(json.dumps(result, indent=2))

    if failures:
        print(
            "FAIL: strict replay malformed-drop gate failed "
            f"(dropped_invalid={dropped_invalid}, denominator={denominator}, drop_rate={drop_rate:.6f})"
        )
        return 1

    print(
        "PASS: strict replay malformed-drop gate passed "
        f"(dropped_invalid={dropped_invalid}, denominator={denominator}, drop_rate={drop_rate:.6f})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
