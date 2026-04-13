"""
Load fraud_scenarios.sql data into PostgreSQL and sync to Neo4j.
"""

import sys
import subprocess
from pathlib import Path

FINABLE_CBS = "finacle_cbs"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "postgres"
POSTGRES_HOST = "127.0.0.1"
POSTGRES_PORT = 5433

NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_AUTH = ("neo4j", "unigraph_dev")

SCRIPT_DIR = Path(__file__).parent
FRAUD_SQL = SCRIPT_DIR.parent / "fraud_scenarios.sql"


def load_sql_to_postgres():
    print("Loading fraud_scenarios.sql into PostgreSQL...")

    try:
        import psycopg2
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "psycopg2-binary"], check=True
        )
        import psycopg2

    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=FINABLE_CBS,
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        DROP TABLE IF EXISTS alerts CASCADE;
        DROP TABLE IF EXISTS transactions CASCADE;
        DROP TABLE IF EXISTS accounts CASCADE;
        
        CREATE TABLE accounts (
            account_id VARCHAR(20) PRIMARY KEY,
            customer_name VARCHAR(100),
            account_type VARCHAR(20),
            kyc_tier INTEGER,
            risk_score DECIMAL(5,2),
            is_dormant BOOLEAN DEFAULT FALSE,
            last_active TIMESTAMP,
            account_age_days INTEGER,
            balance DECIMAL(15,2),
            branch_code VARCHAR(10),
            ifsc_code VARCHAR(15),
            pep_flag BOOLEAN DEFAULT FALSE,
            sanction_flag BOOLEAN DEFAULT FALSE
        );
        
        CREATE TABLE transactions (
            txn_id VARCHAR(30) PRIMARY KEY,
            sender_account VARCHAR(20),
            receiver_account VARCHAR(20),
            amount DECIMAL(15,2),
            channel VARCHAR(10),
            txn_timestamp TIMESTAMP,
            device_id VARCHAR(30),
            ip_address VARCHAR(20),
            geo_lat DECIMAL(9,6),
            geo_lon DECIMAL(9,6),
            utr_number VARCHAR(30),
            narration VARCHAR(200),
            status VARCHAR(20) DEFAULT 'SUCCESS',
            is_flagged BOOLEAN DEFAULT FALSE,
            fraud_flag_type VARCHAR(50)
        );
        
        CREATE TABLE alerts (
            alert_id VARCHAR(20) PRIMARY KEY,
            txn_id VARCHAR(30),
            account_id VARCHAR(20),
            fraud_type VARCHAR(50),
            ensemble_score DECIMAL(5,2),
            drools_score DECIMAL(5,2),
            gnn_score DECIMAL(5,2),
            isolation_score DECIMAL(5,2),
            alert_timestamp TIMESTAMP,
            status VARCHAR(20) DEFAULT 'OPEN',
            pmla_citation VARCHAR(100),
            fatf_typology VARCHAR(100)
        );
    """)

    # Read SQL file and execute only INSERT statements (skip comments and SELECTs)
    with open(FRAUD_SQL, "r") as f:
        content = f.read()

    # Split by semicolon and filter to INSERT statements only
    statements = content.split(";")
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
        if stmt.upper().startswith("INSERT INTO"):
            try:
                # Execute the entire multi-row INSERT
                cursor.execute(stmt)
            except Exception as e:
                if "duplicate key" not in str(e).lower():
                    print(f"Warning: {str(e)[:80]}")

    cursor.close()
    conn.close()
    print("PostgreSQL data loaded successfully!")
    return True


async def sync_to_neo4j():
    print("Syncing to Neo4j...")

    try:
        import asyncpg
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "asyncpg"], check=True)
        import asyncpg

    from neo4j import AsyncGraphDatabase

    pg_conn = await asyncpg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=FINABLE_CBS,
    )

    neo4j_driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    async with neo4j_driver.session() as neo4j_sess:
        print("Clearing existing Neo4j data...")
        await neo4j_sess.run("MATCH (n) DETACH DELETE n")

        print("Syncing accounts to Neo4j...")
        accounts = await pg_conn.fetch("SELECT * FROM accounts")
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

        print("Syncing transactions to Neo4j...")
        transactions = await pg_conn.fetch("SELECT * FROM transactions")
        for txn in transactions:
            await neo4j_sess.run(
                """MATCH (src:Account {id: $from_id}), (dst:Account {id: $to_id})
                CREATE (t:Transaction {id: $id, amount: $amount, channel: $channel, timestamp: $ts,
                    from_account: $from_id, to_account: $to_id, device_id: $device, ip_address: $ip,
                    narration: $narration, status: $status, is_flagged: $flagged, fraud_flag_type: $fraud})
                CREATE (src)-[:SENT {txn_id: $id, amount: $amount, timestamp: $ts, channel: $channel}]->(dst)""",
                id=txn["txn_id"],
                from_id=txn["sender_account"],
                to_id=txn["receiver_account"],
                amount=float(txn["amount"] or 0),
                channel=txn["channel"],
                ts=txn["txn_timestamp"].isoformat() if txn["txn_timestamp"] else None,
                device=txn["device_id"],
                ip=txn["ip_address"],
                narration=txn["narration"],
                status=txn["status"],
                flagged=txn["is_flagged"],
                fraud=txn["fraud_flag_type"],
            )

        print("Syncing alerts to Neo4j...")
        alerts = await pg_conn.fetch("SELECT * FROM alerts")

        # Map alert_ids to account_ids based on transaction sender
        alert_account_map = {
            "ALT-2024-0847": "ACC-RT-MUM-001",  # Round-Tripping
            "ALT-2024-0848": "ACC-ST-RECV-001",  # Structuring
            "ALT-2024-0849": "ACC-DA-DORM-001",  # Dormant Awakening
            "ALT-2024-0850": "ACC-LA-001",  # Rapid Layering
            "ALT-2024-0852": "ACC-MU-HUB-001",  # Mule Network
        }

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
            account_id = alert_account_map.get(
                alert["alert_id"], alert["account_id"] or "UNKNOWN"
            )
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

            # Create HAS_ALERT relationship
            await neo4j_sess.run(
                "MATCH (a:Account {id: $acc}), (al:Alert {id: $aid}) CREATE (a)-[:HAS_ALERT]->(al)",
                acc=account_id,
                aid=alert["alert_id"],
            )
            await neo4j_sess.run(
                """CREATE (al:Alert {id: $id, transaction_id: $txn_id, account_id: $acc_id,
                    fraud_type: $fraud, ensemble_score: $ens, drools_score: $drools,
                    gnn_score: $gnn, isolation_score: $iso, alert_timestamp: $ts, status: $st,
                    pmla_citation: $pmla, fatf_typology: $fatf, risk_level: $risk, 
                    risk_score: $ens, created_at: datetime()})""",
                id=alert["alert_id"],
                txn_id=alert["txn_id"],
                acc_id=alert["account_id"],
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

            await neo4j_sess.run(
                "MATCH (a:Account {id: $acc}), (al:Alert {id: $aid}) CREATE (a)-[:HAS_ALERT]->(al)",
                acc=alert["account_id"],
                aid=alert["alert_id"],
            )

        print(
            f"Synced {len(accounts)} accounts, {len(transactions)} transactions, {len(alerts)} alerts"
        )

    await pg_conn.close()
    await neo4j_driver.close()
    print("Neo4j sync complete!")


async def main():
    if not load_sql_to_postgres():
        print("Failed to load SQL to PostgreSQL")
        sys.exit(1)
    await sync_to_neo4j()
    print("\n=== Fraud scenarios loaded with risk_score! ===")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
