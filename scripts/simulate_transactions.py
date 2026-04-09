from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone


def generate_event(i: int) -> dict:
    return {
        "txn_id": f"SIM-TXN-{i:08d}",
        "sender_account_no": f"SIM-ACC-{i % 1000:04d}",
        "receiver_account_no": f"SIM-ACC-{(i * 7) % 1000:04d}",
        "amount": round(random.uniform(100.0, 100000.0), 2),
        "channel": random.choice(["UPI", "IMPS", "NEFT", "RTGS"]),
        "txn_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic transaction events")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--output", default="transactions.sim.jsonl")
    args = parser.parse_args()

    with open(args.output, "w", encoding="utf-8") as f:
        for i in range(1, args.count + 1):
            f.write(json.dumps(generate_event(i)) + "\n")

    print(f"Wrote {args.count} synthetic events to {args.output}")


if __name__ == "__main__":
    main()
