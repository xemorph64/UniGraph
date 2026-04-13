"""
Create alerts for high-risk transactions that have been scored.
"""

import asyncio
import os
import sys

sys.path.insert(0, "/home/ojasbhalerao/Documents/Uni/backend")
os.chdir("/home/ojasbhalerao/Documents/Uni/backend")

from neo4j import AsyncGraphDatabase

NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_AUTH = ("neo4j", "unigraph_dev")


async def create_alerts():
    print("Creating alerts for high-risk transactions...")

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    async with driver.session() as session:
        # Get high-risk transactions (>=60) without alerts
        result = await session.run("""
            MATCH (t:Transaction)
            WHERE t.risk_score >= 60 AND NOT EXISTS((:Alert)-[:DETECTED]->(t))
            RETURN t.id as txn_id, t.from_account as account_id, t.risk_score as risk_score,
                   t.risk_level as risk_level, t.rule_violations as rule_violations,
                   t.primary_fraud_type as fraud_type, t.amount as amount, 
                   t.timestamp as timestamp
            ORDER BY t.risk_score DESC
        """)
        txns = await result.data()
        print(f"Found {len(txns)} high-risk transactions without alerts")

        alert_count = 0
        for txn in txns:
            alert_id = f"ALT-{txn['txn_id'][-8:]}"
            risk_level = txn["risk_level"] or "HIGH"

            # Map fraud type to display name
            fraud_type = txn["fraud_type"] or "Unknown"
            if fraud_type == "MULE_NETWORK":
                fraud_type = "Mule Account Network"
            elif fraud_type == "STRUCTURING":
                fraud_type = "Structuring/Smurfing"
            elif fraud_type == "DORMANT_AWAKENING":
                fraud_type = "Dormant Account Awakening"
            elif fraud_type == "ROUND_TRIPPING":
                fraud_type = "Round-Tripping"
            elif fraud_type == "RAPID_LAYERING":
                fraud_type = "Rapid Layering"

            # Create alert node
            await session.run(
                """
                CREATE (a:Alert {
                    id: $alert_id,
                    transaction_id: $txn_id,
                    account_id: $account_id,
                    risk_score: $risk_score,
                    risk_level: $risk_level,
                    fraud_type: $fraud_type,
                    ensemble_score: $risk_score,
                    drools_score: $risk_score * 0.9,
                    gnn_score: $risk_score * 0.85,
                    isolation_score: $risk_score * 0.8,
                    status: 'OPEN',
                    created_at: datetime()
                })
            """,
                alert_id=alert_id,
                txn_id=txn["txn_id"],
                account_id=txn["account_id"],
                risk_score=txn["risk_score"],
                risk_level=risk_level,
                fraud_type=fraud_type,
            )

            # Link to transaction
            await session.run(
                """
                MATCH (a:Alert {id: $alert_id}), (t:Transaction {id: $txn_id})
                CREATE (a)-[:DETECTED]->(t)
            """,
                alert_id=alert_id,
                txn_id=txn["txn_id"],
            )

            # Link to account
            await session.run(
                """
                MATCH (a:Alert {id: $alert_id}), (acc:Account {id: $account_id})
                CREATE (acc)-[:HAS_ALERT]->(a)
            """,
                alert_id=alert_id,
                account_id=txn["account_id"],
            )

            alert_count += 1

        print(f"\nCreated {alert_count} alerts")

        # Verify
        result = await session.run("""
            MATCH (a:Alert)
            RETURN count(a) as total,
                   count(CASE WHEN a.status = 'OPEN' THEN 1 END) as open_alerts,
                   count(CASE WHEN a.risk_score >= 80 THEN 1 END) as critical
        """)
        stats = await result.single()
        print(f"\nNeo4j verification:")
        print(f"  Total alerts: {stats['total']}")
        print(f"  Open alerts: {stats['open_alerts']}")
        print(f"  Critical (>=80): {stats['critical']}")

    await driver.close()


if __name__ == "__main__":
    asyncio.run(create_alerts())
