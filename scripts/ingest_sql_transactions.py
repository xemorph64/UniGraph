#!/usr/bin/env python3
"""Script to ingest transactions from transactions_inserts.sql."""

import re
import httpx
import asyncio
from pathlib import Path

SQL_FILE = Path(__file__).resolve().parents[1] / "transactions_inserts.sql"
API_URL = "http://localhost:8000/api/v1/transactions/ingest"

CHANNEL_MAP = {
    "C3521": "IMPS",
    "C9520": "UPI",
    "C4508": "CASH",
    "C1853": "UPI",
    "C3014": "CASH",
    "C7611": "IMPS",
    "C2311": "SWIFT",
    "C7059": "UPI",
    "C6391": "UPI",
    "C5065": "NEFT",
    "C4244": "UPI",
    "C1517": "NEFT",
    "C1390": "IMPS",
    "C9387": "UPI",
    "C7472": "UPI",
    "C2927": "RTGS",
    "C9892": "SWIFT",
    "C9547": "SWIFT",
    "C7749": "NEFT",
    "C2040": "SWIFT",
    "C9438": "NEFT",
    "C1546": "RTGS",
    "C4899": "IMPS",
    "C8570": "RTGS",
    "C5370": "CASH",
    "C4518": "RTGS",
    "C9550": "RTGS",
    "C6064": "IMPS",
    "C5204": "CASH",
    "C9911": "UPI",
    "C8159": "SWIFT",
    "C6531": "NEFT",
    "C7327": "CASH",
    "C9130": "NEFT",
    "C4012": "NEFT",
    "C1896": "SWIFT",
    "C8688": "CASH",
    "C6257": "CASH",
    "C9967": "NEFT",
    "C8874": "RTGS",
    "C6895": "CASH",
    "C9807": "RTGS",
    "C6382": "CASH",
    "C4090": "UPI",
    "C3435": "SWIFT",
    "C2600": "RTGS",
    "C9219": "IMPS",
    "C5360": "SWIFT",
    "C1849": "UPI",
    "C7113": "RTGS",
    "C7182": "SWIFT",
    "C5339": "SWIFT",
    "C7882": "CASH",
    "C6628": "UPI",
    "C9948": "SWIFT",
    "C9004": "NEFT",
    "C8762": "UPI",
    "C4416": "CASH",
    "C8149": "CASH",
    "C4659": "RTGS",
    "C2240": "UPI",
    "C6685": "RTGS",
    "C7852": "SWIFT",
    "C6943": "SWIFT",
    "C1805": "NEFT",
    "C8067": "IMPS",
    "C9391": "CASH",
    "C8297": "NEFT",
    "C6956": "RTGS",
    "C6967": "NEFT",
    "C4148": "CASH",
    "C9545": "UPI",
    "C3679": "UPI",
    "C2763": "RTGS",
    "C8455": "CASH",
    "C1686": "RTGS",
    "C4120": "NEFT",
    "C5167": "SWIFT",
    "C6305": "RTGS",
    "C6186": "CASH",
    "C5030": "RTGS",
    "C9714": "NEFT",
    "C2586": "NEFT",
    "C4582": "CASH",
    "C9409": "IMPS",
    "C3855": "UPI",
    "C2233": "SWIFT",
    "C3571": "UPI",
    "C5844": "NEFT",
    "C8739": "IMPS",
    "C4242": "CASH",
    "C6849": "NEFT",
    "C6248": "UPI",
    "C3927": "CASH",
    "C5738": "NEFT",
    "C1924": "CASH",
    "C6161": "RTGS",
    "C4105": "RTGS",
    "C1920": "SWIFT",
    "C6327": "SWIFT",
    "C8643": "SWIFT",
    "C8256": "SWIFT",
    "C5483": "CASH",
    "C2538": "SWIFT",
    "C1100": "CASH",
    "C8753": "SWIFT",
    "C6621": "UPI",
    "C1955": "UPI",
    "C3447": "UPI",
    "C2172": "CASH",
    "C7568": "NEFT",
    "C3644": "IMPS",
    "C7143": "SWIFT",
    "C7923": "IMPS",
    "C2696": "SWIFT",
    "C2394": "CASH",
    "C7942": "UPI",
    "C3862": "IMPS",
    "C3802": "RTGS",
    "C9485": "CASH",
    "C7286": "IMPS",
    "C2870": "RTGS",
    "C3832": "RTGS",
    "C3407": "SWIFT",
    "C2662": "IMPS",
    "C1004": "RTGS",
    "C6495": "CASH",
    "C9917": "NEFT",
    "C1323": "RTGS",
    "C8911": "IMPS",
    "C7762": "UPI",
    "C1078": "IMPS",
    "C5156": "IMPS",
    "C3519": "UPI",
    "C4867": "CASH",
    "C9026": "RTGS",
    "C7831": "NEFT",
    "C1033": "SWIFT",
    "C7721": "IMPS",
    "C9055": "SWIFT",
    "C3389": "NEFT",
    "C8522": "CASH",
    "C7573": "CASH",
    "C4950": "UPI",
    "C2657": "NEFT",
    "C5650": "CASH",
    "C8574": "IMPS",
    "C8002": "SWIFT",
    "C2598": "NEFT",
    "C3463": "NEFT",
    "C3869": "UPI",
    "C8258": "IMPS",
    "C7406": "IMPS",
    "C2405": "SWIFT",
    "C1143": "CASH",
    "C4069": "NEFT",
    "C4184": "IMPS",
    "C7750": "IMPS",
    "C7743": "IMPS",
    "C1077": "CASH",
    "C1421": "SWIFT",
    "C5762": "SWIFT",
    "C7777": "SWIFT",
    "C4511": "NEFT",
    "C1478": "NEFT",
    "C8357": "CASH",
    "C3884": "NEFT",
}


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "y", "t"}


