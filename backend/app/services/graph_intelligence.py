"""
Graph Intelligence Module for UniGRAPH.
Extracts graph features and detects fraud patterns.
"""

from typing import Optional
import structlog
from ..services.neo4j_service import neo4j_service

logger = structlog.get_logger()


class GraphIntelligence:
    async def get_account_features(self, account_id: str) -> dict:
        """
        Extract graph features for an account:
        - PageRank
        - Degree (in/out)
        - Community ID (Louvain)
        - Connected account count
        """
        async with neo4j_service.driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Account {id: $account_id})
                OPTIONAL MATCH (a)<-[:SENT]-(t:Transaction)
                OPTIONAL MATCH (a)-[:SENT]->(t2:Transaction)
                OPTIONAL MATCH (a)-[:USED_DEVICE]->(d:Device)
                OPTIONAL MATCH (a)-[:OWNS]->(c:Customer)
                RETURN 
                    a.id as account_id,
                    a.risk_score as risk_score,
                    a.pagerank as pagerank,
                    a.community_id as community_id,
                    a.is_dormant as is_dormant,
                    a.kyc_tier as kyc_tier,
                    count(DISTINCT t) as inbound_txn_count,
                    count(DISTINCT t2) as outbound_txn_count,
                    count(DISTINCT d) as device_count,
                    c.pep_flag as pep_flag,
                    c.sanction_flag as sanction_flag
                LIMIT 1
            """,
                account_id=account_id,
            )

            record = await result.single()
            if record:
                return dict(record)
            return {}

    async def get_velocity_stats(self, account_id: str) -> dict:
        """Calculate velocity (transaction count) in different time windows."""
        async with neo4j_service.driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Account {id: $account_id})-[r:SENT]->()
                WHERE r.timestamp > datetime() - duration('PT1H')
                WITH count(r) as txns_1h
                
                MATCH (a:Account {id: $account_id})-[r:SENT]->()
                WHERE r.timestamp > datetime() - duration('PT24H')
                WITH txns_1h, count(r) as txns_24h
                
                MATCH (a:Account {id: $account_id})-[r:SENT]->()
                WHERE r.timestamp > datetime() - duration('P7D')
                RETURN txns_1h, txns_24h, count(r) as txns_7d
            """,
                account_id=account_id,
            )

            record = await result.single()
            if record:
                return {
                    "velocity_1h": record["txns_1h"],
                    "velocity_24h": record["txns_24h"],
                    "velocity_7d": record["txns_7d"],
                }
            return {"velocity_1h": 0, "velocity_24h": 0, "velocity_7d": 0}

    async def detect_patterns(self, account_id: str) -> list[str]:
        """Detect known fraud patterns for an account."""
        patterns = []

        async with neo4j_service.driver.session() as session:
            # Check for rapid layering (5+ txns in 30 min)
            result = await session.run(
                """
                MATCH (a:Account {id: $account_id})-[r:SENT]->()
                WITH a, collect(r) as txns
                WHERE size(txns) >= 5
                AND duration.between(txns[0].timestamp, txns[-1].timestamp).minutes <= 30
                RETURN 'RAPID_LAYERING' as pattern
            """,
                account_id=account_id,
            )
            if await result.single():
                patterns.append("RAPID_LAYERING")

            # Check for structuring (multiple txns near CTR threshold)
            result = await session.run(
                """
                MATCH (a:Account {id: $account_id})-[r:SENT]->(b)
                WHERE r.amount >= 800000 AND r.amount <= 990000
                WITH count(r) as count
                WHERE count >= 3
                RETURN 'STRUCTURING' as pattern
            """,
                account_id=account_id,
            )
            if await result.single():
                patterns.append("STRUCTURING")

            # Check for dormant account awakening
            result = await session.run(
                """
                MATCH (a:Account {id: $account_id})
                WHERE a.is_dormant = true
                MATCH (a)-[r:SENT]->()
                WHERE r.timestamp > a.dormant_since
                RETURN 'DORMANT_AWAKENING' as pattern
            """,
                account_id=account_id,
            )
            if await result.single():
                patterns.append("DORMANT_AWAKENING")

            # Check for mule network (shared device)
            result = await session.run(
                """
                MATCH (a:Account {id: $account_id})-[:USED_DEVICE]->(d:Device)
                MATCH (d)<-[:USED_DEVICE]-(other:Account)
                WHERE other <> a
                WITH count(DISTINCT other) as shared_count
                WHERE shared_count > 3
                RETURN 'MULE_NETWORK' as pattern
            """,
                account_id=account_id,
            )
            if await result.single():
                patterns.append("MULE_NETWORK")

        return patterns

    async def get_connected_accounts(self, account_id: str, hops: int = 2) -> list[str]:
        """Get all accounts connected within N hops."""
        async with neo4j_service.driver.session() as session:
            result = await session.run(
                f"""
                MATCH (a:Account {{id: $account_id}})-[:SENT*1..{hops}]-(connected:Account)
                RETURN collect(DISTINCT connected.id) as connected_accounts
            """,
                account_id=account_id,
            )
            record = await result.single()
            return record["connected_accounts"] if record else []


graph_intelligence = GraphIntelligence()
