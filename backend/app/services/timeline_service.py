import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import structlog

from ..config import settings
from .neo4j_service import neo4j_service

logger = structlog.get_logger()


class TimelineService:
    def __init__(self):
        self._cluster: Optional[Any] = None
        self._session: Optional[Any] = None

    def _ensure_session(self) -> Any:
        if self._session:
            return self._session

        try:
            from cassandra.cluster import Cluster
        except Exception as ex:
            raise RuntimeError("cassandra_driver_unavailable") from ex

        contact_points = [
            cp.strip()
            for cp in settings.CASSANDRA_CONTACT_POINTS.split(",")
            if cp.strip()
        ]
        self._cluster = Cluster(contact_points=contact_points)
        self._session = self._cluster.connect(settings.CASSANDRA_KEYSPACE)
        return self._session

    def _query_cassandra_timeline_sync(self, account_id: str, days: int) -> list[dict]:
        session = self._ensure_session()
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            "SELECT computed_at, risk_score, ml_score, rule_flags, community_id, pagerank "
            "FROM account_risk_history WHERE account_id=%s AND computed_at >= %s"
        )
        rows = session.execute(query, (account_id, since))

        items: list[dict] = []
        for row in rows:
            computed_at = row.computed_at
            items.append(
                {
                    "computed_at": computed_at.isoformat() if hasattr(computed_at, "isoformat") else str(computed_at),
                    "risk_score": float(row.risk_score or 0.0),
                    "ml_score": float(row.ml_score or 0.0),
                    "rule_flags": list(row.rule_flags or []),
                    "community_id": int(row.community_id or 0),
                    "pagerank": float(row.pagerank or 0.0),
                }
            )

        return list(reversed(items))

    async def get_account_timeline(self, account_id: str, days: int = 30) -> dict[str, Any]:
        try:
            cassandra_timeline = await asyncio.to_thread(
                self._query_cassandra_timeline_sync, account_id, days
            )
            if cassandra_timeline:
                return {
                    "account_id": account_id,
                    "days": days,
                    "source": "cassandra",
                    "timeline": cassandra_timeline,
                }
        except Exception as ex:
            logger.warning("timeline_cassandra_unavailable", error=str(ex))

        graph_timeline = await neo4j_service.get_account_timeline_from_graph(
            account_id=account_id,
            days=days,
        )
        return {
            "account_id": account_id,
            "days": days,
            "source": "neo4j_fallback",
            "timeline": graph_timeline,
        }

    async def close(self) -> None:
        if self._session:
            self._session.shutdown()
            self._session = None
        if self._cluster:
            self._cluster.shutdown()
            self._cluster = None


timeline_service = TimelineService()
