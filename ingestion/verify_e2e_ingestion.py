from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone

from confluent_kafka import Consumer, Producer


def _wait_assignment(consumer: Consumer, timeout_s: int = 10) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        consumer.poll(0.5)
        if consumer.assignment():
            return
    raise RuntimeError("consumer assignment timeout")


def _parse_enriched_latency_ms(payload: dict) -> float:
    source_ts = payload["raw_event"]["after"]["timestamp"]
    ingest_ts = payload["enrichment"]["ingest_ts"]
    source_dt = datetime.fromisoformat(source_ts.replace("Z", "+00:00"))
    ingest_dt = datetime.fromisoformat(ingest_ts.replace("Z", "+00:00"))
    return round((ingest_dt - source_dt).total_seconds() * 1000, 2)


def run(bootstrap: str, timeout_enriched: int, timeout_rule: int) -> dict:
    eid = f"TXN-E2E-{int(time.time())}"
    account = "UBI30100099999999"

    producer = Producer({"bootstrap.servers": bootstrap})

    enriched_consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": f"e2e-enriched-{uuid.uuid4().hex[:12]}",
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )
    rule_consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": f"e2e-rule-{uuid.uuid4().hex[:12]}",
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )

    enriched_consumer.subscribe(["enriched-transactions"])
    rule_consumer.subscribe(["rule-violations"])
    _wait_assignment(enriched_consumer)
    _wait_assignment(rule_consumer)

    evt = {
        "op": "c",
        "source": {
            "version": "2.5.0.Final",
            "connector": "postgresql",
            "name": "cbs",
            "db": "finacle_cbs",
            "table": "transactions",
            "ts_ms": int(time.time() * 1000),
        },
        "after": {
            "txn_id": eid,
            "from_account": account,
            "to_account": "UBI30100088888888",
            "amount": 750000.0,
            "channel": "RTGS",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "customer_id": "CUST-E2E-0001",
            "device_fingerprint": "sha256:dev-e2e",
            "ip_address": "sha256:ip-e2e",
            "location": {"lat": 19.076, "lon": 72.8777},
        },
    }

    producer.produce("raw-transactions", value=json.dumps(evt).encode("utf-8"))
    producer.flush()

    enriched_payload = None
    deadline = time.time() + timeout_enriched
    while time.time() < deadline:
        msg = enriched_consumer.poll(1.0)
        if msg is None or msg.error():
            continue
        text = msg.value().decode("utf-8", errors="ignore")
        if eid not in text:
            continue
        enriched_payload = json.loads(text)
        break

    if enriched_payload is None:
        return {
            "status": "FAIL",
            "txn_id": eid,
            "error": "txn_id not found in enriched-transactions",
        }

    rule_payload = None
    deadline = time.time() + timeout_rule
    while time.time() < deadline:
        msg = rule_consumer.poll(1.0)
        if msg is None or msg.error():
            continue
        text = msg.value().decode("utf-8", errors="ignore")
        if account not in text:
            continue
        rule_payload = json.loads(text)
        break

    if rule_payload is None:
        return {
            "status": "FAIL",
            "txn_id": eid,
            "error": "account not found in rule-violations",
        }

    latency_ms = _parse_enriched_latency_ms(enriched_payload)
    return {
        "status": "PASS",
        "txn_id": eid,
        "account_id": account,
        "source_to_enrichment_latency_ms": latency_ms,
        "rule_window": rule_payload.get("window"),
        "rule_total_amount": rule_payload.get("total_amount"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify UniGRAPH ingestion E2E flow")
    parser.add_argument("--bootstrap", default="localhost:19092")
    parser.add_argument("--timeout-enriched", type=int, default=90)
    parser.add_argument("--timeout-rule", type=int, default=150)
    args = parser.parse_args()

    result = run(args.bootstrap, args.timeout_enriched, args.timeout_rule)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
