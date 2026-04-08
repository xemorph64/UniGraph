from __future__ import annotations

import argparse
import json
import signal
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from confluent_kafka import Consumer, KafkaError


TOPICS = ["raw-transactions", "enriched-transactions", "rule-violations"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "Z"


def _safe_json(value: bytes | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None


def _extract_raw_txn_id(payload: dict[str, Any]) -> str:
    return str(payload.get("txn_id") or payload.get("after", {}).get("txn_id") or "unknown")


def _extract_enriched_txn_id(payload: dict[str, Any]) -> str:
    raw_event = payload.get("raw_event", {})
    return str(raw_event.get("txn_id") or raw_event.get("after", {}).get("txn_id") or "unknown")


def _format_raw(payload: dict[str, Any], partition: int, offset: int) -> str:
    txn_id = _extract_raw_txn_id(payload)
    amount = payload.get("amount") or payload.get("after", {}).get("amount")
    channel = payload.get("channel") or payload.get("after", {}).get("channel")
    return (
        f"[{_utc_now()}] [RAW] "
        f"txn_id={txn_id} amount={amount} channel={channel} "
        f"(p={partition}, o={offset})"
    )


def _format_enriched(payload: dict[str, Any], partition: int, offset: int) -> str:
    txn_id = _extract_enriched_txn_id(payload)
    enrichment = payload.get("enrichment", {})
    event_uid = enrichment.get("event_uid", "n/a")
    ingest_ts = enrichment.get("ingest_ts", "n/a")
    return (
        f"[{_utc_now()}] [ENRICHED] "
        f"txn_id={txn_id} event_uid={event_uid} ingest_ts={ingest_ts} "
        f"(p={partition}, o={offset})"
    )


def _format_violation(payload: dict[str, Any], partition: int, offset: int) -> str:
    account = payload.get("account_id", "unknown")
    rule = payload.get("rule", "unknown")
    total_amount = payload.get("total_amount", "n/a")
    flagged = payload.get("is_flagged", "n/a")
    return (
        f"[{_utc_now()}] [VIOLATION] "
        f"account={account} rule={rule} total_amount={total_amount} flagged={flagged} "
        f"(p={partition}, o={offset})"
    )


def _print_message(topic: str, payload: Any, partition: int, offset: int, raw_bytes: bytes | None) -> None:
    if isinstance(payload, dict):
        if topic == "raw-transactions":
            print(_format_raw(payload, partition, offset), flush=True)
            return
        if topic == "enriched-transactions":
            print(_format_enriched(payload, partition, offset), flush=True)
            return
        if topic == "rule-violations":
            print(_format_violation(payload, partition, offset), flush=True)
            return

    text = (raw_bytes or b"").decode("utf-8", errors="replace")
    snippet = text if len(text) <= 280 else text[:277] + "..."
    print(
        f"[{_utc_now()}] [UNKNOWN:{topic}] payload={snippet} (p={partition}, o={offset})",
        flush=True,
    )


def _build_consumer(bootstrap_servers: str, offset_reset: str) -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": f"live-viewer-{uuid.uuid4().hex[:10]}",
            "client.id": "unigraph-live-viewer",
            "auto.offset.reset": offset_reset,
            "enable.auto.commit": True,
            "session.timeout.ms": 10000,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Live viewer for UniGRAPH ingestion pipeline topics")
    parser.add_argument("--bootstrap-servers", default="localhost:19092")
    parser.add_argument("--offset-reset", choices=["latest", "earliest"], default="latest")
    args = parser.parse_args()

    consumer = _build_consumer(args.bootstrap_servers, args.offset_reset)
    running = True

    def _stop_handler(signum, frame):  # type: ignore[no-untyped-def]
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    print(
        f"[{_utc_now()}] Live viewer started on {args.bootstrap_servers} | topics={', '.join(TOPICS)}",
        flush=True,
    )
    print(f"[{_utc_now()}] Press Ctrl+C to stop", flush=True)

    consumer.subscribe(TOPICS)

    try:
        while running:
            msg = consumer.poll(1.0)
            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"[{_utc_now()}] [ERROR] {msg.error()}", file=sys.stderr, flush=True)
                continue

            topic = msg.topic()
            raw_value = msg.value()
            payload = _safe_json(raw_value)
            _print_message(topic, payload, msg.partition(), msg.offset(), raw_value)
    finally:
        consumer.close()
        print(f"[{_utc_now()}] Live viewer stopped", flush=True)


if __name__ == "__main__":
    main()