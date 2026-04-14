"""
Neo4j service for UniGRAPH.
Uses the async neo4j Python driver.
All queries must be async.
"""

from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional, Any
import json
import structlog
from ..config import settings

logger = structlog.get_logger()


class Neo4jService:
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None
        self._gds_graph_name = "unigraph-flow-live"

    @staticmethod
    def _serialize_temporals(data: dict) -> dict:
        serialized = {}
        for key, value in data.items():
            normalized = value.isoformat() if hasattr(value, "isoformat") else value

            # Neo4j properties cannot store nested maps directly; metadata is persisted as JSON text.
            if key in {"metadata", "metadata_json"}:
                serialized["metadata"] = Neo4jService._deserialize_metadata(normalized)
                continue

            serialized[key] = normalized
        return serialized

    @staticmethod
    def _serialize_metadata(metadata: Optional[dict]) -> str:
        try:
            return json.dumps(metadata or {}, ensure_ascii=True, separators=(",", ":"))
        except Exception:
            return "{}"

    @staticmethod
    def _deserialize_metadata(metadata: Any) -> Any:
        if isinstance(metadata, str):
            try:
                return json.loads(metadata)
            except Exception:
                return metadata
        return metadata

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
            "CREATE CONSTRAINT case_id_unique IF NOT EXISTS FOR (c:Case) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT str_report_id_unique IF NOT EXISTS FOR (s:STRReport) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT enforcement_action_id_unique IF NOT EXISTS FOR (e:EnforcementAction) REQUIRE e.id IS UNIQUE",
        ]
        indexes = [
            "CREATE INDEX account_risk IF NOT EXISTS FOR (a:Account) ON (a.risk_score)",
            "CREATE INDEX txn_timestamp IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp)",
            "CREATE INDEX alert_status IF NOT EXISTS FOR (al:Alert) ON (al.status)",
            "CREATE INDEX case_status IF NOT EXISTS FOR (c:Case) ON (c.status)",
            "CREATE INDEX str_status IF NOT EXISTS FOR (s:STRReport) ON (s.status)",
            "CREATE INDEX enforcement_status IF NOT EXISTS FOR (e:EnforcementAction) ON (e.status)",
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
                    t.primary_fraud_type = $primary_fraud_type,
                    t.description = $description,
                    t.device_id = $device_id,
                    t.gnn_fraud_probability = $gnn_fraud_probability,
                    t.if_anomaly_score = $if_anomaly_score,
                    t.xgboost_risk_score = $xgboost_risk_score,
                    t.model_version = $model_version,
                    t.scoring_source = $scoring_source,
                    t.scoring_latency_ms = $scoring_latency_ms
                ON MATCH SET
                    t.amount = $amount,
                    t.channel = $channel,
                    t.timestamp = datetime($timestamp),
                    t.from_account = $from_account,
                    t.to_account = $to_account,
                    t.risk_score = $risk_score,
                    t.is_flagged = $is_flagged,
                    t.rule_violations = $rule_violations,
                    t.primary_fraud_type = $primary_fraud_type,
                    t.description = $description,
                    t.device_id = $device_id,
                    t.gnn_fraud_probability = $gnn_fraud_probability,
                    t.if_anomaly_score = $if_anomaly_score,
                    t.xgboost_risk_score = $xgboost_risk_score,
                    t.model_version = $model_version,
                    t.scoring_source = $scoring_source,
                    t.scoring_latency_ms = $scoring_latency_ms
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
                primary_fraud_type=txn.get("primary_fraud_type"),
                description=txn.get("description", ""),
                device_id=txn.get("device_id", "unknown"),
                gnn_fraud_probability=txn.get("gnn_fraud_probability"),
                if_anomaly_score=txn.get("if_anomaly_score"),
                xgboost_risk_score=txn.get("xgboost_risk_score"),
                model_version=txn.get("model_version"),
                scoring_source=txn.get("scoring_source"),
                scoring_latency_ms=txn.get("scoring_latency_ms"),
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

    async def get_scoring_graph_features(self, account_id: str) -> dict:
        """Return graph-derived scoring features for an account.

        These values are lightweight and safe to compute inline during scoring.
        """
        defaults = {
            "connected_suspicious_nodes": 0,
            "community_risk_score": 0.0,
            "neighbor_avg_risk": 0.0,
            "community_id": 0,
            "pagerank": 0.0,
            "betweenness_centrality": 0.0,
            "in_degree_24h": 0,
            "out_degree_24h": 0,
            "shortest_path_to_fraud": 0.0,
            "neighbor_fraud_ratio": 0.0,
        }

        if not account_id:
            return defaults

        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Account {id: $account_id})
                                OPTIONAL MATCH (a)-[o:SENT]->(:Account)
                WHERE datetime(toString(o.timestamp)) >= datetime() - duration({hours: 24})
                                WITH a, count(o) AS out_degree_24h
                                OPTIONAL MATCH (:Account)-[i:SENT]->(a)
                WHERE datetime(toString(i.timestamp)) >= datetime() - duration({hours: 24})
                                WITH a, out_degree_24h, count(i) AS in_degree_24h
                OPTIONAL MATCH (a)-[:SENT*1..2]-(n:Account)
                                WITH a, in_degree_24h, out_degree_24h, collect(DISTINCT n) AS neighbors
                WITH
                  a,
                                    in_degree_24h,
                                    out_degree_24h,
                  neighbors,
                  size([n IN neighbors WHERE coalesce(n.risk_score, 0.0) >= 60.0]) AS connected_suspicious_nodes,
                                    CASE size(neighbors)
                                        WHEN 0 THEN 0.0
                                        ELSE toFloat(size([n IN neighbors WHERE coalesce(n.risk_score, 0.0) >= 60.0])) / toFloat(size(neighbors))
                                    END AS neighbor_fraud_ratio,
                  CASE size(neighbors)
                    WHEN 0 THEN 0.0
                    ELSE reduce(total = 0.0, n IN neighbors | total + coalesce(n.risk_score, 0.0)) / toFloat(size(neighbors))
                  END AS neighbor_avg_risk
                                OPTIONAL MATCH p = (a)-[:SENT*1..6]-(f:Account)
                                WHERE f.id <> a.id AND coalesce(f.risk_score, 0.0) >= 60.0
                                WITH a,
                                         in_degree_24h,
                                         out_degree_24h,
                                         connected_suspicious_nodes,
                                         neighbor_fraud_ratio,
                                         neighbor_avg_risk,
                                         min(length(p)) AS min_path_len
                RETURN
                  connected_suspicious_nodes,
                  coalesce(a.community_id, 0) AS community_id,
                  coalesce(a.pagerank, 0.0) AS pagerank,
                  coalesce(a.betweenness_centrality, 0.0) AS betweenness_centrality,
                                    neighbor_avg_risk,
                                    in_degree_24h,
                                    out_degree_24h,
                                    coalesce(toFloat(min_path_len), 0.0) AS shortest_path_to_fraud,
                                    neighbor_fraud_ratio
                """,
                account_id=account_id,
            )
            record = await result.single()
            if not record:
                return defaults

            return {
                "connected_suspicious_nodes": int(
                    record["connected_suspicious_nodes"] or 0
                ),
                "community_risk_score": float(record["neighbor_avg_risk"] or 0.0),
                "neighbor_avg_risk": float(record["neighbor_avg_risk"] or 0.0),
                "community_id": int(record["community_id"] or 0),
                "pagerank": float(record["pagerank"] or 0.0),
                "betweenness_centrality": float(
                    record["betweenness_centrality"] or 0.0
                ),
                "in_degree_24h": int(record["in_degree_24h"] or 0),
                "out_degree_24h": int(record["out_degree_24h"] or 0),
                "shortest_path_to_fraud": float(
                    record["shortest_path_to_fraud"] or 0.0
                ),
                "neighbor_fraud_ratio": float(record["neighbor_fraud_ratio"] or 0.0),
            }

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
                    primary_fraud_type: $primary_fraud_type,
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
        transaction_id_prefix: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> dict:
        filters = []
        params: dict[str, Any] = {"limit": limit, "skip": skip}
        if status:
            filters.append("al.status = $status")
            params["status"] = status
        if min_risk_score is not None:
            filters.append("al.risk_score >= $min_risk_score")
            params["min_risk_score"] = float(min_risk_score)
        if transaction_id_prefix:
            filters.append("coalesce(al.transaction_id, '') STARTS WITH $transaction_id_prefix")
            params["transaction_id_prefix"] = transaction_id_prefix
        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""
        async with self.driver.session() as session:
            total_result = await session.run(
                f"""
                MATCH (al:Alert)
                {where_clause}
                RETURN count(al) as total
                """,
                **params,
            )
            total_record = await total_result.single()
            total = int(total_record["total"]) if total_record else 0

            result = await session.run(
                f"""
                MATCH (al:Alert)
                {where_clause}
                RETURN al
                ORDER BY al.created_at DESC
                SKIP $skip
                LIMIT $limit
                """,
                **params,
            )
            alerts = []
            async for record in result:
                alerts.append(self._serialize_temporals(dict(record["al"])))
            return {"items": alerts, "total": total}

    async def purge_transactions_by_prefix(self, txn_id_prefix: str) -> dict:
        """Delete replay artifacts for a transaction-id prefix.

        Removes transaction-scoped alert and transfer edges before deleting
        transactions so reruns for the same dataset prefix stay clean.
        """
        prefix = (txn_id_prefix or "").strip()
        if not prefix:
            return {
                "txn_id_prefix": prefix,
                "alerts_deleted": 0,
                "transactions_deleted": 0,
                "sent_relationships_deleted": 0,
            }

        async with self.driver.session() as session:
            rel_result = await session.run(
                """
                MATCH ()-[r:SENT]->()
                WHERE coalesce(r.txn_id, '') STARTS WITH $prefix
                WITH collect(r) AS rels
                FOREACH (rel IN rels | DELETE rel)
                RETURN size(rels) AS deleted_count
                """,
                prefix=prefix,
            )
            rel_record = await rel_result.single()
            sent_relationships_deleted = (
                int(rel_record["deleted_count"]) if rel_record else 0
            )

            alert_result = await session.run(
                """
                MATCH (al:Alert)
                WHERE coalesce(al.transaction_id, '') STARTS WITH $prefix
                WITH collect(al) AS alerts
                FOREACH (a IN alerts | DETACH DELETE a)
                RETURN size(alerts) AS deleted_count
                """,
                prefix=prefix,
            )
            alert_record = await alert_result.single()
            alerts_deleted = int(alert_record["deleted_count"]) if alert_record else 0

            txn_result = await session.run(
                """
                MATCH (t:Transaction)
                WHERE t.id STARTS WITH $prefix
                WITH collect(t) AS txns
                FOREACH (txn IN txns | DETACH DELETE txn)
                RETURN size(txns) AS deleted_count
                """,
                prefix=prefix,
            )
            txn_record = await txn_result.single()
            transactions_deleted = int(txn_record["deleted_count"]) if txn_record else 0

        return {
            "txn_id_prefix": prefix,
            "alerts_deleted": alerts_deleted,
            "transactions_deleted": transactions_deleted,
            "sent_relationships_deleted": sent_relationships_deleted,
        }

    async def get_alert_by_id(self, alert_id: str) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (al:Alert {id: $alert_id}) RETURN al", alert_id=alert_id
            )
            record = await result.single()
            if record:
                return self._serialize_temporals(dict(record["al"]))
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
                return self._serialize_temporals(dict(record["t"]))
            return None

    async def get_transactions(
        self,
        page: int = 1,
        page_size: int = 50,
        account_id: Optional[str] = None,
        channel: Optional[str] = None,
        min_risk_score: Optional[float] = None,
        txn_id_prefix: Optional[str] = None,
    ) -> dict:
        filters = []
        params: dict[str, Any] = {
            "limit": page_size,
            "skip": (page - 1) * page_size,
        }
        if account_id:
            filters.append(
                "(t.from_account = $account_id OR t.to_account = $account_id)"
            )
            params["account_id"] = account_id
        if channel:
            filters.append("t.channel = $channel")
            params["channel"] = channel
        if min_risk_score is not None:
            filters.append("coalesce(t.risk_score, 0) >= $min_risk_score")
            params["min_risk_score"] = float(min_risk_score)
        if txn_id_prefix:
            filters.append("t.id STARTS WITH $txn_id_prefix")
            params["txn_id_prefix"] = txn_id_prefix

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        async with self.driver.session() as session:
            total_result = await session.run(
                f"""
                MATCH (t:Transaction)
                {where_clause}
                RETURN count(t) as total
                """,
                **params,
            )
            total_record = await total_result.single()
            total = int(total_record["total"]) if total_record else 0

            result = await session.run(
                f"""
                MATCH (t:Transaction)
                {where_clause}
                RETURN t
                ORDER BY t.timestamp DESC
                SKIP $skip
                LIMIT $limit
                """,
                **params,
            )

            items: list[dict] = []
            async for record in result:
                items.append(self._serialize_temporals(dict(record["t"])))

        return {"items": items, "total": total}

    async def create_case(
        self,
        case_id: str,
        alert_id: str,
        title: str,
        description: str,
        priority: str,
        assigned_to: str,
    ) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (al:Alert {id: $alert_id})
                CREATE (c:Case {
                    id: $case_id,
                    alert_id: $alert_id,
                    title: $title,
                    description: $description,
                    priority: $priority,
                    status: 'OPEN',
                    assigned_to: $assigned_to,
                    created_at: datetime(),
                    closed_at: null,
                    labels: []
                })
                MERGE (al)-[:CREATED_CASE]->(c)
                RETURN c
                """,
                case_id=case_id,
                alert_id=alert_id,
                title=title,
                description=description,
                priority=priority,
                assigned_to=assigned_to,
            )
            record = await result.single()
            return self._serialize_temporals(dict(record["c"])) if record else None

    async def get_case(self, case_id: str) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (c:Case {id: $case_id}) RETURN c", case_id=case_id
            )
            record = await result.single()
            return self._serialize_temporals(dict(record["c"])) if record else None

    async def close_case(
        self,
        case_id: str,
        outcome: str,
        notes: str,
        closed_by: str,
    ) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Case {id: $case_id})
                SET c.status = 'CLOSED',
                    c.closed_at = datetime(),
                    c.close_outcome = $outcome,
                    c.close_notes = $notes,
                    c.closed_by = $closed_by,
                    c.labels = CASE
                        WHEN c.labels IS NULL THEN [$outcome]
                        ELSE c.labels + [$outcome]
                    END
                RETURN c
                """,
                case_id=case_id,
                outcome=outcome,
                notes=notes,
                closed_by=closed_by,
            )
            record = await result.single()
            return self._serialize_temporals(dict(record["c"])) if record else None

    async def list_cases(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> dict:
        filters = []
        params: dict[str, Any] = {
            "limit": page_size,
            "skip": (page - 1) * page_size,
        }
        if status:
            filters.append("c.status = $status")
            params["status"] = status
        if assigned_to:
            filters.append("c.assigned_to = $assigned_to")
            params["assigned_to"] = assigned_to

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        async with self.driver.session() as session:
            total_result = await session.run(
                f"""
                MATCH (c:Case)
                {where_clause}
                RETURN count(c) as total
                """,
                **params,
            )
            total_record = await total_result.single()
            total = int(total_record["total"]) if total_record else 0

            result = await session.run(
                f"""
                MATCH (c:Case)
                {where_clause}
                RETURN c
                ORDER BY c.created_at DESC
                SKIP $skip
                LIMIT $limit
                """,
                **params,
            )
            items = []
            async for record in result:
                items.append(self._serialize_temporals(dict(record["c"])))

        return {"items": items, "total": total}

    async def create_str_report(
        self,
        str_id: str,
        alert_id: str,
        account_id: str,
        risk_score: float,
        narrative: str,
        generated_by: str = "LLM",
    ) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (al:Alert {id: $alert_id})
                MERGE (s:STRReport {id: $str_id})
                ON CREATE SET
                    s.alert_id = $alert_id,
                    s.account_id = $account_id,
                    s.risk_score = $risk_score,
                    s.narrative = $narrative,
                    s.generated_by = $generated_by,
                    s.status = 'DRAFT',
                    s.created_at = datetime(),
                    s.submitted_at = null,
                    s.reference_id = null
                ON MATCH SET
                    s.alert_id = $alert_id,
                    s.account_id = $account_id,
                    s.risk_score = $risk_score,
                    s.narrative = $narrative,
                    s.generated_by = $generated_by,
                    s.updated_at = datetime()
                MERGE (al)-[:HAS_STR]->(s)
                RETURN s
                """,
                str_id=str_id,
                alert_id=alert_id,
                account_id=account_id,
                risk_score=risk_score,
                narrative=narrative,
                generated_by=generated_by,
            )
            record = await result.single()
            return self._serialize_temporals(dict(record["s"])) if record else {}

    async def get_str_report(self, str_id: str) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (s:STRReport {id: $str_id}) RETURN s", str_id=str_id
            )
            record = await result.single()
            return self._serialize_temporals(dict(record["s"])) if record else None

    async def submit_str_report(
        self,
        str_id: str,
        edited_narrative: str,
        digital_signature: str,
        reference_id: str,
        status: str,
    ) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (s:STRReport {id: $str_id})
                SET s.narrative = $edited_narrative,
                    s.digital_signature = $digital_signature,
                    s.reference_id = $reference_id,
                    s.status = $status,
                    s.submitted_at = datetime(),
                    s.updated_at = datetime()
                RETURN s
                """,
                str_id=str_id,
                edited_narrative=edited_narrative,
                digital_signature=digital_signature,
                reference_id=reference_id,
                status=status,
            )
            record = await result.single()
            return self._serialize_temporals(dict(record["s"])) if record else None

    async def list_str_reports(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> dict:
        filters = []
        params: dict[str, Any] = {
            "limit": page_size,
            "skip": (page - 1) * page_size,
        }
        if status:
            filters.append("s.status = $status")
            params["status"] = status
        if account_id:
            filters.append("s.account_id = $account_id")
            params["account_id"] = account_id

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        async with self.driver.session() as session:
            total_result = await session.run(
                f"""
                MATCH (s:STRReport)
                {where_clause}
                RETURN count(s) as total
                """,
                **params,
            )
            total_record = await total_result.single()
            total = int(total_record["total"]) if total_record else 0

            result = await session.run(
                f"""
                MATCH (s:STRReport)
                {where_clause}
                RETURN s
                ORDER BY s.created_at DESC
                SKIP $skip
                LIMIT $limit
                """,
                **params,
            )
            items: list[dict] = []
            async for record in result:
                items.append(self._serialize_temporals(dict(record["s"])))

        return {"items": items, "total": total}

    async def update_str_review(
        self,
        str_id: str,
        status: str,
        reviewed_by: str,
        review_notes: str = "",
    ) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (s:STRReport {id: $str_id})
                SET s.status = $status,
                    s.reviewed_by = $reviewed_by,
                    s.review_notes = $review_notes,
                    s.reviewed_at = datetime(),
                    s.updated_at = datetime()
                RETURN s
                """,
                str_id=str_id,
                status=status,
                reviewed_by=reviewed_by,
                review_notes=review_notes,
            )
            record = await result.single()
            return self._serialize_temporals(dict(record["s"])) if record else None

    async def create_enforcement_action(
        self,
        action_id: str,
        action_type: str,
        account_id: str,
        reason: str,
        initiated_by: str,
        status: str,
        reference_id: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MERGE (e:EnforcementAction {id: $action_id})
                ON CREATE SET
                    e.action_type = $action_type,
                    e.account_id = $account_id,
                    e.reason = $reason,
                    e.initiated_by = $initiated_by,
                    e.status = $status,
                    e.reference_id = $reference_id,
                    e.metadata_json = $metadata_json,
                    e.created_at = datetime(),
                    e.updated_at = datetime()
                ON MATCH SET
                    e.action_type = $action_type,
                    e.account_id = $account_id,
                    e.reason = $reason,
                    e.initiated_by = $initiated_by,
                    e.status = $status,
                    e.reference_id = $reference_id,
                    e.metadata_json = $metadata_json,
                    e.updated_at = datetime()
                WITH e
                OPTIONAL MATCH (a:Account {id: $account_id})
                FOREACH (_ IN CASE WHEN a IS NULL THEN [] ELSE [1] END |
                    MERGE (a)-[:HAS_ENFORCEMENT_ACTION]->(e)
                )
                RETURN e
                """,
                action_id=action_id,
                action_type=action_type,
                account_id=account_id,
                reason=reason,
                initiated_by=initiated_by,
                status=status,
                reference_id=reference_id,
                metadata_json=self._serialize_metadata(metadata),
            )
            record = await result.single()
            return self._serialize_temporals(dict(record["e"])) if record else {}

    async def get_enforcement_action(self, action_id: str) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (e:EnforcementAction {id: $action_id}) RETURN e",
                action_id=action_id,
            )
            record = await result.single()
            return self._serialize_temporals(dict(record["e"])) if record else None

    async def list_enforcement_actions(
        self,
        page: int = 1,
        page_size: int = 50,
        action_type: Optional[str] = None,
        status: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> dict:
        filters = []
        params: dict[str, Any] = {
            "limit": page_size,
            "skip": (page - 1) * page_size,
        }
        if action_type:
            filters.append("e.action_type = $action_type")
            params["action_type"] = action_type
        if status:
            filters.append("e.status = $status")
            params["status"] = status
        if account_id:
            filters.append("e.account_id = $account_id")
            params["account_id"] = account_id

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        async with self.driver.session() as session:
            total_result = await session.run(
                f"""
                MATCH (e:EnforcementAction)
                {where_clause}
                RETURN count(e) as total
                """,
                **params,
            )
            total_record = await total_result.single()
            total = int(total_record["total"]) if total_record else 0

            result = await session.run(
                f"""
                MATCH (e:EnforcementAction)
                {where_clause}
                RETURN e
                ORDER BY e.created_at DESC
                SKIP $skip
                LIMIT $limit
                """,
                **params,
            )
            items: list[dict] = []
            async for record in result:
                items.append(self._serialize_temporals(dict(record["e"])))

        return {"items": items, "total": total}

    async def update_enforcement_action_status(
        self,
        action_id: str,
        status: str,
        reviewed_by: str,
        review_notes: str = "",
        metadata: Optional[dict] = None,
    ) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:EnforcementAction {id: $action_id})
                SET e.status = $status,
                    e.reviewed_by = $reviewed_by,
                    e.review_notes = $review_notes,
                    e.reviewed_at = datetime(),
                    e.updated_at = datetime(),
                    e.metadata_json = $metadata_json
                RETURN e
                """,
                action_id=action_id,
                status=status,
                reviewed_by=reviewed_by,
                review_notes=review_notes,
                metadata_json=self._serialize_metadata(metadata),
            )
            record = await result.single()
            return self._serialize_temporals(dict(record["e"])) if record else None

    async def create_audit_event(
        self,
        event_type: str,
        actor_id: str,
        actor_role: str,
        action: str,
        status: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                CREATE (ae:AuditEvent {
                    id: randomUUID(),
                    event_type: $event_type,
                    actor_id: $actor_id,
                    actor_role: $actor_role,
                    action: $action,
                    status: $status,
                    metadata_json: $metadata_json,
                    created_at: datetime()
                })
                RETURN ae
                """,
                event_type=event_type,
                actor_id=actor_id,
                actor_role=actor_role,
                action=action,
                status=status,
                metadata_json=self._serialize_metadata(metadata),
            )
            record = await result.single()
            return self._serialize_temporals(dict(record["ae"])) if record else {}

    async def get_account_timeline_from_graph(
        self, account_id: str, days: int = 30
    ) -> list[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (t:Transaction)
                WHERE (t.from_account = $account_id OR t.to_account = $account_id)
                                    AND t.timestamp >= datetime() - duration({days: $days})
                WITH date(t.timestamp) as day,
                     count(t) as txn_count,
                     avg(coalesce(t.risk_score, 0.0)) as avg_risk,
                     max(coalesce(t.risk_score, 0.0)) as max_risk,
                     sum(CASE WHEN coalesce(t.is_flagged, false) THEN 1 ELSE 0 END) as flagged_txn_count
                RETURN toString(day) as day,
                       txn_count,
                       avg_risk,
                       max_risk,
                       flagged_txn_count
                ORDER BY day ASC
                """,
                account_id=account_id,
                days=days,
            )

            timeline: list[dict] = []
            async for record in result:
                timeline.append(
                    {
                        "day": record["day"],
                        "risk_score": round(float(record["avg_risk"] or 0.0), 2),
                        "max_risk_score": round(float(record["max_risk"] or 0.0), 2),
                        "txn_count": int(record["txn_count"] or 0),
                        "flagged_txn_count": int(record["flagged_txn_count"] or 0),
                    }
                )
            return timeline

    async def get_graph_stats(self) -> dict:
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (a:Account)
                OPTIONAL MATCH (a)-[r:SENT]->()
                OPTIONAL MATCH (a)-[:HAS_ALERT]->(al:Alert)
                RETURN 
                    count(DISTINCT a) as total_accounts,
                    count(DISTINCT r) as total_transactions,
                    count(DISTINCT al) as total_alerts
            """)
            record = await result.single()
            if record:
                return {
                    "accounts": int(record.get("total_accounts", 0) or 0),
                    "transactions": int(record.get("total_transactions", 0) or 0),
                    "alerts": int(record.get("total_alerts", 0) or 0),
                    "open_alerts": int(record.get("total_alerts", 0) or 0),
                }
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

    async def run_gds_analytics(self) -> dict:
        """Run PageRank, Louvain, and Betweenness over live Account->SENT->Account graph."""
        async with self.driver.session() as session:
            exists_result = await session.run(
                "CALL gds.graph.exists($graph_name) YIELD exists RETURN exists",
                graph_name=self._gds_graph_name,
            )
            exists_record = await exists_result.single()
            if exists_record and bool(exists_record.get("exists", False)):
                await session.run(
                    "CALL gds.graph.drop($graph_name, false) YIELD graphName RETURN graphName",
                    graph_name=self._gds_graph_name,
                )

            project_result = await session.run(
                """
                CALL gds.graph.project(
                  $graph_name,
                  'Account',
                  {
                    SENT: {
                      orientation: 'NATURAL',
                      properties: 'amount'
                    }
                  }
                )
                YIELD graphName, nodeCount, relationshipCount
                RETURN graphName, nodeCount, relationshipCount
                """,
                graph_name=self._gds_graph_name,
            )
            project = await project_result.single()

            pagerank_result = await session.run(
                """
                CALL gds.pageRank.write($graph_name, {
                  maxIterations: 20,
                  dampingFactor: 0.85,
                  writeProperty: 'pagerank'
                })
                YIELD nodePropertiesWritten, ranIterations
                RETURN nodePropertiesWritten, ranIterations
                """,
                graph_name=self._gds_graph_name,
            )
            pagerank = await pagerank_result.single()

            louvain_result = await session.run(
                """
                CALL gds.louvain.write($graph_name, {
                  writeProperty: 'community_id'
                })
                YIELD communityCount, modularity
                RETURN communityCount, modularity
                """,
                graph_name=self._gds_graph_name,
            )
            louvain = await louvain_result.single()

            betweenness_result = await session.run(
                """
                CALL gds.betweenness.write($graph_name, {
                  writeProperty: 'betweenness_centrality'
                })
                YIELD nodePropertiesWritten
                RETURN nodePropertiesWritten
                """,
                graph_name=self._gds_graph_name,
            )
            betweenness = await betweenness_result.single()

            await session.run(
                """
                MATCH (a:Account)
                WITH a.community_id AS cid, avg(coalesce(a.risk_score, 0.0)) AS avg_risk
                MATCH (n:Account {community_id: cid})
                SET n.community_risk_score = avg_risk
                """
            )

            await session.run(
                "CALL gds.graph.drop($graph_name, false) YIELD graphName RETURN graphName",
                graph_name=self._gds_graph_name,
            )

            return {
                "graph": {
                    "name": project["graphName"] if project else self._gds_graph_name,
                    "node_count": int(project["nodeCount"] if project else 0),
                    "relationship_count": int(
                        project["relationshipCount"] if project else 0
                    ),
                },
                "pagerank": {
                    "node_properties_written": int(
                        pagerank["nodePropertiesWritten"] if pagerank else 0
                    ),
                    "iterations": int(pagerank["ranIterations"] if pagerank else 0),
                },
                "louvain": {
                    "community_count": int(louvain["communityCount"] if louvain else 0),
                    "modularity": float(louvain["modularity"] if louvain else 0.0),
                },
                "betweenness": {
                    "node_properties_written": int(
                        betweenness["nodePropertiesWritten"] if betweenness else 0
                    )
                },
            }

    async def get_gds_status(self) -> dict:
        """Return current graph analytics property coverage and top ranked accounts."""
        async with self.driver.session() as session:
            coverage_result = await session.run(
                """
                MATCH (a:Account)
                RETURN
                  count(a) AS total_accounts,
                  sum(CASE WHEN coalesce(a.pagerank, 0.0) > 0 THEN 1 ELSE 0 END) AS with_pagerank,
                  sum(CASE WHEN coalesce(a.community_id, 0) <> 0 THEN 1 ELSE 0 END) AS with_community,
                  sum(CASE WHEN coalesce(a.betweenness_centrality, 0.0) > 0 THEN 1 ELSE 0 END) AS with_betweenness,
                  max(coalesce(a.pagerank, 0.0)) AS max_pagerank,
                  count(DISTINCT a.community_id) AS distinct_communities
                """
            )
            coverage = await coverage_result.single()

            top_result = await session.run(
                """
                MATCH (a:Account)
                WHERE coalesce(a.pagerank, 0.0) > 0
                RETURN a.id AS account_id,
                       a.pagerank AS pagerank,
                       coalesce(a.community_id, 0) AS community_id,
                       coalesce(a.betweenness_centrality, 0.0) AS betweenness_centrality,
                       coalesce(a.risk_score, 0.0) AS risk_score
                ORDER BY pagerank DESC
                LIMIT 10
                """
            )
            top_accounts: list[dict] = []
            async for record in top_result:
                top_accounts.append(
                    {
                        "account_id": record["account_id"],
                        "pagerank": float(record["pagerank"]),
                        "community_id": int(record["community_id"]),
                        "betweenness_centrality": float(
                            record["betweenness_centrality"]
                        ),
                        "risk_score": float(record["risk_score"]),
                    }
                )

            return {
                "total_accounts": int(coverage["total_accounts"] if coverage else 0),
                "with_pagerank": int(coverage["with_pagerank"] if coverage else 0),
                "with_community": int(coverage["with_community"] if coverage else 0),
                "with_betweenness": int(
                    coverage["with_betweenness"] if coverage else 0
                ),
                "max_pagerank": float(coverage["max_pagerank"] if coverage else 0.0),
                "distinct_communities": int(
                    coverage["distinct_communities"] if coverage else 0
                ),
                "top_accounts": top_accounts,
            }

    async def get_pattern_overview(self) -> dict:
        """Return calibrated pattern counts and sample entities for investigator workflows."""
        async with self.driver.session() as session:
            rapid_window_hours = 24
            rapid_min_txn_count = 3
            rapid_min_total_amount = 50000.0

            structuring_window_days = 7
            structuring_min_repeats = 2
            structuring_lower_factor = 0.9
            structuring_upper_factor = 1.03

            dormant_window_days = 30
            dormant_prior_days = 30
            dormant_min_amount = 50000.0

            mule_window_hours = 24
            mule_min_senders = 2
            mule_min_receivers = 2

            sample_limit = 5

            anchor_result = await session.run(
                """
                MATCH ()-[r:SENT]->()
                RETURN toString(coalesce(max(r.timestamp), datetime())) AS anchor_ts
                """
            )
            anchor = await anchor_result.single()
            anchor_timestamp = (
                anchor["anchor_ts"] if anchor and anchor["anchor_ts"] else None
            )

            rapid_result = await session.run(
                """
                CALL {
                  MATCH ()-[rx:SENT]->()
                  RETURN coalesce(max(rx.timestamp), datetime()) AS anchor_ts
                }
                MATCH (a:Account)-[r:SENT]->(:Account)
                WHERE r.timestamp >= anchor_ts - duration({hours: $window_hours})
                WITH a, count(r) AS txn_count, sum(coalesce(r.amount, 0.0)) AS total_amount
                WHERE txn_count >= $min_txn_count AND total_amount >= $min_total_amount
                RETURN count(a) AS rapid_layering_accounts,
                       max(txn_count) AS max_txn_count_window,
                       max(total_amount) AS max_amount_window
                """,
                window_hours=rapid_window_hours,
                min_txn_count=rapid_min_txn_count,
                min_total_amount=rapid_min_total_amount,
            )
            rapid = await rapid_result.single()

            rapid_samples_result = await session.run(
                """
                CALL {
                  MATCH ()-[rx:SENT]->()
                  RETURN coalesce(max(rx.timestamp), datetime()) AS anchor_ts
                }
                MATCH (a:Account)-[r:SENT]->(b:Account)
                WHERE r.timestamp >= anchor_ts - duration({hours: $window_hours})
                WITH a, collect(DISTINCT b.id)[0..3] AS top_destinations,
                     count(r) AS txn_count,
                     sum(coalesce(r.amount, 0.0)) AS total_amount,
                     max(r.timestamp) AS last_seen
                WHERE txn_count >= $min_txn_count AND total_amount >= $min_total_amount
                RETURN a.id AS account_id,
                       txn_count,
                       total_amount,
                       top_destinations,
                       toString(last_seen) AS last_seen
                ORDER BY txn_count DESC, total_amount DESC
                LIMIT $sample_limit
                """,
                window_hours=rapid_window_hours,
                min_txn_count=rapid_min_txn_count,
                min_total_amount=rapid_min_total_amount,
                sample_limit=sample_limit,
            )
            rapid_samples: list[dict] = []
            async for record in rapid_samples_result:
                rapid_samples.append(
                    {
                        "account_id": record["account_id"],
                        "txn_count": int(record["txn_count"] or 0),
                        "total_amount": float(record["total_amount"] or 0.0),
                        "top_destinations": list(record["top_destinations"] or []),
                        "last_seen": record["last_seen"],
                    }
                )

            structuring_result = await session.run(
                """
                CALL {
                  MATCH ()-[rx:SENT]->()
                  RETURN coalesce(max(rx.timestamp), datetime()) AS anchor_ts
                }
                MATCH (:Account)-[r:SENT]->(:Account)
                WHERE r.timestamp >= anchor_ts - duration({days: $window_days})
                WITH anchor_ts, percentileCont(coalesce(r.amount, 0.0), 0.90) AS p90
                MATCH (s:Account)-[r:SENT]->(:Account)
                WHERE r.timestamp >= anchor_ts - duration({days: $window_days})
                  AND coalesce(r.amount, 0.0) >= p90 * $lower_factor
                  AND coalesce(r.amount, 0.0) < p90 * $upper_factor
                WITH p90, s,
                     count(r) AS near_threshold_txn_count,
                     avg(coalesce(r.amount, 0.0)) AS avg_amount,
                     max(coalesce(r.amount, 0.0)) AS max_amount
                WHERE near_threshold_txn_count >= $min_repeats
                RETURN count(s) AS structuring_accounts_window,
                       max(near_threshold_txn_count) AS max_repeat_count,
                       max(max_amount) AS max_structuring_amount,
                       p90 AS p90_amount
                """,
                window_days=structuring_window_days,
                lower_factor=structuring_lower_factor,
                upper_factor=structuring_upper_factor,
                min_repeats=structuring_min_repeats,
            )
            structuring = await structuring_result.single()

            structuring_samples_result = await session.run(
                """
                CALL {
                  MATCH ()-[rx:SENT]->()
                  RETURN coalesce(max(rx.timestamp), datetime()) AS anchor_ts
                }
                MATCH (:Account)-[r:SENT]->(:Account)
                WHERE r.timestamp >= anchor_ts - duration({days: $window_days})
                WITH anchor_ts, percentileCont(coalesce(r.amount, 0.0), 0.90) AS p90
                MATCH (s:Account)-[r:SENT]->(:Account)
                WHERE r.timestamp >= anchor_ts - duration({days: $window_days})
                  AND coalesce(r.amount, 0.0) >= p90 * $lower_factor
                  AND coalesce(r.amount, 0.0) < p90 * $upper_factor
                WITH p90, s,
                     count(r) AS near_threshold_txn_count,
                     avg(coalesce(r.amount, 0.0)) AS avg_amount,
                     min(coalesce(r.amount, 0.0)) AS min_amount,
                     max(coalesce(r.amount, 0.0)) AS max_amount
                WHERE near_threshold_txn_count >= $min_repeats
                RETURN s.id AS account_id,
                       near_threshold_txn_count,
                       avg_amount,
                       min_amount,
                       max_amount,
                       p90 AS p90_amount
                ORDER BY near_threshold_txn_count DESC, avg_amount DESC
                LIMIT $sample_limit
                """,
                window_days=structuring_window_days,
                lower_factor=structuring_lower_factor,
                upper_factor=structuring_upper_factor,
                min_repeats=structuring_min_repeats,
                sample_limit=sample_limit,
            )
            structuring_samples: list[dict] = []
            async for record in structuring_samples_result:
                structuring_samples.append(
                    {
                        "account_id": record["account_id"],
                        "near_threshold_txn_count": int(
                            record["near_threshold_txn_count"] or 0
                        ),
                        "avg_amount": float(record["avg_amount"] or 0.0),
                        "min_amount": float(record["min_amount"] or 0.0),
                        "max_amount": float(record["max_amount"] or 0.0),
                        "p90_amount": float(record["p90_amount"] or 0.0),
                    }
                )

            dormant_result = await session.run(
                """
                CALL {
                  MATCH (t:Transaction)
                  RETURN coalesce(max(t.timestamp), datetime()) AS anchor_ts
                }
                MATCH (a:Account)-[recent:SENT]->(:Account)
                WHERE recent.timestamp >= anchor_ts - duration({days: $window_days})
                WITH a,
                     min(recent.timestamp) AS first_recent_ts,
                     max(coalesce(recent.amount, 0.0)) AS max_recent_amount,
                     sum(coalesce(recent.amount, 0.0)) AS total_recent_amount
                OPTIONAL MATCH (a)-[prior:SENT]->(:Account)
                WHERE prior.timestamp < first_recent_ts
                  AND prior.timestamp >= first_recent_ts - duration({days: $prior_days})
                WITH a, first_recent_ts, max_recent_amount, total_recent_amount, count(prior) AS prior_txn_count
                WHERE prior_txn_count = 0 AND max_recent_amount >= $min_reactivation_amount
                RETURN count(a) AS dormant_awakening_accounts_window,
                       max(max_recent_amount) AS max_reactivation_amount
                """,
                window_days=dormant_window_days,
                prior_days=dormant_prior_days,
                min_reactivation_amount=dormant_min_amount,
            )
            dormant = await dormant_result.single()

            dormant_samples_result = await session.run(
                """
                CALL {
                  MATCH (t:Transaction)
                  RETURN coalesce(max(t.timestamp), datetime()) AS anchor_ts
                }
                MATCH (a:Account)-[recent:SENT]->(:Account)
                WHERE recent.timestamp >= anchor_ts - duration({days: $window_days})
                WITH a,
                     min(recent.timestamp) AS first_recent_ts,
                     max(coalesce(recent.amount, 0.0)) AS max_recent_amount,
                     sum(coalesce(recent.amount, 0.0)) AS total_recent_amount
                OPTIONAL MATCH (a)-[prior:SENT]->(:Account)
                WHERE prior.timestamp < first_recent_ts
                  AND prior.timestamp >= first_recent_ts - duration({days: $prior_days})
                WITH a, first_recent_ts, max_recent_amount, total_recent_amount, count(prior) AS prior_txn_count
                WHERE prior_txn_count = 0 AND max_recent_amount >= $min_reactivation_amount
                RETURN a.id AS account_id,
                       toString(first_recent_ts) AS reactivated_at,
                       max_recent_amount,
                       total_recent_amount,
                       prior_txn_count
                ORDER BY max_recent_amount DESC
                LIMIT $sample_limit
                """,
                window_days=dormant_window_days,
                prior_days=dormant_prior_days,
                min_reactivation_amount=dormant_min_amount,
                sample_limit=sample_limit,
            )
            dormant_samples: list[dict] = []
            async for record in dormant_samples_result:
                dormant_samples.append(
                    {
                        "account_id": record["account_id"],
                        "reactivated_at": record["reactivated_at"],
                        "max_recent_amount": float(record["max_recent_amount"] or 0.0),
                        "total_recent_amount": float(
                            record["total_recent_amount"] or 0.0
                        ),
                        "prior_txn_count": int(record["prior_txn_count"] or 0),
                    }
                )

            mule_result = await session.run(
                """
                CALL {
                  MATCH ()-[rx:SENT]->()
                  RETURN coalesce(max(rx.timestamp), datetime()) AS anchor_ts
                }
                MATCH (s:Account)-[in:SENT]->(m:Account)-[out:SENT]->(d:Account)
                WHERE in.timestamp >= anchor_ts - duration({hours: $window_hours})
                  AND out.timestamp >= anchor_ts - duration({hours: $window_hours})
                  AND s <> d
                WITH m,
                     count(DISTINCT s) AS distinct_senders,
                     count(DISTINCT d) AS distinct_receivers,
                     sum(coalesce(in.amount, 0.0)) AS pass_through_amount
                WHERE distinct_senders >= $min_senders AND distinct_receivers >= $min_receivers
                RETURN count(m) AS mule_hub_accounts_window,
                       max(distinct_senders) AS max_distinct_senders,
                       max(distinct_receivers) AS max_distinct_receivers,
                       max(pass_through_amount) AS max_pass_through_amount
                """,
                window_hours=mule_window_hours,
                min_senders=mule_min_senders,
                min_receivers=mule_min_receivers,
            )
            mule = await mule_result.single()

            mule_samples_result = await session.run(
                """
                CALL {
                  MATCH ()-[rx:SENT]->()
                  RETURN coalesce(max(rx.timestamp), datetime()) AS anchor_ts
                }
                MATCH (s:Account)-[in:SENT]->(m:Account)-[out:SENT]->(d:Account)
                WHERE in.timestamp >= anchor_ts - duration({hours: $window_hours})
                  AND out.timestamp >= anchor_ts - duration({hours: $window_hours})
                  AND s <> d
                WITH m,
                     count(DISTINCT s) AS distinct_senders,
                     count(DISTINCT d) AS distinct_receivers,
                     sum(coalesce(in.amount, 0.0)) AS pass_through_amount,
                     collect(DISTINCT s.id)[0..3] AS sample_sources,
                     collect(DISTINCT d.id)[0..3] AS sample_destinations
                WHERE distinct_senders >= $min_senders AND distinct_receivers >= $min_receivers
                RETURN m.id AS account_id,
                       distinct_senders,
                       distinct_receivers,
                       pass_through_amount,
                       sample_sources,
                       sample_destinations
                ORDER BY distinct_senders DESC, distinct_receivers DESC, pass_through_amount DESC
                LIMIT $sample_limit
                """,
                window_hours=mule_window_hours,
                min_senders=mule_min_senders,
                min_receivers=mule_min_receivers,
                sample_limit=sample_limit,
            )
            mule_samples: list[dict] = []
            async for record in mule_samples_result:
                mule_samples.append(
                    {
                        "account_id": record["account_id"],
                        "distinct_senders": int(record["distinct_senders"] or 0),
                        "distinct_receivers": int(record["distinct_receivers"] or 0),
                        "pass_through_amount": float(
                            record["pass_through_amount"] or 0.0
                        ),
                        "sample_sources": list(record["sample_sources"] or []),
                        "sample_destinations": list(
                            record["sample_destinations"] or []
                        ),
                    }
                )

            rule_result = await session.run(
                """
                MATCH (t:Transaction)
                UNWIND coalesce(t.rule_violations, []) AS rule
                RETURN rule, count(*) AS cnt
                ORDER BY cnt DESC
                """
            )
            rule_counts: dict[str, int] = {}
            async for record in rule_result:
                if record["rule"]:
                    rule_counts[str(record["rule"])] = int(record["cnt"])

            rule_samples_result = await session.run(
                """
                MATCH (t:Transaction)
                UNWIND coalesce(t.rule_violations, []) AS rule
                WITH rule, t
                ORDER BY coalesce(t.risk_score, 0.0) DESC, t.timestamp DESC
                WITH rule, collect({
                    transaction_id: t.id,
                    from_account: t.from_account,
                    to_account: t.to_account,
                    amount: coalesce(t.amount, 0.0),
                    risk_score: coalesce(t.risk_score, 0.0)
                })[0..3] AS samples
                RETURN rule, samples
                """
            )
            rule_samples: dict[str, list[dict]] = {}
            async for record in rule_samples_result:
                rule = record["rule"]
                if not rule:
                    continue
                entries = []
                for sample in record["samples"] or []:
                    entries.append(
                        {
                            "transaction_id": sample.get("transaction_id"),
                            "from_account": sample.get("from_account"),
                            "to_account": sample.get("to_account"),
                            "amount": float(sample.get("amount") or 0.0),
                            "risk_score": float(sample.get("risk_score") or 0.0),
                        }
                    )
                rule_samples[str(rule)] = entries

            return {
                "analysis_anchor_timestamp": anchor_timestamp,
                "thresholds": {
                    "rapid_layering": {
                        "window_hours": rapid_window_hours,
                        "min_txn_count": rapid_min_txn_count,
                        "min_total_amount": rapid_min_total_amount,
                    },
                    "structuring": {
                        "window_days": structuring_window_days,
                        "min_repeats": structuring_min_repeats,
                        "lower_factor": structuring_lower_factor,
                        "upper_factor": structuring_upper_factor,
                    },
                    "dormant_awakening": {
                        "window_days": dormant_window_days,
                        "prior_activity_days": dormant_prior_days,
                        "min_reactivation_amount": dormant_min_amount,
                    },
                    "mule_hub": {
                        "window_hours": mule_window_hours,
                        "min_distinct_senders": mule_min_senders,
                        "min_distinct_receivers": mule_min_receivers,
                    },
                },
                "rapid_layering_accounts_24h": int(
                    rapid["rapid_layering_accounts"] if rapid else 0
                ),
                "max_txn_count_24h": int(
                    rapid["max_txn_count_window"]
                    if rapid and rapid["max_txn_count_window"]
                    else 0
                ),
                "max_amount_24h": float(
                    rapid["max_amount_window"]
                    if rapid and rapid["max_amount_window"]
                    else 0.0
                ),
                "structuring_edges_7d": int(
                    structuring["structuring_accounts_window"] if structuring else 0
                ),
                "dormant_awakening_edges_30d": int(
                    dormant["dormant_awakening_accounts_window"] if dormant else 0
                ),
                "mule_hub_accounts_24h": int(
                    mule["mule_hub_accounts_window"] if mule else 0
                ),
                "rule_violations_from_transactions": rule_counts,
                "sample_entities": {
                    "rapid_layering": rapid_samples,
                    "structuring": structuring_samples,
                    "dormant_awakening": dormant_samples,
                    "mule_hub": mule_samples,
                    "rule_violations": rule_samples,
                },
            }


neo4j_service = Neo4jService()
