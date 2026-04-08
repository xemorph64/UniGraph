from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..auth.jwt_rbac import User, require_permission

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


@router.get("/{account_id}/profile", response_model=AccountProfile)
async def get_account_profile(
    account_id: str,
    user: User = Depends(require_permission("read:accounts")),
):
    """Get account profile with current risk score."""


@router.get("/{account_id}/graph")
async def get_account_subgraph(
    account_id: str,
    hops: int = Query(2, ge=1, le=4),
    window_start: Optional[str] = None,
    user: User = Depends(require_permission("read:graph")),
):
    """Get N-hop subgraph for Cytoscape visualization."""


@router.get("/{account_id}/timeline")
async def get_account_timeline(
    account_id: str,
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(require_permission("read:accounts")),
):
    """Get historical risk score timeline from Cassandra."""
