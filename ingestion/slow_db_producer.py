from __future__ import annotations

import argparse
import random
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json


CHANNELS = ["UPI", "IMPS", "NEFT", "RTGS", "CASH", "SWIFT"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "Z"


def _connect_with_retry(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    retry_seconds: int,
):
    while True:
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
            )
            conn.autocommit = False
            print(
                f"[{_fmt_ts(_utc_now())}] [PRODUCER] Connected to Postgres {host}:{port}/{dbname}",
                flush=True,
            )
            return conn
        except psycopg2.Error as exc:
            print(
                f"[{_fmt_ts(_utc_now())}] [PRODUCER][WARN] DB connection failed: {exc}. "
                f"Retrying in {retry_seconds}s...",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(retry_seconds)


def _build_txn(seq: int, high_amount: float) -> dict[str, Any]:
    now = _utc_now()
    base_txn_id = now.strftime("%Y%m%d%H%M%S")
    txn_id = f"TXN-SLOW-{base_txn_id}-{seq:06d}-{uuid.uuid4().hex[:6]}"

    is_high = seq % 3 == 0
    amount = high_amount if is_high else round(random.uniform(125.0, 3500.0), 2)

    # Keep a stable account for high-value rows so violations are easy to track.
    from_account = "UBI30100099999999" if is_high else f"UBI3010001{seq % 100000:05d}"
    to_account = f"UBI3010002{(seq * 7) % 100000:05d}"

    return {
        "txn_id": txn_id,
        "from_account": from_account,
        "to_account": to_account,
        "amount": amount,
        "channel": CHANNELS[seq % len(CHANNELS)],
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "customer_id": f"CUST-SLOW-{seq % 10000:04d}",
        "device_fingerprint": f"sha256:dev-slow-{seq:06d}",
        "ip_address": f"sha256:ip-slow-{seq:06d}",
        "location": {
            "lat": round(8 + ((seq * 13) % 4200) / 100.0, 6),
            "lon": round(68 + ((seq * 17) % 4300) / 100.0, 6),
        },
        "is_high": is_high,
    }


def _insert_txn(conn, txn: dict[str, Any]) -> None:
    with conn.cursor() as cur:
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
                txn["txn_id"],
                txn["from_account"],
                txn["to_account"],
                txn["amount"],
                txn["channel"],
                txn["timestamp"],
                txn["customer_id"],
                txn["device_fingerprint"],
                txn["ip_address"],
                Json(txn["location"]),
            ),
        )
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert one transaction/second into Postgres for live CDC demo")
    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--db-port", type=int, default=5432)
    parser.add_argument("--db-name", default="finacle_cbs")
    parser.add_argument("--db-user", default="postgres")
    parser.add_argument("--db-password", default="postgres")
    parser.add_argument("--retry-seconds", type=int, default=3)
    parser.add_argument("--high-amount", type=float, default=750000.0)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--start-seq", type=int, default=1)
    args = parser.parse_args()

    running = True

    def _stop_handler(signum, frame):  # type: ignore[no-untyped-def]
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    print(
        f"[{_fmt_ts(_utc_now())}] [PRODUCER] Starting slow injector: 1 row every {args.interval_seconds:.1f}s",
        flush=True,
    )
    print(
        f"[{_fmt_ts(_utc_now())}] [PRODUCER] Every 3rd row uses high amount={args.high_amount:.2f}",
        flush=True,
    )

    conn = _connect_with_retry(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
        retry_seconds=args.retry_seconds,
    )

    seq = args.start_seq

    try:
        while running:
            loop_start = time.time()
            txn = _build_txn(seq, args.high_amount)
            try:
                _insert_txn(conn, txn)
                level = "HIGH" if txn["is_high"] else "NORMAL"
                print(
                    f"[{_fmt_ts(_utc_now())}] [PRODUCER] [{level}] "
                    f"txn_id={txn['txn_id']} from={txn['from_account']} "
                    f"amount={txn['amount']:.2f} channel={txn['channel']}",
                    flush=True,
                )
                seq += 1
            except psycopg2.Error as exc:
                print(
                    f"[{_fmt_ts(_utc_now())}] [PRODUCER][WARN] Insert failed: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                try:
                    conn.rollback()
                except psycopg2.Error:
                    pass
                try:
                    conn.close()
                except psycopg2.Error:
                    pass
                conn = _connect_with_retry(
                    host=args.db_host,
                    port=args.db_port,
                    dbname=args.db_name,
                    user=args.db_user,
                    password=args.db_password,
                    retry_seconds=args.retry_seconds,
                )

            elapsed = time.time() - loop_start
            sleep_for = max(0.0, args.interval_seconds - elapsed)
            time.sleep(sleep_for)
    finally:
        try:
            conn.close()
        except psycopg2.Error:
            pass
        print(f"[{_fmt_ts(_utc_now())}] [PRODUCER] Stopped", flush=True)


if __name__ == "__main__":
    main()