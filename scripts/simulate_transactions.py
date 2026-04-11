#!/usr/bin/env python3
"""
Real-time Transaction Simulator for UniGRAPH Demo
Generates transactions and pushes them to the backend via HTTP API.

Usage:
    python scripts/simulate_transactions.py --mode live --rate 5
    python scripts/simulate_transactions.py --mode scenario --scenario rapid_layering
"""

import asyncio
import argparse
import json
import random
import time
from datetime import datetime, timezone
from typing import Optional
import httpx


class TransactionSimulator:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=10.0)
        self.stats = {"sent": 0, "flagged": 0, "errors": 0}

    async def close(self):
        await self.client.aclose()

    def _generate_account(self, prefix: str, idx: int) -> str:
        return f"UBI301000{prefix}{idx:06d}"

    def _generate_normal_transaction(self, idx: int) -> dict:
        channels = ["UPI", "IMPS", "NEFT", "RTGS"]
        amount = round(random.uniform(100, 50000), 2)
        return {
            "txn_id": f"TXN-NORM-{idx:06d}",
            "from_account": self._generate_account("N", random.randint(1, 100)),
            "to_account": self._generate_account("R", random.randint(1, 200)),
            "amount": amount,
            "channel": random.choice(channels),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "customer_id": f"CUST-{random.randint(1000, 9999)}",
            "device_fingerprint": f"sha256:dev-{random.randint(1000, 9999):08x}",
            "ip_address": f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
            "location": {
                "lat": 19.0 + random.uniform(-1, 1),
                "lon": 72.8 + random.uniform(-1, 1),
            },
        }

    def _generate_rapid_layering(self) -> list[dict]:
        events = []
        accounts = [self._generate_account("L", i) for i in range(1, 8)]
        base_amount = 950000.0
        base_time = datetime.now(timezone.utc)

        for i in range(len(accounts) - 1):
            events.append(
                {
                    "txn_id": f"TXN-LAYER-{i + 1:03d}",
                    "from_account": accounts[i],
                    "to_account": accounts[i + 1],
                    "amount": max(50000.0, base_amount - i * 50000),
                    "channel": random.choice(["IMPS", "NEFT", "RTGS"]),
                    "timestamp": (base_time.replace(second=i * 10, microsecond=0))
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "customer_id": f"CUST-LAYER-{i:03d}",
                    "device_fingerprint": f"sha256:dev-layer-{i:03d}",
                    "ip_address": f"10.0.1.{i + 1}",
                    "location": {"lat": 19.0760, "lon": 72.8777},
                    "velocity_1h": 6,
                    "velocity_24h": 6,
                    "is_dormant": False,
                    "device_account_count": 1,
                }
            )
        return events

    def _generate_structuring(self) -> list[dict]:
        events = []
        src = self._generate_account("S", 1)
        base_time = datetime.now(timezone.utc)

        for i in range(12):
            amount = round(random.uniform(990000, 999500), 2)
            events.append(
                {
                    "txn_id": f"TXN-STRUCT-{i + 1:03d}",
                    "from_account": src,
                    "to_account": self._generate_account("S", 100 + i),
                    "amount": amount,
                    "channel": random.choice(["NEFT", "RTGS"]),
                    "timestamp": (
                        base_time.replace(minute=i * 5, second=0, microsecond=0)
                    )
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "customer_id": "CUST-STRUCT-001",
                    "device_fingerprint": f"sha256:dev-struct-001",
                    "ip_address": "10.0.2.1",
                    "location": {"lat": 28.6139, "lon": 77.2090},
                    "velocity_1h": 12,
                    "velocity_24h": 12,
                    "is_dormant": False,
                    "device_account_count": 1,
                }
            )
        return events

    def _generate_dormant_awakening(self) -> dict:
        return {
            "txn_id": "TXN-DORMANT-001",
            "from_account": self._generate_account("D", 1),
            "to_account": self._generate_account("D", 2),
            "amount": 1500000.0,
            "channel": "NEFT",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "customer_id": "CUST-DORMANT-001",
            "device_fingerprint": "sha256:dev-new-001",
            "ip_address": "10.0.3.1",
            "location": {"lat": 12.9716, "lon": 77.5946},
            "velocity_1h": 1,
            "velocity_24h": 1,
            "is_dormant": True,
            "device_account_count": 1,
        }

    def _generate_mule_network(self) -> list[dict]:
        events = []
        accounts = [self._generate_account("M", i) for i in range(1, 6)]
        mule_device = "sha256:dev-mule-shared-001"
        base_time = datetime.now(timezone.utc)

        for i in range(len(accounts) - 1):
            events.append(
                {
                    "txn_id": f"TXN-MULE-{i + 1:03d}",
                    "from_account": accounts[i],
                    "to_account": accounts[i + 1],
                    "amount": 50000 * (i + 1),
                    "channel": "UPI",
                    "timestamp": (
                        base_time.replace(hour=i, minute=0, second=0, microsecond=0)
                    )
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "customer_id": f"CUST-MULE-{i:03d}",
                    "device_fingerprint": mule_device,
                    "ip_address": f"10.0.4.{i + 1}",
                    "location": {"lat": 12.9716, "lon": 77.5946},
                    "velocity_1h": 4,
                    "velocity_24h": 4,
                    "is_dormant": False,
                    "device_account_count": 5,
                }
            )
        return events

    async def _post_transaction(self, txn: dict) -> Optional[dict]:
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/transactions/ingest",
                json=txn,
            )
            self.stats["sent"] += 1
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get("risk_level") in ["HIGH", "CRITICAL"]:
                    self.stats["flagged"] += 1
                return result
            else:
                print(f"Error: {response.status_code} - {response.text[:100]}")
                self.stats["errors"] += 1
                return None
        except Exception as e:
            print(f"Error posting transaction: {e}")
            self.stats["errors"] += 1
            return None

    async def run_live_stream(self, rate: int = 5, duration: Optional[int] = None):
        print(f"Starting live transaction stream at {rate} txns/sec...")
        print(f"Target: {self.base_url}")

        start_time = time.time()
        txn_idx = 0

        try:
            while True:
                if duration and (time.time() - start_time) >= duration:
                    break

                txn = self._generate_normal_transaction(txn_idx)
                result = await self._post_transaction(txn)

                if result:
                    risk = result.get("risk_level", "UNKNOWN")
                    color = "\033[91m" if risk in ["HIGH", "CRITICAL"] else "\033[92m"
                    reset = "\033[0m"
                    print(
                        f"  {txn['txn_id']}: ₹{txn['amount']:,.2f} | {result.get('probability', 0):.2%} [{color}{risk}{reset}]"
                    )

                txn_idx += 1
                await asyncio.sleep(1.0 / rate)

        except KeyboardInterrupt:
            print("\n\nStream stopped by user")

        print(f"\n📊 Final Stats:")
        print(f"   Sent: {self.stats['sent']}")
        print(f"   Flagged: {self.stats['flagged']}")
        print(f"   Errors: {self.stats['errors']}")

    async def run_scenario(self, scenario: str):
        print(f"Running fraud scenario: {scenario}")

        if scenario == "rapid_layering":
            txns = self._generate_rapid_layering()
        elif scenario == "structuring":
            txns = self._generate_structuring()
        elif scenario == "dormant_awakening":
            txns = [self._generate_dormant_awakening()]
        elif scenario == "mule_network":
            txns = self._generate_mule_network()
        else:
            print(f"Unknown scenario: {scenario}")
            return

        print(f"Generated {len(txns)} transactions")

        for i, txn in enumerate(txns):
            result = await self._post_transaction(txn)
            if result:
                risk = result.get("risk_level", "UNKNOWN")
                color = "\033[91m" if risk in ["HIGH", "CRITICAL"] else "\033[92m"
                reset = "\033[0m"
                print(
                    f"[{i + 1}/{len(txns)}] {txn['txn_id']}: ₹{txn['amount']:,.2f} | Score: {result.get('probability', 0):.2%} [{color}{risk}{reset}]"
                )

            await asyncio.sleep(0.5)

        print(f"\n📊 Scenario '{scenario}' complete!")
        print(f"   Transactions: {len(txns)}")
        print(f"   Flagged: {self.stats['flagged']}")


async def main():
    parser = argparse.ArgumentParser(description="UniGRAPH Transaction Simulator")
    parser.add_argument("--mode", choices=["live", "scenario"], default="live")
    parser.add_argument(
        "--rate", type=int, default=5, help="Transactions per second (live mode)"
    )
    parser.add_argument("--duration", type=int, help="Duration in seconds (live mode)")
    parser.add_argument(
        "--scenario",
        choices=["rapid_layering", "structuring", "dormant_awakening", "mule_network"],
        default="rapid_layering",
        help="Fraud scenario to run",
    )
    parser.add_argument("--url", default="http://localhost:8000", help="Backend URL")

    args = parser.parse_args()

    sim = TransactionSimulator(args.url)

    try:
        if args.mode == "live":
            await sim.run_live_stream(rate=args.rate, duration=args.duration)
        else:
            await sim.run_scenario(args.scenario)
    finally:
        await sim.close()


if __name__ == "__main__":
    asyncio.run(main())
