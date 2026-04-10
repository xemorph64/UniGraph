from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from ..auth.jwt_rbac import require_permission, User

router = APIRouter()


class AlertResponse(BaseModel):
    alert_id: str
    txn_id: str
    account_id: str
    risk_score: int
    risk_level: str
    recommendation: str
    shap_summary: str
    rule_flags: list[str]
    status: str
    created_at: str
    assigned_to: Optional[str]


@router.get("/")
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    min_risk_score: Optional[int] = None,
    account_id: Optional[str] = None,
    user: User = Depends(require_permission("read:alerts")),
):
    """List alerts with pagination and filters."""
    return {"items": [], "page": page, "page_size": page_size}


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str, user: User = Depends(require_permission("write:alerts"))
):
    """Investigator takes ownership of alert."""
    return {"alert_id": alert_id, "status": "acknowledged", "assigned_to": user.user_id}


@router.post("/{alert_id}/escalate")
async def escalate_alert(
    alert_id: str, reason: str, user: User = Depends(require_permission("write:alerts"))
):
    """Escalate alert to supervisor."""
    return {"alert_id": alert_id, "status": "escalated", "reason": reason}
