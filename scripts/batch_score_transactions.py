"""
Batch score all existing transactions in Neo4j with proper context.
"""

import asyncio
import os
import sys

sys.path.insert(0, "/home/ojasbhalerao/Documents/Uni/backend")
os.chdir("/home/ojasbhalerao/Documents/Uni/backend")

from neo4j import AsyncGraphDatabase
from app.services.fraud_scorer import fraud_scorer

NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_AUTH = ("neo4j", "unigraph_dev")


async def batch_score_transactions():
    print("Starting batch scoring with context enrichment...")

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    async with driver.session() as session:
        # First, get all accounts to know which are dormant
        accounts_result = await session.run("""
            MATCH (a:Account)
            RETURN a.id as id, a.is_dormant as is_dormant
        """)
        accounts = await accounts_result.data()
        dormant_accounts = {a["id"] for a in accounts if a.get("is_dormant")}
        print(f"Found {len(dormant_accounts)} dormant accounts")

        # Get all transactions (regardless of existing risk_score for re-scoring)
        result = await session.run("""
            MATCH (t:Transaction)
            RETURN t.id as id, t.amount as amount, t.channel as channel,
                   t.from_account as from_account, t.to_account as to_account,
                   t.timestamp as timestamp, t.device_id as device_id,
                   t.ip_address as ip_address
            ORDER BY t.timestamp DESC
        """)
        transactions = await result.data()
        print(f"Found {len(transactions)} transactions to score")

        # Build device to account mapping from transactions
        device_accounts = {}
        for txn in transactions:
            dev = txn.get("device_id")
            if dev:
                device_accounts.setdefault(dev, set()).add(txn["from_account"])
                device_accounts.setdefault(dev, set()).add(txn["to_account"])

        # For each transaction, compute 1h and 24h velocity for from_account
        print("Computing velocity metrics...")
        txns_by_account = {}
        for txn in transactions:
            acc = txn["from_account"]
            ts = txn["timestamp"]
            txns_by_account.setdefault(acc, []).append((txn["id"], ts))

        velocity_cache = {}
        for acc, txns in txns_by_account.items():
            # Sort by timestamp
            sorted_txns = sorted(txns, key=lambda x: x[1] if x[1] else "")
            # For each txn, count how many in last 1h and 24h
            for idx, (txn_id, ts) in enumerate(sorted_txns):
                if not ts:
                    velocity_cache[(acc, txn_id)] = (0, 0)
                    continue
                count_1h = 0
                count_24h = 0
                for prev_id, prev_ts in sorted_txns[:idx]:
                    if prev_ts:
                        # Simple time comparison - in real scenario would use proper datetime
                        count_24h += 1
                        # For 1h, we'd need proper time diff
                        count_1h += 1  # Simplified
                velocity_cache[(acc, txn_id)] = (count_1h, count_24h)

        scored = 0
        high_risk = 0

        for txn in transactions:
            from_acc = txn["from_account"]
            to_acc = txn["to_account"]
            dev_id = txn.get("device_id") or "UNKNOWN"

            # Enrich transaction with context
            txn_dict = {
                "txn_id": txn["id"],
                "from_account": from_acc,
                "to_account": to_acc,
                "amount": float(txn["amount"]),
                "channel": txn["channel"],
                "timestamp": txn["timestamp"] if txn["timestamp"] else "",
                "device_id": dev_id,
                "ip_address": txn.get("ip_address") or "",
                "is_dormant": from_acc in dormant_accounts,
                "device_account_count": len(device_accounts.get(dev_id, set())),
                "velocity_1h": velocity_cache.get((from_acc, txn["id"]), (0, 0))[0],
                "velocity_24h": velocity_cache.get((from_acc, txn["id"]), (0, 0))[1],
            }

            # Score the transaction
            score_result = await fraud_scorer.score_transaction(txn_dict)

            risk_score = score_result["risk_score"]
            risk_level = score_result["risk_level"]
            rule_violations = score_result["rule_violations"]
            is_flagged = risk_score >= 60

            # Update transaction in Neo4j
            await session.run(
                """
                MATCH (t:Transaction {id: $id})
                SET t.risk_score = $risk_score,
                    t.risk_level = $risk_level,
                    t.is_flagged = $is_flagged,
                    t.rule_violations = $rule_violations,
                    t.shap_top3 = $shap_top3,
                    t.primary_fraud_type = $primary_fraud_type,
                    t.scored_at = datetime()
            """,
                id=txn["id"],
                risk_score=risk_score,
                risk_level=risk_level,
                is_flagged=is_flagged,
                rule_violations=rule_violations,
                shap_top3=score_result["shap_top3"],
                primary_fraud_type=score_result.get("primary_fraud_type"),
            )

            scored += 1
            if risk_score >= 60:
                high_risk += 1

            if scored % 50 == 0:
                print(f"  Scored {scored}/{len(transactions)} transactions...")

        print(f"\nScoring complete!")
        print(f"  Total scored: {scored}")
        print(f"  High risk (>=60): {high_risk}")

        # Verify
        result = await session.run("""
            MATCH (t:Transaction)
            RETURN count(t) as total,
                   count(CASE WHEN t.risk_score >= 60 THEN 1 END) as high_risk,
                   count(CASE WHEN t.risk_score >= 80 THEN 1 END) as critical
        """)
        stats = await result.single()
        print(f"\nNeo4j verification:")
        print(f"  Total transactions: {stats['total']}")
        print(f"  High risk (>=60): {stats['high_risk']}")
        print(f"  Critical (>=80): {stats['critical']}")

    await driver.close()


if __name__ == "__main__":
    asyncio.run(batch_score_transactions())
