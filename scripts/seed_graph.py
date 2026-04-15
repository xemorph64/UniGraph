#!/usr/bin/env python3
"""Deprecated compatibility wrapper.

This script previously inserted synthetic graph nodes directly into Neo4j.
It is intentionally disabled because active validation must use canonical
ingest + scoring paths.

Use one of these instead:
  1) scripts/ingest_transactions_input_sql.py --dataset 100
  2) scripts/ingest_transactions_input_sql.py --dataset 200
  3) scripts/demo_seeder.py (demo-only setup)
"""

from __future__ import annotations


def main() -> int:
    print(
        "seed_graph.py is deprecated and disabled. "
        "Use canonical ingest scripts for dataset 100/200, or demo_seeder.py for demo mode."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
