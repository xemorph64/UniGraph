from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..auth.jwt_rbac import User, require_permission

router = APIRouter()


class TransactionResponse(BaseModel):
    txn_id: str
    from_account: str
    to_account: str
    amount: float
    currency: str
    channel: str
    timestamp: str
    risk_score: Optional[float]
    rule_violations: list[str]
    is_flagged: bool
    alert_id: Optional[str]


@router.get("/{txn_id}", response_model=TransactionResponse)
async def get_transaction(
    txn_id: str,
    user: User = Depends(require_permission("read:transactions")),
):
    """Get transaction details with SHAP explanation."""


@router.get("/")
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    account_id: Optional[str] = None,
    channel: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    flagged_only: bool = False,
    user: User = Depends(require_permission("read:transactions")),
):
    """List transactions with pagination and filters."""


@router.post("/ingest")
async def ingest_transaction(
    txn: dict,
    user: User = Depends(require_permission("write:transactions")),
):
    """Manually ingest a transaction (for testing)."""
