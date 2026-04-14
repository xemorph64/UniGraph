from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * p
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return ordered[low]
    fraction = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def _build_payload(run_id: str, index: int) -> dict[str, Any]:
    suffix = (index % 50000) + 100000
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    amount = 50000.0 + float((index % 200) * 5000)
    return {
        "txn_id": f"{run_id}-{index:08d}",
        "from_account": f"UBI301000{suffix:08d}",
        "to_account": f"UBI301000{(suffix + 1):08d}",
        "amount": amount,
        "channel": random.choice(["IMPS", "UPI", "NEFT", "RTGS"]),
        "customer_id": f"CUST-{suffix}",
        "description": "backend-ingest-benchmark",
        "device_id": f"BENCH-DEV-{index % 4096}",
        "is_dormant": False,
        "device_account_count": 1 + (index % 3),
        "velocity_1h": 2 + (index % 6),
        "velocity_24h": 4 + (index % 12),
        "timestamp": now_ts,
    }


async def run_benchmark(
    url: str,
    count: int,
    concurrency: int,
    timeout_seconds: float,
    batch_size: int,
) -> dict[str, Any]:
    run_id = f"BENCH-INGEST-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    latencies_ms: list[float] = []
    success = 0
    errors = 0
    alerts = 0
    is_batch_endpoint = url.rstrip("/").endswith("/transactions/ingest/batch")
    if batch_size > 1 and not is_batch_endpoint:
        raise ValueError("--batch-size > 1 requires --url to /transactions/ingest/batch")

    queue: asyncio.Queue[list[dict[str, Any]] | None] = asyncio.Queue()
    effective_batch_size = max(1, batch_size)
    for batch_start in range(0, count, effective_batch_size):
        batch_payload = [
            _build_payload(run_id, idx)
            for idx in range(batch_start, min(count, batch_start + effective_batch_size))
        ]
        queue.put_nowait(batch_payload)

    limits = httpx.Limits(
        max_connections=max(200, concurrency * 4),
        max_keepalive_connections=max(100, concurrency * 2),
    )

    start_ns = time.perf_counter_ns()

    async with httpx.AsyncClient(timeout=timeout_seconds, limits=limits) as client:

        async def worker() -> None:
            nonlocal success, errors, alerts
            while True:
                payload_batch = await queue.get()
                if payload_batch is None:
                    queue.task_done()
                    break

                txn_start_ns = time.perf_counter_ns()
                try:
                    if is_batch_endpoint:
                        request_json = {"items": payload_batch}
                    elif effective_batch_size == 1:
                        request_json: Any = payload_batch[0]
                    else:
                        request_json = payload_batch[0]

                    response = await client.post(url, json=request_json)
                    if response.status_code == 200:
                        data = response.json()
                        if is_batch_endpoint:
                            success += len(payload_batch)
                            if isinstance(data, dict):
                                alerts += int(data.get("alerts_created") or 0)
                        else:
                            success += 1
                            if isinstance(data, dict) and data.get("alert_id"):
                                alerts += 1
                    else:
                        errors += len(payload_batch)
                except Exception:
                    errors += len(payload_batch)
                finally:
                    latency_ms = (time.perf_counter_ns() - txn_start_ns) / 1_000_000.0
                    latencies_ms.append(latency_ms)
                    queue.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(max(1, concurrency))]

        await queue.join()
        for _ in workers:
            queue.put_nowait(None)
        await asyncio.gather(*workers)

    end_ns = time.perf_counter_ns()
    elapsed_seconds = max(0.000001, (end_ns - start_ns) / 1_000_000_000.0)

    throughput_tps = success / elapsed_seconds

    return {
        "status": "PASS" if success == count else "PARTIAL",
        "run_id": run_id,
        "endpoint": url,
        "count": count,
        "concurrency": concurrency,
        "batch_size": effective_batch_size,
        "duration_seconds": round(elapsed_seconds, 3),
        "throughput_tps": round(throughput_tps, 2),
        "success": success,
        "errors": errors,
        "alerts": alerts,
        "latency_ms": {
            "p50": round(_percentile(latencies_ms, 0.50), 2) if latencies_ms else None,
            "p95": round(_percentile(latencies_ms, 0.95), 2) if latencies_ms else None,
            "p99": round(_percentile(latencies_ms, 0.99), 2) if latencies_ms else None,
            "mean": round(statistics.fmean(latencies_ms), 2) if latencies_ms else None,
            "max": round(max(latencies_ms), 2) if latencies_ms else None,
        },
    }


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark backend transaction ingest throughput")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/api/v1/transactions/ingest",
        help="Ingest endpoint URL",
    )
    parser.add_argument("--count", type=int, default=5000)
    parser.add_argument("--concurrency", type=int, default=128)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()

    result = await run_benchmark(
        url=args.url,
        count=max(1, args.count),
        concurrency=max(1, args.concurrency),
        timeout_seconds=max(1.0, args.timeout),
        batch_size=max(1, args.batch_size),
    )
    print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(_main())
