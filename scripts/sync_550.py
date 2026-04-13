"""
Sync data from PostgreSQL to Neo4j for the 550 transaction dataset.
"""

import asyncio
import sys

POSTGRES_HOST = "127.0.0.1"
POSTGRES_PORT = 5433
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "postgres"
POSTGRES_DB = "finacle_cbs"

NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_AUTH = ("neo4j", "unigraph_dev")


async def sync_data():
    print("Starting sync to Neo4j...")

    try:
        import asyncpg
    except ImportError:
        import subprocess

        subprocess.run([sys.executable, "-m", "pip", "install", "asyncpg"], check=True)
        import asyncpg

    from neo4j import AsyncGraphDatabase

    pg_conn = await asyncpg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
    )

    neo4j_driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    async with neo4j_driver.session() as neo4j_sess:
        print("Clearing existing Neo4j data...")
        await neo4j_sess.run("MATCH (n) DETACH DELETE n")

        print("Syncing accounts to Neo4j...")
        accounts = await pg_conn.fetch("SELECT * FROM accounts")
        print(f"  Found {len(accounts)} accounts")

        for acc in accounts:
            await neo4j_sess.run(
                """CREATE (a:Account {id: $id, customer_name: $name, account_type: $type,
                    kyc_tier: $tier, risk_score: $risk, is_dormant: $dormant, last_active: $last_active,
                    account_age_days: $age_days, balance: $balance, branch_code: $branch,
                    ifsc_code: $ifsc, pep_flag: $pep, sanction_flag: $sanction, created_at: datetime()})""",
                id=acc["account_id"],
                name=acc["customer_name"],
                type=acc["account_type"],
                tier=acc["kyc_tier"],
                risk=float(acc["risk_score"] or 0),
                dormant=acc["is_dormant"],
                last_active=acc["last_active"].isoformat()
                if acc["last_active"]
                else None,
                age_days=acc["account_age_days"],
                balance=float(acc["balance"] or 0),
                branch=acc["branch_code"],
                ifsc=acc["ifsc_code"],
                pep=acc["pep_flag"],
                sanction=acc["sanction_flag"],
            )
        print(f"  Created {len(accounts)} accounts")

        print("Syncing transactions to Neo4j...")
        transactions = await pg_conn.fetch("SELECT * FROM transactions")
        print(f"  Found {len(transactions)} transactions")

        for txn in transactions:
            await neo4j_sess.run(
                """MATCH (src:Account {id: $from_id}), (dst:Account {id: $to_id})
                CREATE (t:Transaction {id: $id, amount: $amount, channel: $channel, timestamp: $ts,
                    from_account: $from_id, to_account: $to_id, device_id: $device, ip_address: $ip,
                    geo_lat: $lat, geo_lon: $lon, utr_number: $utr, narration: $narr,
                    status: $status, is_flagged: $flagged, created_at: datetime()})
                CREATE (src)-[:SENT {id: $id, amount: $amount, timestamp: $ts}]->(t)
                CREATE (t)-[:RECEIVED {id: $id, amount: $amount, timestamp: $ts}]->(dst)""",
                id=txn["txn_id"],
                from_id=txn["sender_account"],
                to_id=txn["receiver_account"],
                amount=float(txn["amount"] or 0),
                channel=txn["channel"],
                ts=txn["txn_timestamp"].isoformat() if txn["txn_timestamp"] else None,
                device=txn["device_id"],
                ip=txn["ip_address"],
                lat=float(txn["geo_lat"] or 0),
                lon=float(txn["geo_lon"] or 0),
                utr=txn["utr_number"],
                narr=txn["narration"],
                status=txn["status"],
                flagged=txn["is_flagged"],
            )
        print(f"  Created {len(transactions)} transactions")

        print("Syncing alerts to Neo4j...")
        alerts = await pg_conn.fetch("SELECT * FROM alerts")
        print(f"  Found {len(alerts)} alerts")

        for alert in alerts:
            ensemble = float(alert["ensemble_score"] or 0)
            risk_level = (
                "CRITICAL"
                if ensemble >= 90
                else "HIGH"
                if ensemble >= 80
                else "MEDIUM"
                if ensemble >= 50
                else "LOW"
            )
            account_id = alert["account_id"] or "UNKNOWN"
            await neo4j_sess.run(
                """CREATE (al:Alert {id: $id, transaction_id: $txn_id, account_id: $acc_id,
                    fraud_type: $fraud, ensemble_score: $ens, drools_score: $drools,
                    gnn_score: $gnn, isolation_score: $iso, alert_timestamp: $ts, status: $st,
                    pmla_citation: $pmla, fatf_typology: $fatf, risk_level: $risk, 
                    risk_score: $ens, created_at: datetime()})""",
                id=alert["alert_id"],
                txn_id=alert["txn_id"],
                acc_id=account_id,
                fraud=alert["fraud_type"],
                ens=ensemble,
                drools=float(alert["drools_score"] or 0),
                gnn=float(alert["gnn_score"] or 0),
                iso=float(alert["isolation_score"] or 0),
                ts=alert["alert_timestamp"].isoformat()
                if alert["alert_timestamp"]
                else None,
                st=alert["status"],
                pmla=alert["pmla_citation"],
                fatf=alert["fatf_typology"],
                risk=risk_level,
            )

            if account_id != "UNKNOWN":
                await neo4j_sess.run(
                    "MATCH (a:Account {id: $acc}), (al:Alert {id: $aid}) CREATE (a)-[:HAS_ALERT]->(al)",
                    acc=account_id,
                    aid=alert["alert_id"],
                )
        print(f"  Created {len(alerts)} alerts")

        print("\nVerifying data in Neo4j...")
        result = await neo4j_sess.run(
            "MATCH (n) RETURN labels(n)[0] as label, count(*) as count"
        )
        records = await result.data()
        for r in records:
            print(f"  {r['label']}: {r['count']}")

    await pg_conn.close()
    await neo4j_driver.close()
    print("\nSync complete!")


if __name__ == "__main__":
    asyncio.run(sync_data())
