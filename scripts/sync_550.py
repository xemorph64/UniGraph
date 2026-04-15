#!/usr/bin/env python3
"""Deprecated compatibility wrapper.

This script is intentionally disabled. The dataset_550 flow is no longer valid for
active validation.

Use canonical datasets and ingestion paths instead:
  1) scripts/ingest_transactions_input_sql.py --dataset 100
  2) scripts/ingest_transactions_input_sql.py --dataset 200

Or use API-assisted dataset switching:
  POST /api/v1/datasets/stream with {"dataset": "100"} or {"dataset": "200"}
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "sync_550.py is deprecated and disabled. "
        "Use dataset_100_interconnected_txns.sql or dataset_200_interconnected_txns.sql via "
        "scripts/ingest_transactions_input_sql.py --dataset {100|200}."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
