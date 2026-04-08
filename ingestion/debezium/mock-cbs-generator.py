from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
import os
from random import Random
from typing import Any


_RNG = Random(42)


def _iso_now(offset_minutes: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)).isoformat().replace("+00:00", "Z")


def _account(i: int) -> str:
    return f"UBI301000{i:08d}"


def _customer(i: int) -> str:
    return f"CUST-UBI-{i:07d}"


def _device(i: int) -> str:
    return f"sha256:dev-{i:08x}"


def _ip(i: int) -> str:
    return f"sha256:ip-{i:08x}"


def generate_transaction(
    txn_id: str,
    from_account: str,
    to_account: str,
    amount: float,
    channel: str,
    timestamp: str,
    customer_id: str,
    device_fingerprint: str,
    ip_address: str,
    location: dict,
) -> dict:
    """Generate a single mock CBS transaction event matching Debezium output format."""
    return {
        "op": "c",
        "source": {
            "version": "2.5.0.Final",
            "connector": "postgresql",
            "name": "cbs",
            "db": "finacle_cbs",
            "table": "transactions",
            "ts_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
        },
        "after": {
            "txn_id": txn_id,
            "from_account": from_account,
            "to_account": to_account,
            "amount": amount,
            "channel": channel,
            "timestamp": timestamp,
            "customer_id": customer_id,
            "device_fingerprint": device_fingerprint,
            "ip_address": ip_address,
            "location": location,
        },
    }


def generate_fraud_scenario_rapid_layering(num_hops: int = 6) -> list[dict]:
    """Generate a chain of 6 rapid transactions (<30 min, each >50K)."""
    events: list[dict] = []
    chain_accounts = [_account(90000000 + i) for i in range(num_hops + 1)]
    base_amount = 95000.0

    for i in range(num_hops):
        events.append(
            generate_transaction(
                txn_id=f"TXN-LAYER-{i + 1:03d}",
                from_account=chain_accounts[i],
                to_account=chain_accounts[i + 1],
                amount=max(50000.0, base_amount - i * 3000),
                channel=_RNG.choice(["IMPS", "NEFT", "RTGS"]),
                timestamp=_iso_now(offset_minutes=i * 4),
                customer_id=_customer(7000000 + i),
                device_fingerprint=_device(100 + i),
                ip_address=_ip(100 + i),
                location={"lat": 19.0760 + i * 0.001, "lon": 72.8777 + i * 0.001},
            )
        )
    return events


def generate_fraud_scenario_structuring(num_txns: int = 12) -> list[dict]:
    """Generate 12 transactions just below 10L CTR threshold."""
    events: list[dict] = []
    src = _account(91000000)
    base_time = datetime.now(timezone.utc)
    for i in range(num_txns):
        amount = float(_RNG.uniform(990000, 999500))
        ts = (base_time + timedelta(minutes=i * 20)).isoformat().replace("+00:00", "Z")
        events.append(
            generate_transaction(
                txn_id=f"TXN-STRUCT-{i + 1:03d}",
                from_account=src,
                to_account=_account(91010000 + i),
                amount=round(amount, 2),
                channel=_RNG.choice(["NEFT", "RTGS", "IMPS"]),
                timestamp=ts,
                customer_id=_customer(7100000),
                device_fingerprint=_device(200),
                ip_address=_ip(200),
                location={"lat": 28.6139, "lon": 77.2090},
            )
        )
    return events


def generate_fraud_scenario_dormant_awakening() -> list[dict]:
    """Generate a sudden large debit from a dormant account."""
    return [
        generate_transaction(
            txn_id="TXN-DORM-001",
            from_account=_account(92000000),
            to_account=_account(92000001),
            amount=875000.00,
            channel="RTGS",
            timestamp=_iso_now(),
            customer_id=_customer(7200000),
            device_fingerprint=_device(300),
            ip_address=_ip(300),
            location={"lat": 12.9716, "lon": 77.5946},
        )
    ]


def generate_normal_transactions(count: int = 100) -> list[dict]:
    """Generate realistic normal transaction patterns."""
    events: list[dict] = []
    channels = ["UPI", "IMPS", "NEFT", "CASH"]
    for i in range(count):
        amount = round(float(_RNG.uniform(200, 45000)), 2)
        events.append(
            generate_transaction(
                txn_id=f"TXN-NORM-{i + 1:05d}",
                from_account=_account(10000000 + (i % 250)),
                to_account=_account(20000000 + (i % 400)),
                amount=amount,
                channel=_RNG.choice(channels),
                timestamp=_iso_now(offset_minutes=i),
                customer_id=_customer(1000000 + (i % 250)),
                device_fingerprint=_device(1000 + (i % 100)),
                ip_address=_ip(1000 + (i % 100)),
                location={"lat": 19.0 + (i % 10) * 0.01, "lon": 72.8 + (i % 10) * 0.01},
            )
        )
    return events


def publish_to_kafka(
    events: list[dict],
    topic: str = "raw-transactions",
    bootstrap_servers: str | None = None,
    raise_on_error: bool = False,
) -> int:
    """Publish events to Kafka topic and return published event count."""
    bootstrap = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    try:
        from confluent_kafka import Producer

        producer = Producer({"bootstrap.servers": bootstrap})
        for event in events:
            producer.produce(topic=topic, value=json.dumps(event).encode("utf-8"))
        producer.flush()
        return len(events)
    except Exception:
        if raise_on_error:
            raise
        return 0


def _build_events(scenario: str, count: int) -> list[dict]:
    if scenario == "normal":
        return generate_normal_transactions(count)
    if scenario == "rapid_layering":
        return generate_fraud_scenario_rapid_layering(max(2, count))
    if scenario == "structuring":
        return generate_fraud_scenario_structuring(max(2, count))
    if scenario == "dormant":
        return generate_fraud_scenario_dormant_awakening()
    if scenario == "mixed":
        normal_count = max(1, count)
        events = generate_normal_transactions(normal_count)
        events.extend(generate_fraud_scenario_rapid_layering())
        events.extend(generate_fraud_scenario_structuring())
        events.extend(generate_fraud_scenario_dormant_awakening())
        return events
    raise ValueError(f"Unknown scenario: {scenario}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate mock CBS events for UniGRAPH ingestion")
    parser.add_argument(
        "--scenario",
        default="mixed",
        choices=["normal", "rapid_layering", "structuring", "dormant", "mixed"],
        help="Type of event stream to generate",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Event count for scenarios that support variable size",
    )
    parser.add_argument(
        "--topic",
        default="raw-transactions",
        help="Kafka topic name to publish to",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output path to save events as JSON lines",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish generated events to Kafka",
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        help="Kafka bootstrap servers",
    )
    args = parser.parse_args()

    events = _build_events(args.scenario, args.count)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            for event in events:
                fh.write(json.dumps(event) + "\n")

    published = 0
    if args.publish:
        published = publish_to_kafka(events, topic=args.topic, bootstrap_servers=args.bootstrap_servers)

    print(
        json.dumps(
            {
                "events_generated": len(events),
                "scenario": args.scenario,
                "topic": args.topic,
                "published": published,
                "bootstrap_servers": args.bootstrap_servers,
            }
        )
    )


if __name__ == "__main__":
    main()
