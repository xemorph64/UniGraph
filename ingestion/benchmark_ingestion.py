from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from confluent_kafka import Consumer, Producer


def _wait_assignment(consumer: Consumer, timeout_s: int = 20) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        consumer.poll(0.5)
        if consumer.assignment():
            return
    raise RuntimeError("consumer assignment timeout")


def _parse_json(text: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None


def _extract_event_node(root: dict[str, Any]) -> dict[str, Any] | None:
    candidate: Any = root
    if "raw_event" in root:
        raw_event = root.get("raw_event")
        if isinstance(raw_event, str):
            parsed = _parse_json(raw_event)
            if parsed is None:
                return None
            candidate = parsed
        elif isinstance(raw_event, dict):
            candidate = raw_event
        else:
            return None

    if isinstance(candidate, dict) and "payload" in candidate and isinstance(candidate["payload"], dict):
        candidate = candidate["payload"]
    if isinstance(candidate, dict) and "after" in candidate and isinstance(candidate["after"], dict):
        candidate = candidate["after"]

    if isinstance(candidate, dict):
        return candidate
    return None


def _extract_txn_id_from_enriched(text: str) -> str | None:
    root = _parse_json(text)
    if root is None:
        return None
    event_node = _extract_event_node(root)
    if event_node is None:
        return None
    txn_id = event_node.get("txn_id")
    if isinstance(txn_id, str) and txn_id:
        return txn_id
    return None


def _extract_txn_id_from_rule(text: str) -> str | None:
    root = _parse_json(text)
    if root is None:
        return None
    txn_id = root.get("txn_id")
    if isinstance(txn_id, str) and txn_id:
        return txn_id
    return None


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def run_benchmark(bootstrap: str, count: int, timeout_s: int, profile: str) -> dict[str, Any]:
    run_id = f"BENCH-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    producer = Producer({"bootstrap.servers": bootstrap})

    enriched_consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": f"bench-enriched-{uuid.uuid4().hex[:12]}",
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )
    rule_consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": f"bench-rule-{uuid.uuid4().hex[:12]}",
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )

    enriched_consumer.subscribe(["enriched-transactions"])
    rule_consumer.subscribe(["rule-violations"])
    _wait_assignment(enriched_consumer)
    _wait_assignment(rule_consumer)

    send_times_ns: dict[str, int] = {}
    first_send_ns = 0
    publish_started_ns = time.perf_counter_ns()
    for i in range(count):
        txn_id = f"{run_id}-{i:06d}"
        send_ns = time.perf_counter_ns()
        if first_send_ns == 0:
            first_send_ns = send_ns
        send_times_ns[txn_id] = send_ns

        event = {
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
                "txn_id": txn_id,
                "from_account": f"UBI301000{(10000000 + (i % 5000)):08d}",
                "to_account": f"UBI301000{(20000000 + (i % 5000)):08d}",
                "amount": 750000.0,
                "channel": "RTGS",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "customer_id": f"CUST-BENCH-{i % 5000:04d}",
                "device_fingerprint": f"sha256:dev-{i % 2048}",
                "ip_address": f"sha256:ip-{i % 2048}",
                "location": {"lat": 19.076, "lon": 72.8777},
            },
        }

        producer.produce("raw-transactions", value=json.dumps(event).encode("utf-8"))
        if i % 1000 == 0:
            producer.poll(0)

    producer.flush()
    publish_finished_ns = time.perf_counter_ns()

    enriched_seen: set[str] = set()
    rule_seen: set[str] = set()
    latencies_ms: list[float] = []
    last_enriched_ns = 0

    enriched_deadline = time.time() + timeout_s
    while len(enriched_seen) < count and time.time() < enriched_deadline:
        msg = enriched_consumer.poll(0.5)
        if msg is None or msg.error():
            continue

        text = msg.value().decode("utf-8", errors="ignore")
        txn_id = _extract_txn_id_from_enriched(text)
        if txn_id is None or txn_id not in send_times_ns or txn_id in enriched_seen:
            continue

        now_ns = time.perf_counter_ns()
        enriched_seen.add(txn_id)
        latencies_ms.append((now_ns - send_times_ns[txn_id]) / 1_000_000.0)
        last_enriched_ns = now_ns

    rule_deadline = time.time() + timeout_s
    while len(rule_seen) < count and time.time() < rule_deadline:
        msg = rule_consumer.poll(0.5)
        if msg is None or msg.error():
            continue

        text = msg.value().decode("utf-8", errors="ignore")
        txn_id = _extract_txn_id_from_rule(text)
        if txn_id is None or txn_id not in send_times_ns:
            continue
        rule_seen.add(txn_id)

    enriched_consumer.close()
    rule_consumer.close()

    throughput_tps = 0.0
    if first_send_ns > 0 and last_enriched_ns > first_send_ns and enriched_seen:
        throughput_tps = len(enriched_seen) / ((last_enriched_ns - first_send_ns) / 1_000_000_000.0)

    result = {
        "profile": profile,
        "run_id": run_id,
        "count": count,
        "publish_duration_ms": round((publish_finished_ns - publish_started_ns) / 1_000_000.0, 2),
        "enriched_received": len(enriched_seen),
        "rule_received": len(rule_seen),
        "throughput_tps": round(throughput_tps, 2),
        "latency_ms": {
            "p50": round(_percentile(latencies_ms, 0.50), 2) if latencies_ms else None,
            "p95": round(_percentile(latencies_ms, 0.95), 2) if latencies_ms else None,
            "p99": round(_percentile(latencies_ms, 0.99), 2) if latencies_ms else None,
            "mean": round(statistics.fmean(latencies_ms), 2) if latencies_ms else None,
            "max": round(max(latencies_ms), 2) if latencies_ms else None,
        },
    }

    result["status"] = "PASS" if (len(enriched_seen) == count and len(rule_seen) == count) else "PARTIAL"
    result["missing_enriched"] = count - len(enriched_seen)
    result["missing_rule"] = count - len(rule_seen)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Burst benchmark for UniGRAPH ingestion pipeline")
    parser.add_argument("--bootstrap", default="localhost:19092")
    parser.add_argument("--count", type=int, default=5000)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--profile", default="optimized")
    args = parser.parse_args()

    result = run_benchmark(args.bootstrap, args.count, args.timeout, args.profile)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
