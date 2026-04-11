from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..services.neo4j_service import neo4j_service
from ..services.timeline_service import timeline_service

router = APIRouter()


class AccountProfile(BaseModel):
    id: str
    customer_id: str
    account_type: str
    branch_code: str
    open_date: str
    kyc_tier: int
    risk_score: float
    is_dormant: bool
    community_id: int
    pagerank: float
    last_active: str


class SubgraphResponse(BaseModel):
    nodes: list[dict]
    relationships: list[dict]


@router.get("/{account_id}/graph")
async def get_account_subgraph(account_id: str, hops: int = Query(2, ge=1, le=4)):
    """Get N-hop subgraph for Cytoscape visualization."""
    subgraph = await neo4j_service.get_account_subgraph(account_id, hops=hops)
    return {"nodes": subgraph.get("nodes", []), "edges": subgraph.get("edges", [])}


@router.get("/{account_id}/profile")
async def get_account_profile(account_id: str):
    """Get account profile with current risk score."""
    async with neo4j_service.driver.session() as session:
        result = await session.run(
            "MATCH (a:Account {id: $account_id}) RETURN a", account_id=account_id
        )
        record = await result.single()
        if record:
            return dict(record["a"])
        return {"error": "Account not found"}


@router.get("/{account_id}/timeline")
async def get_account_timeline(account_id: str, days: int = Query(30, ge=1, le=365)):
    """Get historical risk score timeline from Cassandra."""
    return await timeline_service.get_account_timeline(account_id=account_id, days=days)
