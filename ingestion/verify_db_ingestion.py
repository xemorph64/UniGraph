from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone

import psycopg2
from confluent_kafka import Consumer
from psycopg2.extras import Json


TEST_TXN_ID = "DB-TEST-E2E-001"
TOPICS = ["raw-transactions", "enriched-transactions", "rule-violations"]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _wait_assignment(consumer: Consumer, timeout_s: int = 10) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        consumer.poll(0.5)
        if consumer.assignment():
            return
    raise RuntimeError("Kafka consumer assignment timeout")


def _connect_postgres(host: str, port: int, dbname: str, user: str, password: str):
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )


def _get_transactions_columns(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'transactions'
            """
        )
        return {row[0] for row in cur.fetchall()}


def _insert_test_transaction(conn, columns: set[str]) -> tuple[str, str]:
    from_account = "UBI301000DBTEST01"
    to_account = "UBI301000DBTEST99"
    customer_id = "CUST-DB-E2E-0001"
    device = "sha256:dev-db-e2e"
    ip_addr = "sha256:ip-db-e2e"

    with conn.cursor() as cur:
        cur.execute("DELETE FROM public.transactions WHERE txn_id = %s", (TEST_TXN_ID,))

        modern_columns = {
            "from_account",
            "to_account",
            "timestamp",
            "customer_id",
            "device_fingerprint",
            "location",
        }
        legacy_columns = {
            "sender_account",
            "receiver_account",
            "txn_timestamp",
            "device_id",
            "geo_lat",
            "geo_lon",
            "narration",
        }

        if modern_columns.issubset(columns):
            cur.execute(
                """
                INSERT INTO public.transactions (
                    txn_id,
                    from_account,
                    to_account,
                    amount,
                    channel,
                    "timestamp",
                    customer_id,
                    device_fingerprint,
                    ip_address,
                    location
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    TEST_TXN_ID,
                    from_account,
                    to_account,
                    999500.00,
                    "RTGS",
                    _iso_now(),
                    customer_id,
                    device,
                    ip_addr,
                    Json({"lat": 22.5726, "lon": 88.3639}),
                ),
            )
        elif legacy_columns.issubset(columns):
            cur.execute(
                """
                INSERT INTO public.transactions (
                    txn_id,
                    sender_account,
                    receiver_account,
                    amount,
                    channel,
                    txn_timestamp,
                    device_id,
                    ip_address,
                    geo_lat,
                    geo_lon,
                    narration,
                    status,
                    is_flagged,
                    fraud_flag_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    TEST_TXN_ID,
                    from_account,
                    to_account,
                    999500.00,
                    "RTGS",
                    datetime.now(timezone.utc),
                    device,
                    ip_addr,
                    22.5726,
                    88.3639,
                    "db-ingestion-verifier",
                    "SUCCESS",
                    False,
                    None,
                ),
            )
        else:
            raise RuntimeError(
                "Unsupported public.transactions schema for verifier. "
                f"Columns present: {sorted(columns)}"
            )

    conn.commit()
    return from_account, customer_id


def _emit_rapid_updates(conn, columns: set[str], count: int = 2) -> None:
    # Generate quick successive CDC updates so anomaly windows can observe velocity-like bursts.
    timestamp_column = '"timestamp"' if "timestamp" in columns else "txn_timestamp"
    for _ in range(count):
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE public.transactions
                SET amount = amount + 1000.00,
                    {timestamp_column} = %s
                WHERE txn_id = %s
                """,
                (
                    _iso_now() if timestamp_column == '"timestamp"' else datetime.now(timezone.utc),
                    TEST_TXN_ID,
                ),
            )
        conn.commit()
        time.sleep(0.2)


def _build_consumer(bootstrap: str, topic: str) -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": f"verify-db-ingestion-{topic}-{uuid.uuid4().hex[:10]}",
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )


def _assert_topics(bootstrap: str, timeout_s: int, on_ready=None) -> dict:
    consumers: dict[str, Consumer] = {}
    found: dict[str, str] = {}

    try:
        for topic in TOPICS:
            consumer = _build_consumer(bootstrap, topic)
            consumer.subscribe([topic])
            _wait_assignment(consumer)
            consumers[topic] = consumer

        if on_ready is not None:
            on_ready()

        deadline = time.time() + timeout_s
        while time.time() < deadline and len(found) < len(TOPICS):
            for topic, consumer in consumers.items():
                if topic in found:
                    continue
                msg = consumer.poll(0.5)
                if msg is None or msg.error():
                    continue

                value_bytes = msg.value()
                if value_bytes is None:
                    continue

                payload_text = value_bytes.decode("utf-8", errors="ignore")
                if TEST_TXN_ID in payload_text:
                    found[topic] = payload_text

        missing = [topic for topic in TOPICS if topic not in found]
        return {
            "found": sorted(found.keys()),
            "missing": missing,
            "samples": {k: v[:500] for k, v in found.items()},
        }
    finally:
        for consumer in consumers.values():
            consumer.close()


def run(
    bootstrap: str,
    timeout_s: int,
    db_host: str,
    db_port: int,
    db_name: str,
    db_user: str,
    db_password: str,
) -> dict:
    conn = _connect_postgres(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
    )

    try:
        columns = _get_transactions_columns(conn)
        from_account, customer_id = _insert_test_transaction(conn, columns)

        result = _assert_topics(
            bootstrap=bootstrap,
            timeout_s=timeout_s,
            on_ready=lambda: _emit_rapid_updates(conn, columns=columns, count=2),
        )
        if result["missing"]:
            return {
                "status": "FAIL",
                "txn_id": TEST_TXN_ID,
                "error": "Transaction not found in all required topics within timeout",
                "missing_topics": result["missing"],
                "found_topics": result["found"],
            }

        return {
            "status": "PASS",
            "txn_id": TEST_TXN_ID,
            "bootstrap": bootstrap,
            "db": db_name,
            "from_account": from_account,
            "customer_id": customer_id,
            "topics_verified": TOPICS,
        }
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify DB->Debezium->Flink CDC ingestion")
    parser.add_argument("--bootstrap", default="localhost:19092")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--db-host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("PGPORT", "5433")))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", "finacle_cbs"))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", "postgres"))
    args = parser.parse_args()

    outcome = run(
        bootstrap=args.bootstrap,
        timeout_s=args.timeout,
        db_host=args.db_host,
        db_port=args.db_port,
        db_name=args.db_name,
        db_user=args.db_user,
        db_password=args.db_password,
    )
    print(json.dumps(outcome))
    if outcome.get("status") != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
