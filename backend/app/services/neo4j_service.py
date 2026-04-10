from neo4j import AsyncGraphDatabase
from typing import Optional


class Neo4jService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def get_account(self, account_id: str) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (a:Account {id: $account_id}) RETURN a", account_id=account_id
            )
            record = await result.single()
            if record:
                return dict(record["a"])
            return None

    async def get_subgraph(
        self, account_id: str, hops: int = 2, window_start: str = None
    ) -> dict:
        query = f"""
        MATCH path = (a:Account {{id: $account_id}})-[r:SENT*1..{hops}]-(other)
        """
        if window_start:
            query += f" WHERE r.timestamp > datetime($window_start)"
        query += """
        RETURN nodes(path) as nodes, relationships(path) as relationships
        """
        async with self.driver.session() as session:
            result = await session.run(
                query, account_id=account_id, window_start=window_start
            )
            record = await result.single()
            if record:
                return {
                    "nodes": [dict(n) for n in record["nodes"]],
                    "relationships": [dict(r) for r in record["relationships"]],
                }
            return {"nodes": [], "relationships": []}

    async def get_account_features(self, account_id: str) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Account {id: $account_id})
                RETURN a.pagerank as pagerank,
                       a.betweenness_centrality as betweenness,
                       a.community_id as community_id,
                       a.risk_score as risk_score
            """,
                account_id=account_id,
            )
            record = await result.single()
            if record:
                return dict(record)
            return {}

    async def get_transaction_timeline(
        self, account_id: str, days: int = 30
    ) -> list[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Account {id: $account_id})-[r:SENT|RECEIVED]->(other)
                WHERE r.timestamp > datetime() - duration({days: days})
                RETURN r.txn_id as txn_id, r.amount as amount, r.timestamp as timestamp,
                       r.channel as channel, other.id as counterparty, type(r) as direction
                ORDER BY r.timestamp DESC
                LIMIT 100
            """,
                account_id=account_id,
                days=days,
            )
            return [dict(record) async for record in result]

    async def create_alert(self, alert_data: dict) -> str:
        async with self.driver.session() as session:
            result = await session.run(
                """
                CREATE (al:Alert $alert_data)
                RETURN al.id as alert_id
            """,
                alert_data=alert_data,
            )
            record = await result.single()
            return record["alert_id"]

    async def update_account_risk(self, account_id: str, risk_score: float):
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (a:Account {id: $account_id})
                SET a.risk_score = $risk_score
            """,
                account_id=account_id,
                risk_score=risk_score,
            )

    async def close(self):
        await self.driver.close()
