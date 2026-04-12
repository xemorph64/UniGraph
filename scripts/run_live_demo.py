#!/usr/bin/env python3
"""Run a deterministic live UniGRAPH demo chain.

Flow:
1) Ingest one suspicious transaction
2) Confirm alert creation
3) Load investigation graph for alert
4) Generate STR draft
5) Submit STR draft (demo mode)
6) Fetch persisted STR state
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass

import requests


@dataclass
class DemoResult:
    txn_id: str
    alert_id: str
    risk_score: float
    investigate_nodes: int
    investigate_edges: int
    str_id: str
    submit_status: str
    reference_id: str


def _req(method: str, url: str, timeout: float, **kwargs):
    response = requests.request(method, url, timeout=timeout, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed with {response.status_code}: {response.text}")
    return response


def run_demo(base_url: str, timeout: float) -> DemoResult:
    ingest_payload = {
        "txn_id": f"DEMO-TXN-{uuid.uuid4().hex[:10].upper()}",
        "from_account": "DEMO-ACC-PRIMARY",
        "to_account": "DEMO-ACC-MULE-01",
        "amount": 950000,
        "channel": "CASH",
        "customer_id": "DEMO-CUST-01",
        "description": "Live demo structuring scenario",
        "device_id": "DEMO-DEVICE-01",
        "is_dormant": False,
        "device_account_count": 4,
        "velocity_1h": 5,
        "velocity_24h": 12,
    }

    ingest_resp = _req("POST", f"{base_url}/transactions/ingest", timeout, json=ingest_payload).json()
    alert_id = ingest_resp.get("alert_id")
    if not alert_id:
        raise RuntimeError(
            "Ingest completed but no alert was created. Increase suspicious signal values or check scoring thresholds."
        )

    investigation = _req("GET", f"{base_url}/alerts/{alert_id}/investigate?hops=2", timeout).json()
    graph = investigation.get("graph") or {}
    nodes = len(graph.get("nodes") or [])
    edges = len(graph.get("edges") or [])

    gen_resp = _req(
        "POST",
        f"{base_url}/reports/str/generate",
        timeout,
        json={"alert_id": alert_id, "case_notes": "Generated from deterministic live demo"},
    ).json()
    str_id = gen_resp.get("str_id")
    narrative = gen_resp.get("narrative", "")
    if not str_id:
        raise RuntimeError("STR generation did not return str_id")

    submit_resp = _req(
        "POST",
        f"{base_url}/reports/str/{str_id}/submit",
        timeout,
        json={
            "str_id": str_id,
            "edited_narrative": f"{narrative}\n\nSubmitted by run_live_demo.py",
            "digital_signature": "demo-signature",
        },
    ).json()

    _req("GET", f"{base_url}/reports/str/{str_id}", timeout).json()

    return DemoResult(
        txn_id=str(ingest_resp.get("txn_id", "")),
        alert_id=str(alert_id),
        risk_score=float(ingest_resp.get("risk_score", 0.0)),
        investigate_nodes=nodes,
        investigate_edges=edges,
        str_id=str(str_id),
        submit_status=str(submit_resp.get("status", "")),
        reference_id=str(submit_resp.get("reference_id", "")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live UniGRAPH demo chain")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000/api/v1",
        help="Backend API base URL",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout in seconds")
    args = parser.parse_args()

    try:
        result = run_demo(args.base_url.rstrip("/"), args.timeout)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "txn_id": result.txn_id,
                "alert_id": result.alert_id,
                "risk_score": result.risk_score,
                "investigate_nodes": result.investigate_nodes,
                "investigate_edges": result.investigate_edges,
                "str_id": result.str_id,
                "submit_status": result.submit_status,
                "reference_id": result.reference_id,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
