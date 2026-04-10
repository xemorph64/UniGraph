from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from ..auth.jwt_rbac import require_permission, User

router = APIRouter()


class CaseCreate(BaseModel):
    alert_id: str
    title: str
    description: str
    priority: str = "MEDIUM"


class CaseResponse(BaseModel):
    case_id: str
    alert_id: str
    title: str
    description: str
    priority: str
    status: str
    assigned_to: str
    created_at: str
    closed_at: Optional[str]
    labels: list[str]


class CaseClose(BaseModel):
    outcome: str
    notes: str


@router.post("/", response_model=CaseResponse)
async def create_case(
    case: CaseCreate, user: User = Depends(require_permission("write:cases"))
):
    """Create investigation case from alert."""
    return CaseResponse(
        case_id=f"CASE-{case.alert_id}",
        alert_id=case.alert_id,
        title=case.title,
        description=case.description,
        priority=case.priority,
        status="OPEN",
        assigned_to=user.user_id,
        created_at="2026-04-10T00:00:00Z",
        closed_at=None,
        labels=[],
    )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str, user: User = Depends(require_permission("read:cases"))
):
    """Get case details."""
    return CaseResponse(
        case_id=case_id,
        alert_id="ALT-001",
        title="Investigation Case",
        description="Case description",
        priority="MEDIUM",
        status="OPEN",
        assigned_to="INV-001",
        created_at="2026-04-10T00:00:00Z",
        closed_at=None,
        labels=[],
    )


@router.put("/{case_id}/close", response_model=CaseResponse)
async def close_case(
    case_id: str,
    close_data: CaseClose,
    user: User = Depends(require_permission("write:cases")),
):
    """Close case and label for ML retraining."""
    return CaseResponse(
        case_id=case_id,
        alert_id="ALT-001",
        title="Investigation Case",
        description="Case description",
        priority="MEDIUM",
        status="CLOSED",
        assigned_to=user.user_id,
        created_at="2026-04-10T00:00:00Z",
        closed_at="2026-04-10T00:00:00Z",
        labels=[close_data.outcome],
    )


@router.get("/")
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    user: User = Depends(require_permission("read:cases")),
):
    """List cases with pagination."""
    return {"items": [], "page": page, "page_size": page_size}
