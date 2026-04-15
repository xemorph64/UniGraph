#!/usr/bin/env python3
"""Verify Phase 1 deprecation and dataset policy integrity.

Checks:
1) Canonical dataset map only exposes 100 and 200.
2) Legacy scripts are disabled wrappers.
3) Pipeline map documents 100/200 as active and 550 as deprecated.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def main() -> int:
    status = 0

    datasets_router = ROOT / "backend" / "app" / "routers" / "datasets.py"
    datasets_content = _read(datasets_router)
    if '"100": "dataset_100_interconnected_txns.sql"' not in datasets_content:
        status |= _fail("dataset alias 100 missing from backend dataset router")
    else:
        _ok("dataset alias 100 present")

    if '"200": "dataset_200_interconnected_txns.sql"' not in datasets_content:
        status |= _fail("dataset alias 200 missing from backend dataset router")
    else:
        _ok("dataset alias 200 present")

    if re.search(r"dataset_550(_normal_txns)?\\.sql", datasets_content):
        status |= _fail("dataset_550 reference found in backend dataset router")
    else:
        _ok("no dataset_550 reference in backend dataset router")

    ingestor = ROOT / "scripts" / "ingest_transactions_input_sql.py"
    ingestor_content = _read(ingestor)
    if '"100": ROOT_DIR / "dataset_100_interconnected_txns.sql"' not in ingestor_content:
        status |= _fail("dataset 100 missing from canonical ingestor map")
    else:
        _ok("canonical ingestor includes dataset 100")

    if '"200": ROOT_DIR / "dataset_200_interconnected_txns.sql"' not in ingestor_content:
        status |= _fail("dataset 200 missing from canonical ingestor map")
    else:
        _ok("canonical ingestor includes dataset 200")

    for rel in ("scripts/ingest_sql_transactions.py", "scripts/seed_graph.py", "scripts/sync_550.py"):
        content = _read(ROOT / rel)
        if "deprecated and disabled" not in content:
            status |= _fail(f"{rel} is not marked as deprecated and disabled")
        else:
            _ok(f"{rel} is disabled wrapper")

    pipeline_map = ROOT / "END_TO_END_PIPELINE_MAP.md"
    pipeline_content = _read(pipeline_map)
    if "dataset_100_interconnected_txns.sql" not in pipeline_content or "dataset_200_interconnected_txns.sql" not in pipeline_content:
        status |= _fail("pipeline map does not list dataset_100 and dataset_200 as active")
    else:
        _ok("pipeline map lists dataset_100 and dataset_200")

    if "Deprecated for active validation (do not use):" not in pipeline_content:
        status |= _fail("pipeline map missing explicit deprecation section")
    else:
        _ok("pipeline map has explicit deprecation section")

    if status == 0:
        print("PASS: Phase 1 deprecation integrity checks completed")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