def parse_sql_inserts(content: str):
    pattern = r"INSERT INTO transactions VALUES \((.*?)\);"
    matches = re.findall(pattern, content, re.DOTALL)

    txns = []
    for match in matches:
        parts = [p.strip().strip("'").strip('"') for p in match.split(",")]
        if len(parts) >= 24:
            txn_id = parts[0]
            customer_id = parts[5]
            from_acc = parts[3]
            to_acc = parts[4]
            amount = float(parts[6])
            channel = parts[8]
            description = parts[12] or "Payment"

            # SQL dataset carries prior labels/scores that can be used as a risk hint
            # when replaying historical data through the demo scorer.
            risk_score = float(parts[18]) if parts[18] else 0.0
            ml_score = float(parts[19]) if parts[19] else 0.0
            is_flagged = _to_bool(parts[20])
            is_fraud = _to_bool(parts[22])
            hinted_high_risk = is_flagged or is_fraud or risk_score >= 70 or ml_score >= 70

            velocity_1h = 5 if hinted_high_risk else (3 if risk_score >= 50 else 0)
            velocity_24h = 10 if hinted_high_risk else (5 if risk_score >= 50 else 0)
            device_account_count = 4 if hinted_high_risk else 1
            is_dormant = bool(hinted_high_risk and amount >= 200000 and channel in {"RTGS", "SWIFT"})

            mapped_channel = CHANNEL_MAP.get(customer_id, channel)

            txns.append(
                {
                    "txn_id": txn_id,
                    "from_account": from_acc,
                    "to_account": to_acc,
                    "amount": amount,
                    "channel": mapped_channel,
                    "customer_id": customer_id,
                    "description": description,
                    "velocity_1h": velocity_1h,
                    "velocity_24h": velocity_24h,
                    "device_account_count": device_account_count,
                    "is_dormant": is_dormant,
                }
            )

    return txns


async def ingest_transactions(txns: list[dict]):
    async with httpx.AsyncClient(timeout=30.0) as client:
        results = {"success": 0, "flagged": 0, "errors": 0}

        for i, txn in enumerate(txns):
            try:
                resp = await client.post(API_URL, json=txn)
                if resp.status_code == 200:
                    results["success"] += 1
                    data = resp.json()
                    if data.get("is_flagged"):
                        results["flagged"] += 1
                        print(
                            f"  FLAG: {txn['txn_id']} -> risk={data.get('risk_score')}"
                        )
                else:
                    results["errors"] += 1
                    print(f"  ERR: {txn['txn_id']} -> {resp.status_code}")
            except Exception as e:
                results["errors"] += 1
                print(f"  ERR: {txn['txn_id']} -> {e}")

            if (i + 1) % 20 == 0:
                print(f"Progress: {i + 1}/{len(txns)}")

        return results


async def main():
    content = SQL_FILE.read_text()
    txns = parse_sql_inserts(content)
    print(f"Parsed {len(txns)} transactions from SQL file")

    print(f"Ingesting to {API_URL}...")
    results = await ingest_transactions(txns)

    print(f"\n=== Results ===")
    print(f"Success: {results['success']}")
    print(f"Flagged: {results['flagged']}")
    print(f"Errors: {results['errors']}")


if __name__ == "__main__":
    import sys

    if "--allow-legacy" not in sys.argv:
        print(
            "Legacy ingestor disabled in real-data mode. "
            "Use scripts/ingest_fraud_scenarios.py instead, or pass --allow-legacy to override."
        )
        raise SystemExit(1)

    asyncio.run(main())
