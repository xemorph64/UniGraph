"""
Demo data seeder for UniGRAPH hackathon demo.
Seeds 3 compelling fraud scenarios into Neo4j:
1. Rapid layering (6-hop chain)
2. Dormant account awakening
3. Mule network (shared device)

Run: python scripts/demo_seeder.py
"""

import asyncio
import uuid
from datetime import datetime, timedelta
import random
from neo4j import AsyncGraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "unigraph_dev")


async def seed_demo_data():
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    async with driver.session() as session:
        print("Clearing old demo data...")
        await session.run("MATCH (n) DETACH DELETE n")

        print("Creating normal accounts...")
        for i in range(1, 51):
            acc_id = f"ACC-NORMAL-{i:03d}"
            await session.run(
                """
                CREATE (a:Account {
                    id: $id, customer_id: $cust_id, account_type: 'SAVINGS',
                    kyc_tier: 1, risk_score: $risk, is_dormant: false,
                    community_id: 1, pagerank: 0.1, branch_code: 'MUM001',
                    created_at: datetime()
                })
            """,
                id=acc_id,
                cust_id=f"CUST-{i:03d}",
                risk=random.uniform(0, 15),
            )

        print("SCENARIO 1: Rapid Layering (6-hop chain)...")
        layering_accounts = [f"ACC-LAYER-{i:03d}" for i in range(1, 8)]
        base_time = datetime.utcnow() - timedelta(minutes=30)

        for i, acc_id in enumerate(layering_accounts):
            await session.run(
                """
                CREATE (a:Account {
                    id: $id, customer_id: $cust_id, account_type: 'SAVINGS',
                    kyc_tier: 2, risk_score: $risk, is_dormant: false,
                    community_id: 2, pagerank: 0.3, branch_code: 'DEL001',
                    created_at: datetime()
                })
            """,
                id=acc_id,
                cust_id=f"CUST-LAYER-{i:03d}",
                risk=50 + i * 5,
            )

        amounts = [750000, 748000, 745000, 743000, 740000, 738000]
        for i in range(len(layering_accounts) - 1):
            txn_time = (base_time + timedelta(minutes=i * 5)).isoformat() + "Z"
            txn_id = f"TXN-LAYER-{i + 1:03d}"
            amount = amounts[i]
            await session.run(
                """
                MATCH (src:Account {id: $from_id})
                MATCH (dst:Account {id: $to_id})
                CREATE (t:Transaction {
                    id: $txn_id, amount: $amount, channel: 'IMPS',
                    timestamp: datetime($ts), from_account: $from_id, to_account: $to_id,
                    risk_score: 85.0, is_flagged: true,
                    rule_violations: ['RAPID_LAYERING'],
                    description: 'Payment transfer', device_id: 'DEV-LAYER-001'
                })
                CREATE (src)-[:SENT {txn_id: $txn_id, amount: $amount,
                    timestamp: datetime($ts), channel: 'IMPS'}]->(dst)
            """,
                from_id=layering_accounts[i],
                to_id=layering_accounts[i + 1],
                txn_id=txn_id,
                amount=amount,
                ts=txn_time,
            )

        await session.run(
            """
            CREATE (al:Alert {
                id: $alert_id, transaction_id: 'TXN-LAYER-001',
                account_id: 'ACC-LAYER-001', risk_score: 87.0, risk_level: 'HIGH',
                shap_top3: ['velocity_1h_6_txns: +25', 'high_amount_7.5L: +20',
                             'rapid_succession_pattern: +15'],
                rule_flags: ['RAPID_LAYERING'], status: 'OPEN',
                recommendation: 'HOLD',
                created_at: datetime(), assigned_to: null
            })
        """,
            alert_id=f"ALT-LAYER-{uuid.uuid4().hex[:8].upper()}",
        )

        print("SCENARIO 2: Dormant Account Awakening...")
        dormant_acc = "ACC-DORMANT-001"
        await session.run(
            """
            CREATE (a:Account {
                id: $id, customer_id: 'CUST-DORMANT-001', account_type: 'SAVINGS',
                kyc_tier: 1, risk_score: 90.0, is_dormant: true,
                dormant_since: datetime('2025-09-01T00:00:00Z'),
                community_id: 3, pagerank: 0.05, branch_code: 'MUM002',
                created_at: datetime()
            })
        """,
            id=dormant_acc,
        )

        receiver_acc = "ACC-DORMANT-RECV-001"
        await session.run(
            """
            CREATE (a:Account {
                id: $id, customer_id: 'CUST-RECV-001', account_type: 'CURRENT',
                kyc_tier: 2, risk_score: 40.0, is_dormant: false,
                community_id: 3, pagerank: 0.2, branch_code: 'MUM003',
                created_at: datetime()
            })
        """,
            id=receiver_acc,
        )

        dormant_txn_time = (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z"
        await session.run(
            """
            MATCH (src:Account {id: $from_id})
            MATCH (dst:Account {id: $to_id})
            CREATE (t:Transaction {
                id: 'TXN-DORMANT-001', amount: 1500000, channel: 'NEFT',
                timestamp: datetime($ts), from_account: $from_id, to_account: $to_id,
                risk_score: 91.0, is_flagged: true,
                rule_violations: ['DORMANT_AWAKENING'],
                description: 'Transfer after 212 days dormancy',
                device_id: 'DEV-NEW-001'
            })
            CREATE (src)-[:SENT {txn_id: 'TXN-DORMANT-001', amount: 1500000,
                timestamp: datetime($ts), channel: 'NEFT'}]->(dst)
        """,
            from_id=dormant_acc,
            to_id=receiver_acc,
            ts=dormant_txn_time,
        )

        await session.run(
            """
            CREATE (al:Alert {
                id: $alert_id, transaction_id: 'TXN-DORMANT-001',
                account_id: 'ACC-DORMANT-001', risk_score: 91.0, risk_level: 'CRITICAL',
                shap_top3: ['dormant_account_212_days: +35', 'high_amount_15L: +20',
                             'new_device_first_use: +12'],
                rule_flags: ['DORMANT_AWAKENING'], status: 'OPEN',
                recommendation: 'BLOCK',
                created_at: datetime(), assigned_to: null
            })
        """,
            alert_id=f"ALT-DORM-{uuid.uuid4().hex[:8].upper()}",
        )

        print("SCENARIO 3: Mule Network (shared device)...")
        mule_device = "DEV-MULE-SHARED-001"
        mule_accounts = [f"ACC-MULE-{i:03d}" for i in range(1, 6)]

        for i, acc_id in enumerate(mule_accounts):
            await session.run(
                """
                CREATE (a:Account {
                    id: $id, customer_id: $cust_id, account_type: 'SAVINGS',
                    kyc_tier: 1, risk_score: $risk, is_dormant: false,
                    community_id: 4, pagerank: 0.15, branch_code: 'BLR001',
                    created_at: datetime()
                })
                CREATE (d:Device {id: $device_id, device_type: 'Android',
                    account_count: 5, first_seen: datetime()})
                MERGE (a)-[:USED_DEVICE {last_used: datetime()}]->(d)
            """,
                id=acc_id,
                cust_id=f"CUST-MULE-{i:03d}",
                risk=60 + i * 5,
                device_id=mule_device,
            )

        for i in range(len(mule_accounts) - 1):
            mule_txn_time = (datetime.utcnow() - timedelta(hours=i)).isoformat() + "Z"
            await session.run(
                """
                MATCH (src:Account {id: $from_id})
                MATCH (dst:Account {id: $to_id})
                CREATE (t:Transaction {
                    id: $txn_id, amount: $amount, channel: 'UPI',
                    timestamp: datetime($ts), from_account: $from_id, to_account: $to_id,
                    risk_score: 82.0, is_flagged: true,
                    rule_violations: ['MULE_NETWORK'],
                    description: 'UPI transfer', device_id: $device_id
                })
                CREATE (src)-[:SENT {txn_id: $txn_id, amount: $amount,
                    timestamp: datetime($ts), channel: 'UPI'}]->(dst)
            """,
                from_id=mule_accounts[i],
                to_id=mule_accounts[i + 1],
                txn_id=f"TXN-MULE-{i + 1:03d}",
                amount=50000 * (i + 1),
                ts=mule_txn_time,
                device_id=mule_device,
            )

        await session.run(
            """
            CREATE (al:Alert {
                id: $alert_id, transaction_id: 'TXN-MULE-001',
                account_id: 'ACC-MULE-001', risk_score: 83.0, risk_level: 'HIGH',
                shap_top3: ['device_shared_5_accounts: +30', 'mule_cluster_detected: +25',
                             'transaction_pattern_upi_rapid: +15'],
                rule_flags: ['MULE_NETWORK'], status: 'OPEN',
                recommendation: 'HOLD',
                created_at: datetime(), assigned_to: null
            })
        """,
            alert_id=f"ALT-MULE-{uuid.uuid4().hex[:8].upper()}",
        )

        print("Demo data seeded successfully!")
        print(f"   - 50 normal accounts")
        print(f"   - 7 layering accounts + 6 transactions + 1 alert")
        print(f"   - 1 dormant account + 1 transaction + 1 alert")
        print(f"   - 5 mule accounts + 4 transactions + 1 alert")

    await driver.close()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
