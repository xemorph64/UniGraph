"""
Neo4j service for UniGRAPH.
Uses the async neo4j Python driver.
All queries must be async.
"""

from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional, Any
import structlog
from ..config import settings

logger = structlog.get_logger()


class Neo4jService:
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None

    async def connect(self):
        """Initialize Neo4j async driver."""
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        await self.driver.verify_connectivity()
        logger.info("neo4j_connected", uri=settings.NEO4J_URI)

    async def close(self):
        if self.driver:
            await self.driver.close()

    async def initialize_schema(self):
        """Create constraints and indexes on startup."""
        constraints = [
            "CREATE CONSTRAINT account_id_unique IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT customer_id_unique IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT transaction_id_unique IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT alert_id_unique IF NOT EXISTS FOR (al:Alert) REQUIRE al.id IS UNIQUE",
        ]
        indexes = [
            "CREATE INDEX account_risk IF NOT EXISTS FOR (a:Account) ON (a.risk_score)",
            "CREATE INDEX txn_timestamp IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp)",
            "CREATE INDEX alert_status IF NOT EXISTS FOR (al:Alert) ON (al.status)",
        ]
        async with self.driver.session() as session:
            for stmt in constraints + indexes:
                try:
                    await session.run(stmt)
                except Exception as e:
                    logger.warning("schema_stmt_failed", stmt=stmt[:60], error=str(e))
        logger.info("neo4j_schema_initialized")

    async def upsert_account(
        self,
        account_id: str,
        customer_id: str,
        account_type: str = "SAVINGS",
        kyc_tier: int = 1,
        risk_score: float = 0.0,
        is_dormant: bool = False,
    ) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MERGE (a:Account {id: $id})
                ON CREATE SET
                    a.customer_id = $customer_id,
                    a.account_type = $account_type,
                    a.kyc_tier = $kyc_tier,
                    a.risk_score = $risk_score,
                    a.is_dormant = $is_dormant,
                    a.community_id = 0,
                    a.pagerank = 0.0,
                    a.created_at = datetime()
                ON MATCH SET
                    a.risk_score = $risk_score,
                    a.is_dormant = $is_dormant
                RETURN a
                """,
                id=account_id,
                customer_id=customer_id,
                account_type=account_type,
                kyc_tier=kyc_tier,
                risk_score=risk_score,
                is_dormant=is_dormant,
            )
            record = await result.single()
            return dict(record["a"]) if record else {}

    async def create_transaction_node(self, txn: dict) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MERGE (t:Transaction {id: $txn_id})
                ON CREATE SET
                    t.amount = $amount,
                    t.channel = $channel,
                    t.timestamp = datetime($timestamp),
                    t.from_account = $from_account,
                    t.to_account = $to_account,
                    t.risk_score = $risk_score,
                    t.is_flagged = $is_flagged,
                    t.rule_violations = $rule_violations,
                    t.description = $description,
                    t.device_id = $device_id
                RETURN t
                """,
                txn_id=txn["txn_id"],
                amount=txn["amount"],
                channel=txn.get("channel", "IMPS"),
                timestamp=txn.get("timestamp", "2026-04-10T00:00:00Z"),
                from_account=txn["from_account"],
                to_account=txn["to_account"],
                risk_score=txn.get("risk_score", 0.0),
                is_flagged=txn.get("is_flagged", False),
                rule_violations=txn.get("rule_violations", []),
                description=txn.get("description", ""),
                device_id=txn.get("device_id", "unknown"),
            )
            await session.run(
                """
                MATCH (src:Account {id: $from_account})
                MATCH (dst:Account {id: $to_account})
                MERGE (src)-[r:SENT {txn_id: $txn_id}]->(dst)
                ON CREATE SET
                    r.amount = $amount,
                    r.timestamp = datetime($timestamp),
                    r.channel = $channel
                """,
                from_account=txn["from_account"],
                to_account=txn["to_account"],
                txn_id=txn["txn_id"],
                amount=txn["amount"],
                timestamp=txn.get("timestamp", "2026-04-10T00:00:00Z"),
                channel=txn.get("channel", "IMPS"),
            )
            record = await result.single()
            return dict(record["t"]) if record else {}

    async def get_account_subgraph(self, account_id: str, hops: int = 2) -> dict:
        """Get N-hop subgraph for Cytoscape visualization."""
        async with self.driver.session() as session:
            result = await session.run(
                f"""
                MATCH path = (center:Account {{id: $account_id}})-[:SENT*1..{hops}]-(neighbor)
                UNWIND nodes(path) as n
                WITH collect(DISTINCT n) as nodes_list, path
                UNWIND relationships(path) as r
                WITH nodes_list, collect(DISTINCT r) as rels_list
                RETURN nodes_list, rels_list
                """,
                account_id=account_id,
            )
            nodes = []
            edges = []
            seen_nodes = set()
            seen_edges = set()
            async for record in result:
                for node in record["nodes_list"]:
                    node_id = node.element_id
                    if node_id not in seen_nodes:
                        seen_nodes.add(node_id)
                        props = dict(node)
                        props["labels"] = list(node.labels)
                        nodes.append(props)
                for rel in record["rels_list"]:
                    rel_id = rel.element_id
                    if rel_id not in seen_edges:
                        seen_edges.add(rel_id)
                        edges.append(
                            {
                                "id": rel_id,
                                "type": rel.type,
                                "source": dict(rel.start_node).get("id", ""),
                                "target": dict(rel.end_node).get("id", ""),
                                **dict(rel),
                            }
                        )
            return {"nodes": nodes, "edges": edges}

    async def create_alert(self, alert: dict) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                CREATE (al:Alert {
                    id: $alert_id,
                    transaction_id: $transaction_id,
                    account_id: $account_id,
                    risk_score: $risk_score,
                    risk_level: $risk_level,
                    shap_top3: $shap_top3,
                    rule_flags: $rule_flags,
                    status: 'OPEN',
                    recommendation: $recommendation,
                    created_at: datetime(),
                    assigned_to: null
                })
                RETURN al
                """,
                **alert,
            )
            record = await result.single()
            return dict(record["al"]) if record else {}

    async def get_alerts(
        self,
        status: Optional[str] = None,
        min_risk_score: Optional[int] = None,
        limit: int = 50,
    ) -> list[dict]:
        filters = []
        params: dict[str, Any] = {"limit": limit}
        if status:
            filters.append("al.status = $status")
            params["status"] = status
        if min_risk_score is not None:
            filters.append("al.risk_score >= $min_risk_score")
            params["min_risk_score"] = float(min_risk_score)
        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""
        async with self.driver.session() as session:
            result = await session.run(
                f"""
                MATCH (al:Alert)
                {where_clause}
                RETURN al
                ORDER BY al.created_at DESC
                LIMIT $limit
                """,
                **params,
            )
            alerts = []
            async for record in result:
                a = dict(record["al"])
                for k, v in a.items():
                    if hasattr(v, "isoformat"):
                        a[k] = v.isoformat()
                alerts.append(a)
            return alerts

    async def get_alert_by_id(self, alert_id: str) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (al:Alert {id: $alert_id}) RETURN al", alert_id=alert_id
            )
            record = await result.single()
            if record:
                a = dict(record["al"])
                for k, v in a.items():
                    if hasattr(v, "isoformat"):
                        a[k] = v.isoformat()
                return a
            return None

    async def update_alert_status(
        self, alert_id: str, status: str, assigned_to: Optional[str] = None
    ) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (al:Alert {id: $alert_id})
                SET al.status = $status,
                    al.assigned_to = $assigned_to,
                    al.updated_at = datetime()
                RETURN al
                """,
                alert_id=alert_id,
                status=status,
                assigned_to=assigned_to,
            )
            record = await result.single()
            return dict(record["al"]) if record else {}

    async def get_transaction(self, txn_id: str) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (t:Transaction {id: $txn_id}) RETURN t", txn_id=txn_id
            )
            record = await result.single()
            if record:
                t = dict(record["t"])
                for k, v in t.items():
                    if hasattr(v, "isoformat"):
                        t[k] = v.isoformat()
                return t
            return None

    async def get_graph_stats(self) -> dict:
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (a:Account) WITH count(a) as accounts
                MATCH (t:Transaction) WITH accounts, count(t) as transactions
                MATCH (al:Alert) WITH accounts, transactions, count(al) as alerts
                MATCH (al:Alert {status: 'OPEN'}) WITH accounts, transactions, alerts, count(al) as open_alerts
                RETURN accounts, transactions, alerts, open_alerts
            """)
            record = await result.single()
            if record:
                return dict(record)
            return {"accounts": 0, "transactions": 0, "alerts": 0, "open_alerts": 0}

    async def find_fraud_patterns(self) -> list[dict]:
        """Find rapid layering patterns in the graph."""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH path = (a:Account)-[:SENT*3..6]->(b:Account)
                WHERE a <> b
                WITH path, length(path) as hops,
                     reduce(total=0, r IN relationships(path) | total + r.amount) as total_flow
                WHERE total_flow > 100000
                RETURN
                    [n IN nodes(path) | n.id] as account_chain,
                    hops,
                    total_flow
                ORDER BY total_flow DESC
                LIMIT 10
            """)
            patterns = []
            async for record in result:
                patterns.append(
                    {
                        "account_chain": record["account_chain"],
                        "hops": record["hops"],
                        "total_flow": record["total_flow"],
                    }
                )
            return patterns


neo4j_service = Neo4jService()
