from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Graph writer entrypoint. Delegates to ingestion/neo4j_writer.py."
    )
    parser.add_argument("--bootstrap-servers", default="localhost:19092")
    parser.add_argument("--topic", default="enriched-transactions")
    parser.add_argument("--group-id", default="unigraph-neo4j-writer")
    parser.add_argument("--offset-reset", default="latest")
    parser.add_argument("--batch-size", default="100")
    parser.add_argument("--flush-interval-seconds", default="2.0")
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="unigraph_dev")
    parser.add_argument("--neo4j-database", default="neo4j")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    target = Path(__file__).resolve().parents[2] / "ingestion" / "neo4j_writer.py"
    cmd = [
        sys.executable,
        str(target),
        "--bootstrap-servers",
        args.bootstrap_servers,
        "--topic",
        args.topic,
        "--group-id",
        args.group_id,
        "--offset-reset",
        args.offset_reset,
        "--batch-size",
        args.batch_size,
        "--flush-interval-seconds",
        args.flush_interval_seconds,
        "--neo4j-uri",
        args.neo4j_uri,
        "--neo4j-user",
        args.neo4j_user,
        "--neo4j-password",
        args.neo4j_password,
        "--neo4j-database",
        args.neo4j_database,
        "--log-level",
        args.log_level,
    ]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
