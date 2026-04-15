#!/usr/bin/env python3
"""Deprecated compatibility wrapper.

This legacy ingestor is intentionally disabled for active validation.

Use canonical dataset paths instead:
  1) scripts/ingest_transactions_input_sql.py --dataset 100
  2) scripts/ingest_transactions_input_sql.py --dataset 200

For scenario validation, use:
  scripts/ingest_fraud_scenarios.py
"""

from __future__ import annotations


def main() -> int:
    print(
        "ingest_sql_transactions.py is deprecated and disabled. "
        "Use scripts/ingest_transactions_input_sql.py --dataset {100|200} "
        "or scripts/ingest_fraud_scenarios.py."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
