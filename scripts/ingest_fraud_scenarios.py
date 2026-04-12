#!/usr/bin/env python3
"""Ingest real fraud_scenarios SQL data through the backend scoring pipeline.

This script intentionally does not insert alert rows directly. It parses account and
transaction inserts from fraud_scenarios.sql, computes stream-like enrichment
features, sends transactions to POST /api/v1/transactions/ingest, and compares
backend detections against expected scenario typologies from the SQL alert rows.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQL_FILE = ROOT_DIR / "fraud_scenarios.sql"
DEFAULT_API_URL = "http://localhost:8000/api/v1/transactions/ingest"
DEFAULT_ALERTS_URL = "http://localhost:8000/api/v1/alerts/?page=1&page_size=500"
DEFAULT_REPORT_FILE = ROOT_DIR / "ingest_fraud_scenarios_report.json"

NOW_INTERVAL_RE = re.compile(
    r"NOW\(\)\s*-\s*INTERVAL\s*'(?P<value>\d+)\s+(?P<unit>minute|minutes|hour|hours|day|days)'",
    re.IGNORECASE,
)

INSERT_BLOCK_RE = r"INSERT\s+INTO\s+{table}\s+VALUES\s*(?P<body>.*?);"

EXPECTED_RULE_MAP = {
    "ROUND-TRIPPING": "ROUND_TRIPPING",
    "STRUCTURING": "STRUCTURING",
    "DORMANT ACCOUNT AWAKENING": "DORMANT_AWAKENING",
    "RAPID LAYERING": "RAPID_LAYERING",
    "MULE ACCOUNT NETWORK": "MULE_NETWORK",
}


@dataclass
class AccountRow:
    account_id: str
    is_dormant: bool


@dataclass
class TransactionRow:
    txn_id: str
    sender_account: str
    receiver_account: str
    amount: float
    channel: str
    txn_timestamp: datetime
    device_id: str
    narration: str


@dataclass
class ExpectedAlertRow:
    alert_id: str
    txn_id: str
    account_id: str
    fraud_type: str


def normalize_token(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def expected_rule_name(fraud_type: str) -> str:
    direct = EXPECTED_RULE_MAP.get(fraud_type.upper())
    return direct or normalize_token(fraud_type)


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y", "t"}


def parse_now_expression(token: str, now_ref: datetime) -> datetime:
    token = token.strip()
    if token.upper() == "NOW()":
        return now_ref

    match = NOW_INTERVAL_RE.fullmatch(token)
    if not match:
        raise ValueError(f"Unsupported datetime token: {token}")

    value = int(match.group("value"))
    unit = match.group("unit").lower()
    if unit.startswith("minute"):
        delta = timedelta(minutes=value)
    elif unit.startswith("hour"):
        delta = timedelta(hours=value)
    else:
        delta = timedelta(days=value)
    return now_ref - delta


def split_sql_row(row: str) -> list[str]:
    values: list[str] = []
    buff: list[str] = []
    in_quote = False
    paren_depth = 0
    i = 0

    while i < len(row):
        ch = row[i]

        if ch == "'":
            if in_quote and i + 1 < len(row) and row[i + 1] == "'":
                buff.append("''")
                i += 2
                continue
            in_quote = not in_quote
            buff.append(ch)
            i += 1
            continue

        if not in_quote:
            if ch == "(":
                paren_depth += 1
            elif ch == ")" and paren_depth > 0:
                paren_depth -= 1
            elif ch == "," and paren_depth == 0:
                values.append("".join(buff).strip())
                buff = []
                i += 1
                continue

        buff.append(ch)
        i += 1

    if buff:
        values.append("".join(buff).strip())

    return values


def parse_literal(token: str, now_ref: datetime) -> Any:
    token = token.strip()
    upper = token.upper()

    if upper == "NULL":
        return None
    if upper == "TRUE":
        return True
    if upper == "FALSE":
        return False
    if upper.startswith("NOW()"):
        return parse_now_expression(token, now_ref)

    if token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")

    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if re.fullmatch(r"-?\d+\.\d+", token):
        return float(token)

    return token


def extract_insert_blocks(content: str, table: str) -> list[str]:
    pattern = re.compile(INSERT_BLOCK_RE.format(table=re.escape(table)), re.IGNORECASE | re.DOTALL)
    return [m.group("body") for m in pattern.finditer(content)]


def extract_rows(block: str) -> list[str]:
    rows: list[str] = []
    depth = 0
    start_idx: int | None = None

    for idx, ch in enumerate(block):
        if ch == "(":
            if depth == 0:
                start_idx = idx + 1
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start_idx is not None:
                rows.append(block[start_idx:idx].strip())
                start_idx = None

    return rows


def parse_accounts(content: str, now_ref: datetime) -> dict[str, AccountRow]:
    accounts: dict[str, AccountRow] = {}
    for block in extract_insert_blocks(content, "accounts"):
        for row in extract_rows(block):
            cols = [parse_literal(c, now_ref) for c in split_sql_row(row)]
            if len(cols) < 6:
                continue
            account_id = str(cols[0])
            accounts[account_id] = AccountRow(
                account_id=account_id,
                is_dormant=parse_bool(cols[5]),
            )
    return accounts


def parse_transactions(content: str, now_ref: datetime) -> list[TransactionRow]:
    txns: list[TransactionRow] = []
    for block in extract_insert_blocks(content, "transactions"):
        for row in extract_rows(block):
            cols = [parse_literal(c, now_ref) for c in split_sql_row(row)]
            if len(cols) < 12:
                continue

            txns.append(
                TransactionRow(
                    txn_id=str(cols[0]),
                    sender_account=str(cols[1]),
                    receiver_account=str(cols[2]),
                    amount=float(cols[3]),
                    channel=str(cols[4]).upper(),
                    txn_timestamp=cols[5] if isinstance(cols[5], datetime) else now_ref,
                    device_id=str(cols[6] or "DEV-UNKNOWN"),
                    narration=str(cols[11] or "Transfer"),
                )
            )

    txns.sort(key=lambda t: t.txn_timestamp)
    return txns


def parse_expected_alerts(content: str, now_ref: datetime) -> list[ExpectedAlertRow]:
    expected: list[ExpectedAlertRow] = []
    for block in extract_insert_blocks(content, "alerts"):
        for row in extract_rows(block):
            cols = [parse_literal(c, now_ref) for c in split_sql_row(row)]
            if len(cols) < 4:
                continue
            expected.append(
                ExpectedAlertRow(
                    alert_id=str(cols[0]),
                    txn_id=str(cols[1]),
                    account_id=str(cols[2]),
                    fraud_type=str(cols[3]),
                )
            )
    return expected


def path_exists_within_24h(
    history: list[TransactionRow],
    current_ts: datetime,
    source: str,
    target: str,
    max_depth: int = 5,
) -> bool:
    if not source or not target:
        return False

    lower_bound = current_ts - timedelta(hours=24)
    adjacency: dict[str, set[str]] = {}
    for tx in history:
        if tx.txn_timestamp < lower_bound:
            continue
        adjacency.setdefault(tx.sender_account, set()).add(tx.receiver_account)

    queue: deque[tuple[str, int]] = deque([(source, 0)])
    visited = {source}

    while queue:
        node, depth = queue.popleft()
        if depth > max_depth:
            continue
        for nxt in adjacency.get(node, set()):
            if nxt == target:
                return True
            if nxt in visited:
                continue
            visited.add(nxt)
            queue.append((nxt, depth + 1))

    return False


def build_ingest_payloads(
    txns: list[TransactionRow],
    accounts: dict[str, AccountRow],
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    history: list[TransactionRow] = []
    seen_device_accounts: dict[str, set[str]] = {}

    for tx in txns:
        window_1h = tx.txn_timestamp - timedelta(hours=1)
        window_24h = tx.txn_timestamp - timedelta(hours=24)

        sender_participation_1h = sum(
            1
            for prev in history
            if prev.txn_timestamp >= window_1h
            and (prev.sender_account == tx.sender_account or prev.receiver_account == tx.sender_account)
        )
        sender_participation_24h = sum(
            1
            for prev in history
            if prev.txn_timestamp >= window_24h
            and (prev.sender_account == tx.sender_account or prev.receiver_account == tx.sender_account)
        )

        receiver_structuring_count_24h = sum(
            1
            for prev in history
            if prev.txn_timestamp >= window_24h
            and prev.receiver_account == tx.receiver_account
            and 40000 <= prev.amount < 50000
        )
        if 40000 <= tx.amount < 50000:
            receiver_structuring_count_24h += 1

        round_trip_closure = path_exists_within_24h(
            history=history,
            current_ts=tx.txn_timestamp,
            source=tx.receiver_account,
            target=tx.sender_account,
        )

        narration = tx.narration
        if round_trip_closure and "ROUND_TRIP" not in narration.upper():
            narration = f"{narration} ROUND_TRIP"

        dormant_sender = accounts.get(tx.sender_account, AccountRow(tx.sender_account, False)).is_dormant
        dormant_receiver = accounts.get(tx.receiver_account, AccountRow(tx.receiver_account, False)).is_dormant
        is_dormant = bool(dormant_sender or dormant_receiver)

        existing_accounts = seen_device_accounts.get(tx.device_id, set())
        device_accounts = set(existing_accounts)
        device_accounts.update({tx.sender_account, tx.receiver_account})
        device_account_count = max(1, len(device_accounts))

        velocity_1h = sender_participation_1h + 1
        velocity_24h = max(sender_participation_24h + 1, receiver_structuring_count_24h)

        payloads.append(
            {
                "txn_id": tx.txn_id,
                "from_account": tx.sender_account,
                "to_account": tx.receiver_account,
                "amount": tx.amount,
                "channel": tx.channel,
                "customer_id": f"CUST-{tx.sender_account}",
                "description": narration,
                "device_id": tx.device_id,
                "is_dormant": is_dormant,
                "device_account_count": device_account_count,
                "velocity_1h": velocity_1h,
                "velocity_24h": velocity_24h,
            }
        )

        seen_device_accounts[tx.device_id] = device_accounts
        history.append(tx)

    return payloads


async def ingest_payloads(
    api_url: str,
    payloads: list[dict[str, Any]],
    delay_ms: int,
    timeout: float,
    stop_on_error: bool,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=timeout) as client:
        for idx, payload in enumerate(payloads, start=1):
            txn_id = payload["txn_id"]
            try:
                response = await client.post(api_url, json=payload)
                if response.status_code == 200:
                    body = response.json()
                    results.append(
                        {
                            "txn_id": txn_id,
                            "ok": True,
                            "status_code": response.status_code,
                            "response": body,
                        }
                    )
                    print(
                        f"[{idx:02d}/{len(payloads)}] OK {txn_id} risk={body.get('risk_score')} alert={body.get('alert_id') or '-'}"
                    )
                else:
                    body = response.text
                    results.append(
                        {
                            "txn_id": txn_id,
                            "ok": False,
                            "status_code": response.status_code,
                            "error": body,
                        }
                    )
                    print(f"[{idx:02d}/{len(payloads)}] ERR {txn_id} status={response.status_code}")
                    if stop_on_error:
                        break
            except Exception as exc:
                results.append(
                    {
                        "txn_id": txn_id,
                        "ok": False,
                        "status_code": 0,
                        "error": str(exc),
                    }
                )
                print(f"[{idx:02d}/{len(payloads)}] ERR {txn_id} exception={exc}")
                if stop_on_error:
                    break

            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)

    return results


async def fetch_alert_count(alerts_url: str, timeout: float) -> int | None:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(alerts_url)
            if response.status_code != 200:
                return None
            body = response.json()
            items = body.get("items") if isinstance(body, dict) else None
            if not isinstance(items, list):
                return None
            return len(items)
    except Exception:
        return None


def build_validation_rows(
    expected: list[ExpectedAlertRow],
    ingest_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_txn = {row["txn_id"]: row for row in ingest_results}
    rows: list[dict[str, Any]] = []

    for expected_row in expected:
        result = by_txn.get(expected_row.txn_id)
        expected_rule = expected_rule_name(expected_row.fraud_type)

        risk_score = None
        alert_id = None
        actual_rules: list[str] = []
        actual_primary_type = ""
        ok = False

        if result and result.get("ok"):
            body = result.get("response", {})
            risk_score = body.get("risk_score")
            alert_id = body.get("alert_id")
            actual_rules = [normalize_token(x) for x in body.get("rule_violations", [])]
            actual_primary_type = normalize_token(body.get("primary_fraud_type") or "")
            ok = expected_rule == actual_primary_type and bool(alert_id)

        rows.append(
            {
                "txn_id": expected_row.txn_id,
                "expected_typology": expected_row.fraud_type,
                "expected_rule": expected_rule,
                "detected": bool(alert_id),
                "alert_id": alert_id,
                "risk_score": risk_score,
                "actual_rules": actual_rules,
                "actual_primary_type": actual_primary_type,
                "primary_type_match": expected_rule == actual_primary_type,
                "rule_match": expected_rule in actual_rules,
                "pass": ok,
            }
        )

    return rows


def print_validation_table(rows: list[dict[str, Any]]) -> None:
    print("\nScenario Validation")
    print("-" * 120)
    print(
        f"{'TXN ID':<14} {'EXPECTED':<28} {'PRIMARY':<22} {'TYPE':<6} {'RULE':<6} {'ALERT ID':<14} RULES"
    )
    print("-" * 120)
    for row in rows:
        rules = ",".join(row["actual_rules"]) if row["actual_rules"] else "-"
        actual_primary = row["actual_primary_type"] or "-"
        print(
            f"{row['txn_id']:<14} {row['expected_typology']:<28} {actual_primary:<22} {str(row['primary_type_match']):<6} {str(row['rule_match']):<6} {str(row['alert_id'] or '-'): <14} {rules}"
        )

    passed = sum(1 for row in rows if row["pass"])
    print("-" * 120)
    print(f"Validation pass: {passed}/{len(rows)} scenarios")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest fraud_scenarios.sql through backend scoring pipeline")
    parser.add_argument("--sql-file", default=str(DEFAULT_SQL_FILE), help="Path to fraud_scenarios.sql")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Backend ingest endpoint")
    parser.add_argument("--alerts-url", default=DEFAULT_ALERTS_URL, help="Backend alerts list endpoint")
    parser.add_argument("--delay-ms", type=int, default=150, help="Delay between events in milliseconds")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop at first ingest failure")
    parser.add_argument("--dry-run", action="store_true", help="Parse and enrich without sending API calls")
    parser.add_argument("--report-file", default=str(DEFAULT_REPORT_FILE), help="JSON output report path")
    return parser.parse_args()


async def main_async() -> int:
    args = parse_args()

    sql_path = Path(args.sql_file).resolve()
    if not sql_path.exists():
        print(f"SQL file not found: {sql_path}")
        return 1

    now_ref = datetime.now(timezone.utc)
    content = sql_path.read_text(encoding="utf-8")

    accounts = parse_accounts(content, now_ref)
    txns = parse_transactions(content, now_ref)
    expected = parse_expected_alerts(content, now_ref)

    if not txns:
        print("No transactions parsed from SQL input.")
        return 1

    payloads = build_ingest_payloads(txns, accounts)

    print(f"Parsed accounts: {len(accounts)}")
    print(f"Parsed transactions: {len(txns)}")
    print(f"Expected scenario alerts: {len(expected)}")
    print(f"Ingest endpoint: {args.api_url}")

    if args.dry_run:
        print("Dry run enabled; skipping API ingestion.")
        for payload in payloads[:5]:
            print(json.dumps(payload, ensure_ascii=True))
        return 0

    ingest_results = await ingest_payloads(
        api_url=args.api_url,
        payloads=payloads,
        delay_ms=max(0, args.delay_ms),
        timeout=max(1.0, args.timeout),
        stop_on_error=args.stop_on_error,
    )

    success_count = sum(1 for row in ingest_results if row.get("ok"))
    alert_count = sum(
        1
        for row in ingest_results
        if row.get("ok") and row.get("response", {}).get("alert_id")
    )

    validation_rows = build_validation_rows(expected, ingest_results)
    print_validation_table(validation_rows)

    backend_alert_count = await fetch_alert_count(args.alerts_url, timeout=max(1.0, args.timeout))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sql_file": str(sql_path),
        "ingest_endpoint": args.api_url,
        "totals": {
            "transactions_parsed": len(txns),
            "ingest_success": success_count,
            "ingest_errors": len(ingest_results) - success_count,
            "alerts_created_during_ingest": alert_count,
            "alerts_visible_in_backend_list": backend_alert_count,
            "scenario_validation_pass": sum(1 for row in validation_rows if row["pass"]),
            "scenario_validation_total": len(validation_rows),
        },
        "scenario_validation": validation_rows,
        "ingest_results": ingest_results,
    }

    report_path = Path(args.report_file).resolve()
    report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")

    print("\nIngest Summary")
    print("-" * 40)
    print(f"Ingest success: {success_count}/{len(payloads)}")
    print(f"Alerts created: {alert_count}")
    if backend_alert_count is not None:
        print(f"Alerts visible via GET /alerts: {backend_alert_count}")
    else:
        print("Alerts visible via GET /alerts: unavailable")
    print(f"Report written: {report_path}")

    return 0 if success_count == len(payloads) else 2


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
