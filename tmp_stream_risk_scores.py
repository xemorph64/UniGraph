import csv
import io
import json
import os
import re
from datetime import datetime
import urllib.request
import urllib.error
from pathlib import Path

SQL_FILE = Path("transactions_inserts.sql")
API_URL = "http://localhost:8000/api/v1/transactions/ingest"
LINE_RE = re.compile(r"INSERT INTO transactions VALUES \((.*)\);", re.IGNORECASE)
MAX_ROWS = int(os.getenv("MAX_ROWS", "120"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "8"))


def parse_ts(value: str) -> datetime:
    raw = (value or "").strip()
    if not raw:
        return datetime.min
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return datetime.min


def parse_values(raw: str):
    reader = csv.reader(io.StringIO(raw), delimiter=",", quotechar="'", skipinitialspace=True)
    return next(reader)


def post_json(payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_payload(vals: list[str]) -> dict:
    txn_id = vals[0].strip()
    from_account = vals[3].strip()
    to_account = vals[4].strip()
    customer_id = vals[5].strip() or f"CUST-{from_account}"
    amount = float(vals[6].strip() or 0)
    channel = (vals[8].strip() or "IMPS").upper()
    description = vals[12].strip() if len(vals) > 12 and vals[12].strip() else "Payment"
    txn_ts = parse_ts(vals[10] if len(vals) > 10 else "")
    last_active_ts = parse_ts(vals[11] if len(vals) > 11 else "")

    history = build_payload.account_timestamps.setdefault(from_account, [])
    if txn_ts != datetime.min:
        history = [ts for ts in history if (txn_ts - ts).total_seconds() <= 86400]
        history.append(txn_ts)
        build_payload.account_timestamps[from_account] = history
        velocity_24h = len(history)
        velocity_1h = sum(1 for ts in history if (txn_ts - ts).total_seconds() <= 3600)
    else:
        velocity_1h = 0
        velocity_24h = 0

    dormant_days = (txn_ts - last_active_ts).days if txn_ts != datetime.min and last_active_ts != datetime.min else 0
    is_dormant = dormant_days >= 120
    device_account_count = max(1, min(4, int(velocity_24h / 3) + (1 if channel in {"SWIFT", "CASH"} else 0)))

    return {
        "txn_id": txn_id,
        "from_account": from_account,
        "to_account": to_account,
        "amount": amount,
        "channel": channel,
        "customer_id": customer_id,
        "description": description,
        "device_id": f"DEV-{txn_id}",
        "velocity_1h": velocity_1h,
        "velocity_24h": velocity_24h,
        "device_account_count": device_account_count,
        "is_dormant": is_dormant,
    }


build_payload.account_timestamps = {}


def main():
    if not SQL_FILE.exists():
        return

    rows = []
    for line in SQL_FILE.read_text(encoding="utf-8").splitlines():
        m = LINE_RE.search(line)
        if m:
            rows.append(m.group(1))

    if MAX_ROWS > 0:
        rows = rows[:MAX_ROWS]

    for raw in rows:
        vals = parse_values(raw)
        payload = build_payload(vals)

        try:
            result = post_json(payload)
            score = result.get("risk_score")
            types = result.get("rule_violations") or []
            type_text = ",".join(types) if types else "NONE"
            print(f"{payload['txn_id']} {score} {type_text}", flush=True)
        except urllib.error.URLError:
            print(f"{payload['txn_id']} ERR BACKEND_UNAVAILABLE", flush=True)
            continue
        except Exception:
            print(f"{payload['txn_id']} ERR INGEST_FAILED", flush=True)
            continue


if __name__ == "__main__":
    main()
