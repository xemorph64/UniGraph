#!/usr/bin/env python3
"""Ingest transactions_input SQL inserts through backend API.

This parser targets the finalized input schema rows used in
`dataset_100_interconnected_txns.sql` and derives behavioral enrichment
features before calling `POST /api/v1/transactions/ingest`.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from typing import Any

import httpx


ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_SQL_FILES = {
    "100": ROOT_DIR / "dataset_100_interconnected_txns.sql",
    "200": ROOT_DIR / "dataset_200_interconnected_txns.sql",
}
DEFAULT_SQL_FILE = DATASET_SQL_FILES["100"]
DEFAULT_API_URL = "http://localhost:8000/api/v1/transactions/ingest"
DEFAULT_REPORT_FILE = (
    ROOT_DIR / "ingest_transactions_input_report.json"
)


@dataclass
class TransactionRow:
    txn_id: str
    event_type: str
    reference_txn_id: str | None
    from_account: str
    to_account: str
    customer_id: str | None
    amount: float
    channel: str
    txn_timestamp: datetime
    narration: str


def _account_numeric_id(account_id: str) -> int:
    digits = re.sub(r"\D", "", str(account_id or ""))
    if not digits:
        return 0
    return int(digits[-6:])


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / float(len(values))


def _std(values: list[float], *, center: float) -> float:
    if not values:
        return 0.0
    variance = sum((value - center) ** 2 for value in values) / float(len(values))
    return variance ** 0.5


def _split_sql_row(row: str) -> list[str]:
    values: list[str] = []
    buffer: list[str] = []
    in_quote = False
    i = 0

    while i < len(row):
        ch = row[i]

        if ch == "'":
            if in_quote and i + 1 < len(row) and row[i + 1] == "'":
                buffer.append("''")
                i += 2
                continue
            in_quote = not in_quote
            buffer.append(ch)
            i += 1
            continue

        if ch == "," and not in_quote:
            values.append("".join(buffer).strip())
            buffer = []
            i += 1
            continue

        buffer.append(ch)
        i += 1

    if buffer:
        values.append("".join(buffer).strip())
    return values


def _parse_sql_literal(token: str):
    token = token.strip()
    upper = token.upper()

    if upper == "NULL":
        return None
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")
    if token in {"TRUE", "FALSE"}:
        return token == "TRUE"
    try:
        if "." in token:
            return float(token)
        return int(token)
    except Exception:
        return token


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            raise ValueError("Missing txn_timestamp")
        normalized = text.replace(" ", "T")
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        parsed = datetime.fromisoformat(normalized)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _txn_sequence(txn_id: str) -> int:
    match = re.search(r"(\d+)$", txn_id)
    if not match:
        return 0
    digits = match.group(1)
    return int(digits[-3:])


def _derive_device_id(seq: int, from_account: str, to_account: str) -> str:
    if 61 <= seq <= 70:
        return "DEV-STRUCT-B"
    if 71 <= seq <= 80:
        return "DEV-LAYER-C"
    if 81 <= seq <= 90:
        return "DEV-DORM-D"
    if 91 <= seq <= 100:
        return "DEV-MULE-E"
    if 51 <= seq <= 60:
        return f"DEV-CYCLE-A-{seq % 2}"
    return f"DEV-{from_account}-{to_account}"


def _derive_dormant_flag(
    *,
    seq: int,
    amount: float,
    inactivity_days: float | None,
    event_type: str,
) -> bool:
    if 81 <= seq <= 90 and amount >= 500000:
        return True
    if inactivity_days is not None and inactivity_days >= 2.0 and amount >= 250000:
        return True
    if (
        event_type in {"REVERSAL", "ADJUSTMENT"}
        and inactivity_days is not None
        and inactivity_days >= 1.5
        and amount >= 200000
    ):
        return True
    return False


def _path_exists_within_24h(
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
        adjacency.setdefault(tx.from_account, set()).add(tx.to_account)

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


def parse_transactions(sql_file: Path) -> list[TransactionRow]:
    rows: list[TransactionRow] = []
    for raw_line in sql_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("('"):
            continue

        if line.endswith(","):
            line = line[:-1]
        elif line.endswith(";"):
            line = line[:-1]

        if not (line.startswith("(") and line.endswith(")")):
            continue

        inner = line[1:-1]
        parts = [_parse_sql_literal(p) for p in _split_sql_row(inner)]
        if len(parts) != 20:
            raise ValueError(f"Expected 20 columns, got {len(parts)} for line: {raw_line}")

        (
            txn_id,
            event_type,
            reference_txn_id,
            from_account,
            to_account,
            customer_id,
            amount,
            _currency,
            channel,
            _txn_status,
            txn_timestamp,
            _value_date,
            _source_system,
            _branch_code,
            _ifsc_code,
            _external_ref_type,
            _external_ref_no,
            narration,
            _created_at,
            _updated_at,
        ) = parts

        rows.append(
            TransactionRow(
                txn_id=str(txn_id),
                event_type=str(event_type or "POSTED").upper(),
                reference_txn_id=(
                    str(reference_txn_id) if reference_txn_id is not None else None
                ),
                from_account=str(from_account),
                to_account=str(to_account),
                customer_id=str(customer_id) if customer_id is not None else None,
                amount=float(amount),
                channel=str(channel),
                txn_timestamp=_parse_datetime(txn_timestamp),
                narration=str(narration) if narration else "Transfer",
            )
        )

    rows.sort(key=lambda row: row.txn_timestamp)
    return rows


def build_enriched_payloads(
    rows: list[TransactionRow],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payloads: list[dict[str, Any]] = []
    enrichment_trace: list[dict[str, Any]] = []

    history: list[TransactionRow] = []
    seen_device_accounts: dict[str, set[str]] = {}
    last_activity: dict[str, datetime] = {}
    sender_device_events: dict[str, list[tuple[datetime, str]]] = {}
    sender_ip_events: dict[str, list[tuple[datetime, str]]] = {}
    sender_channel_events: dict[str, list[tuple[datetime, str]]] = {}

    for tx in rows:
        window_1h = tx.txn_timestamp - timedelta(hours=1)
        window_24h = tx.txn_timestamp - timedelta(hours=24)
        window_30d = tx.txn_timestamp - timedelta(days=30)

        sender_participation_1h = sum(
            1
            for prev in history
            if prev.txn_timestamp >= window_1h
            and (
                prev.from_account == tx.from_account
                or prev.to_account == tx.from_account
            )
        )
        sender_participation_24h = sum(
            1
            for prev in history
            if prev.txn_timestamp >= window_24h
            and (
                prev.from_account == tx.from_account
                or prev.to_account == tx.from_account
            )
        )

        receiver_structuring_count_24h = sum(
            1
            for prev in history
            if prev.txn_timestamp >= window_24h
            and prev.to_account == tx.to_account
            and 40000 <= prev.amount < 50000
        )
        if 40000 <= tx.amount < 50000:
            receiver_structuring_count_24h += 1

        velocity_1h = sender_participation_1h + 1
        velocity_24h = max(sender_participation_24h + 1, receiver_structuring_count_24h)

        round_trip_closure = _path_exists_within_24h(
            history=history,
            current_ts=tx.txn_timestamp,
            source=tx.to_account,
            target=tx.from_account,
        )

        description = tx.narration
        if tx.reference_txn_id and tx.event_type in {"REVERSAL", "ADJUSTMENT"}:
            description = f"{description} ROUND_TRIP"
        elif round_trip_closure and "ROUND_TRIP" not in description.upper():
            description = f"{description} ROUND_TRIP"

        seq = _txn_sequence(tx.txn_id)
        device_id = _derive_device_id(seq, tx.from_account, tx.to_account)
        ip_token = (
            f"IP-{(_account_numeric_id(tx.from_account) + _account_numeric_id(tx.to_account) + seq) % 37}"
        )
        existing_accounts = seen_device_accounts.get(device_id, set())
        device_accounts = set(existing_accounts)
        device_accounts.update({tx.from_account, tx.to_account})
        seen_device_accounts[device_id] = device_accounts
        device_account_count = max(1, len(device_accounts))

        sender_device_events.setdefault(tx.from_account, [])
        sender_ip_events.setdefault(tx.from_account, [])
        sender_channel_events.setdefault(tx.from_account, [])

        device_events_30d = [
            dev
            for ts, dev in sender_device_events[tx.from_account]
            if ts >= window_30d
        ]
        ip_events_30d = [
            token
            for ts, token in sender_ip_events[tx.from_account]
            if ts >= window_30d
        ]
        channel_events_24h = [
            channel
            for ts, channel in sender_channel_events[tx.from_account]
            if ts >= window_24h
        ]

        sender_30d = [
            prev
            for prev in history
            if prev.from_account == tx.from_account and prev.txn_timestamp >= window_30d
        ]
        amount_history_30d = [prev.amount for prev in sender_30d] + [tx.amount]
        avg_txn_amount_30d = _mean(amount_history_30d)
        std_txn_amount = _std(amount_history_30d, center=avg_txn_amount_30d)
        amount_zscore = (
            (tx.amount - avg_txn_amount_30d) / std_txn_amount
            if std_txn_amount > 0.0
            else 0.0
        )

        channel_set_24h = set(channel_events_24h)
        channel_set_24h.add(tx.channel)
        channel_switch_count = max(0, len(channel_set_24h) - 1)

        receiver_recent_inflow_24h = sum(
            1
            for prev in history
            if prev.txn_timestamp >= window_24h and prev.to_account == tx.to_account
        )
        counterparty_risk_score = min(
            0.99,
            0.15
            + (receiver_recent_inflow_24h * 0.06)
            + (0.18 if device_account_count >= 4 else 0.0)
            + (0.12 if round_trip_closure else 0.0),
        )

        sender_last_seen = last_activity.get(tx.from_account)
        inactivity_days = None
        if sender_last_seen:
            inactivity_days = (
                tx.txn_timestamp - sender_last_seen
            ).total_seconds() / 86400.0
        is_dormant = _derive_dormant_flag(
            seq=seq,
            amount=tx.amount,
            inactivity_days=inactivity_days,
            event_type=tx.event_type,
        )

        from_numeric = _account_numeric_id(tx.from_account)
        to_numeric = _account_numeric_id(tx.to_account)
        account_age_days = 365 + (from_numeric % 2500)
        kyc_tier = 1 + (from_numeric % 3)
        customer_age = 21 + (from_numeric % 38)
        avg_monthly_balance = float(50000 + (from_numeric % 25) * 20000)
        geo_distance_from_home = float(abs(from_numeric - to_numeric) % 120)
        if tx.channel in {"RTGS", "SWIFT"}:
            geo_distance_from_home += 5.0

        transaction_count_30d = len(sender_30d) + 1
        device_count_30d = len(set(device_events_30d + [device_id]))
        ip_count_30d = len(set(ip_events_30d + [ip_token]))

        hour_of_day = tx.txn_timestamp.hour
        day_of_week = tx.txn_timestamp.weekday()
        is_weekend = day_of_week >= 5
        is_holiday = False
        device_risk_flag = device_account_count >= 4
        is_international = tx.channel == "SWIFT"

        payloads.append(
            {
                "txn_id": tx.txn_id,
                "from_account": tx.from_account,
                "to_account": tx.to_account,
                "amount": tx.amount,
                "channel": tx.channel,
                "customer_id": tx.customer_id,
                "description": description,
                "device_id": device_id,
                "is_dormant": is_dormant,
                "device_account_count": device_account_count,
                "velocity_1h": velocity_1h,
                "velocity_24h": velocity_24h,
                "account_age_days": account_age_days,
                "kyc_tier": kyc_tier,
                "transaction_count_30d": transaction_count_30d,
                "avg_txn_amount_30d": avg_txn_amount_30d,
                "device_count_30d": device_count_30d,
                "ip_count_30d": ip_count_30d,
                "customer_age": customer_age,
                "avg_monthly_balance": avg_monthly_balance,
                "avg_txn_amount": avg_txn_amount_30d,
                "std_txn_amount": std_txn_amount,
                "max_txn_amount": max(amount_history_30d),
                "min_txn_amount": min(amount_history_30d),
                "hour_of_day": hour_of_day,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "is_holiday": is_holiday,
                "geo_distance_from_home": geo_distance_from_home,
                "device_risk_flag": device_risk_flag,
                "counterparty_risk_score": counterparty_risk_score,
                "is_international": is_international,
                "channel_switch_count": channel_switch_count,
                "amount_zscore": amount_zscore,
            }
        )

        enrichment_trace.append(
            {
                "txn_id": tx.txn_id,
                "txn_timestamp": tx.txn_timestamp.isoformat(),
                "event_type": tx.event_type,
                "velocity_1h": velocity_1h,
                "velocity_24h": velocity_24h,
                "device_id": device_id,
                "ip_token": ip_token,
                "device_account_count": device_account_count,
                "is_dormant": is_dormant,
                "round_trip_closure": round_trip_closure,
                "transaction_count_30d": transaction_count_30d,
                "avg_txn_amount_30d": avg_txn_amount_30d,
                "amount_zscore": amount_zscore,
                "channel_switch_count": channel_switch_count,
            }
        )

        history.append(tx)
        last_activity[tx.from_account] = tx.txn_timestamp
        last_activity[tx.to_account] = tx.txn_timestamp
        sender_device_events[tx.from_account].append((tx.txn_timestamp, device_id))
        sender_ip_events[tx.from_account].append((tx.txn_timestamp, ip_token))
        sender_channel_events[tx.from_account].append((tx.txn_timestamp, tx.channel))

    return payloads, enrichment_trace


async def ingest_rows(
    rows: list[dict[str, Any]],
    api_url: str,
    *,
    timeout: float,
    delay_ms: int,
    ml_direct_verify: bool = False,
    ml_score_url: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "success": 0,
        "flagged": 0,
        "errors": 0,
        "rule_counts": Counter(),
        "primary_type_counts": Counter(),
        "model_versions": Counter(),
        "ml_direct_success": 0,
        "records": [],
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        for index, row in enumerate(rows, start=1):
            try:
                response = await client.post(api_url, json=row)
                if response.status_code != 200:
                    result["errors"] += 1
                    print(f"ERR {row['txn_id']}: HTTP {response.status_code}")
                    result["records"].append(
                        {
                            "txn_id": row["txn_id"],
                            "ok": False,
                            "status_code": response.status_code,
                            "error": response.text,
                        }
                    )
                    continue

                body = response.json()
                result["success"] += 1

                risk_score = float(body.get("risk_score", 0.0) or 0.0)
                rule_violations = [
                    str(rule).upper()
                    for rule in (body.get("rule_violations") or [])
                    if rule
                ]
                primary_type = body.get("primary_fraud_type")

                if body.get("is_flagged"):
                    result["flagged"] += 1
                    print(
                        "FLAG "
                        f"{row['txn_id']} risk={risk_score:.1f} "
                        f"primary={primary_type or '-'} rules={','.join(rule_violations) or '-'}"
                    )

                result["rule_counts"].update(rule_violations)
                if primary_type:
                    result["primary_type_counts"][str(primary_type).upper()] += 1

                model_version = body.get("model_version")
                if model_version:
                    result["model_versions"][str(model_version)] += 1

                record = {
                    "txn_id": row["txn_id"],
                    "ok": True,
                    "status_code": response.status_code,
                    "risk_score": risk_score,
                    "risk_level": body.get("risk_level"),
                    "is_flagged": bool(body.get("is_flagged")),
                    "alert_id": body.get("alert_id"),
                    "rule_violations": rule_violations,
                    "primary_fraud_type": primary_type,
                    "gnn_fraud_probability": body.get("gnn_fraud_probability"),
                    "if_anomaly_score": body.get("if_anomaly_score"),
                    "xgboost_risk_score": body.get("xgboost_risk_score"),
                    "model_version": model_version,
                }

                if ml_direct_verify and ml_score_url:
                    try:
                        direct_payload = {
                            "enriched_transaction": row,
                            "graph_features": {},
                        }
                        ml_response = await client.post(ml_score_url, json=direct_payload)
                        if ml_response.status_code == 200:
                            direct_body = ml_response.json()
                            record["ml_direct"] = {
                                "ok": True,
                                "gnn_fraud_probability": direct_body.get(
                                    "gnn_fraud_probability"
                                ),
                                "if_anomaly_score": direct_body.get("if_anomaly_score"),
                                "xgboost_risk_score": direct_body.get(
                                    "xgboost_risk_score"
                                ),
                                "model_version": direct_body.get("model_version"),
                                "scoring_latency_ms": direct_body.get(
                                    "scoring_latency_ms"
                                ),
                            }
                            result["ml_direct_success"] += 1
                        else:
                            record["ml_direct"] = {
                                "ok": False,
                                "status_code": ml_response.status_code,
                                "error": ml_response.text,
                            }
                    except Exception as direct_exc:
                        record["ml_direct"] = {
                            "ok": False,
                            "status_code": 0,
                            "error": str(direct_exc),
                        }

                result["records"].append(record)
            except Exception as exc:
                result["errors"] += 1
                print(f"ERR {row['txn_id']}: {exc}")
                result["records"].append(
                    {
                        "txn_id": row["txn_id"],
                        "ok": False,
                        "status_code": 0,
                        "error": str(exc),
                    }
                )

            if index % 20 == 0:
                print(
                    f"Progress: {index}/{len(rows)} "
                    f"success={result['success']} flagged={result['flagged']} errors={result['errors']}"
                )

            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)

    return result


async def fetch_runtime_snapshots(
    api_url: str,
    timeout: float,
    *,
    ml_score_url: str | None = None,
) -> dict[str, Any]:
    backend_root = api_url.split("/api/v1")[0].rstrip("/")
    urls = {
        "health": f"{backend_root}/health",
        "alerts": f"{backend_root}/api/v1/alerts/?page=1&page_size=5",
        "graph_analytics_status": f"{backend_root}/api/v1/graph-analytics/status",
    }
    if ml_score_url:
        ml_base = ml_score_url.split("/api/v1")[0].rstrip("/")
        urls["ml_health"] = f"{ml_base}/api/v1/ml/health"

    snapshots: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for name, url in urls.items():
            try:
                response = await client.get(url)
                payload: Any
                try:
                    payload = response.json()
                except Exception:
                    payload = response.text

                snapshots[name] = {
                    "url": url,
                    "status_code": response.status_code,
                    "payload": payload,
                }
            except Exception as exc:
                snapshots[name] = {
                    "url": url,
                    "status_code": 0,
                    "error": str(exc),
                }

    return snapshots


def build_report(
    *,
    sql_file: Path,
    api_url: str,
    parsed_count: int,
    ingest_result: dict[str, Any],
    enrichment_trace: list[dict[str, Any]],
    runtime_snapshots: dict[str, Any],
) -> dict[str, Any]:
    records = ingest_result.get("records", [])
    success_records = [r for r in records if r.get("ok")]
    ml_outputs_observed = sum(
        1 for row in success_records if row.get("xgboost_risk_score") is not None
    )
    top_risk = sorted(
        success_records,
        key=lambda item: float(item.get("risk_score", 0.0)),
        reverse=True,
    )[:10]

    max_device_accounts = max(
        (row.get("device_account_count", 1) for row in enrichment_trace),
        default=1,
    )
    max_velocity_1h = max((row.get("velocity_1h", 0) for row in enrichment_trace), default=0)
    max_velocity_24h = max((row.get("velocity_24h", 0) for row in enrichment_trace), default=0)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sql_file": str(sql_file),
        "ingest_endpoint": api_url,
        "totals": {
            "transactions_parsed": parsed_count,
            "ingest_success": ingest_result["success"],
            "ingest_errors": ingest_result["errors"],
            "flagged": ingest_result["flagged"],
            "ml_outputs_observed": ml_outputs_observed,
            "ml_direct_success": ingest_result.get("ml_direct_success", 0),
            "model_versions": dict(ingest_result.get("model_versions", {})),
            "rule_counts": dict(ingest_result["rule_counts"]),
            "primary_type_counts": dict(ingest_result["primary_type_counts"]),
        },
        "enrichment_summary": {
            "max_device_account_count": max_device_accounts,
            "max_velocity_1h": max_velocity_1h,
            "max_velocity_24h": max_velocity_24h,
        },
        "runtime_snapshots": runtime_snapshots,
        "top_risk_transactions": top_risk,
        "enrichment_trace": enrichment_trace,
        "ingest_records": records,
    }


def print_summary(report: dict[str, Any]) -> None:
    totals = report["totals"]
    print("\nIngest Summary")
    print("-" * 50)
    print(f"Parsed rows: {totals['transactions_parsed']}")
    print(f"Success: {totals['ingest_success']}")
    print(f"Flagged: {totals['flagged']}")
    print(f"Errors: {totals['ingest_errors']}")
    print(f"ML outputs observed: {totals.get('ml_outputs_observed', 0)}")
    if totals.get("ml_direct_success", 0):
        print(f"ML direct verify success: {totals['ml_direct_success']}")

    model_versions = totals.get("model_versions") or {}
    if model_versions:
        print("Model versions:")
        for version, count in sorted(
            model_versions.items(), key=lambda item: (-item[1], item[0])
        ):
            print(f"  {version}: {count}")

    print("\nRule Counts")
    print("-" * 50)
    if totals["rule_counts"]:
        for rule, count in sorted(
            totals["rule_counts"].items(),
            key=lambda item: (-item[1], item[0]),
        ):
            print(f"{rule}: {count}")
    else:
        print("No rules fired")

    print("\nPrimary Fraud Type Counts")
    print("-" * 50)
    if totals["primary_type_counts"]:
        for fraud_type, count in sorted(
            totals["primary_type_counts"].items(),
            key=lambda item: (-item[1], item[0]),
        ):
            print(f"{fraud_type}: {count}")
    else:
        print("No primary fraud type values")


async def _main_async(
    sql_file: Path,
    api_url: str,
    *,
    report_file: Path,
    timeout: float,
    delay_ms: int,
    dry_run: bool,
    ml_direct_verify: bool,
    ml_score_url: str,
) -> int:
    rows = parse_transactions(sql_file)
    payloads, enrichment_trace = build_enriched_payloads(rows)

    print(f"Parsed rows: {len(rows)}")
    print(f"Prepared payloads: {len(payloads)}")

    if dry_run:
        print("Dry run mode: skipping API ingestion")
        for sample in payloads[:5]:
            print(json.dumps(sample, ensure_ascii=True))
        return 0

    ingest_result = await ingest_rows(
        payloads,
        api_url,
        timeout=max(1.0, timeout),
        delay_ms=max(0, delay_ms),
        ml_direct_verify=ml_direct_verify,
        ml_score_url=ml_score_url,
    )
    runtime_snapshots = await fetch_runtime_snapshots(
        api_url,
        timeout=max(1.0, timeout),
        ml_score_url=ml_score_url,
    )

    report = build_report(
        sql_file=sql_file,
        api_url=api_url,
        parsed_count=len(rows),
        ingest_result=ingest_result,
        enrichment_trace=enrichment_trace,
        runtime_snapshots=runtime_snapshots,
    )
    report_file.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")

    print_summary(report)
    print(f"\nReport written: {report_file}")

    return 0 if ingest_result["errors"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest transactions_input SQL rows via backend API"
    )
    parser.add_argument(
        "--dataset",
        choices=sorted(DATASET_SQL_FILES.keys()),
        help="Use canonical dataset alias instead of manual --sql-file path",
    )
    parser.add_argument("--sql-file", type=Path, default=DEFAULT_SQL_FILE)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--report-file", type=Path, default=DEFAULT_REPORT_FILE)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--delay-ms", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ml-direct-verify", action="store_true")
    parser.add_argument("--ml-score-url", default="http://localhost:8002/api/v1/ml/score")
    args = parser.parse_args()

    if args.dataset:
        args.sql_file = DATASET_SQL_FILES[args.dataset]

    if not args.sql_file.exists():
        print(f"SQL file not found: {args.sql_file}")
        return 1

    report_path = args.report_file.resolve()
    return asyncio.run(
        _main_async(
            args.sql_file.resolve(),
            args.api_url,
            report_file=report_path,
            timeout=args.timeout,
            delay_ms=args.delay_ms,
            dry_run=args.dry_run,
            ml_direct_verify=args.ml_direct_verify,
            ml_score_url=args.ml_score_url,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())