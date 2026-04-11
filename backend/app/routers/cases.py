from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from ..auth.jwt_rbac import require_permission, User
from ..services.neo4j_service import neo4j_service

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


def _to_case_response(case_data: dict) -> CaseResponse:
    return CaseResponse(
        case_id=case_data.get("id", ""),
        alert_id=case_data.get("alert_id", ""),
        title=case_data.get("title", ""),
        description=case_data.get("description", ""),
        priority=case_data.get("priority", "MEDIUM"),
        status=case_data.get("status", "OPEN"),
        assigned_to=case_data.get("assigned_to", ""),
        created_at=case_data.get("created_at", ""),
        closed_at=case_data.get("closed_at"),
        labels=case_data.get("labels") or [],
    )


@router.post("/", response_model=CaseResponse)
async def create_case(
    case: CaseCreate, user: User = Depends(require_permission("write:cases"))
):
    """Create investigation case from alert."""
    case_id = f"CASE-{uuid.uuid4().hex[:10].upper()}"
    created = await neo4j_service.create_case(
        case_id=case_id,
        alert_id=case.alert_id,
        title=case.title,
        description=case.description,
        priority=case.priority,
        assigned_to=user.user_id,
    )
    if not created:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _to_case_response(created)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str, user: User = Depends(require_permission("read:cases"))
):
    """Get case details."""
    case_data = await neo4j_service.get_case(case_id)
    if not case_data:
        raise HTTPException(status_code=404, detail="Case not found")
    return _to_case_response(case_data)


@router.put("/{case_id}/close", response_model=CaseResponse)
async def close_case(
    case_id: str,
    close_data: CaseClose,
    user: User = Depends(require_permission("write:cases")),
):
    """Close case and label for ML retraining."""
    closed = await neo4j_service.close_case(
        case_id=case_id,
        outcome=close_data.outcome,
        notes=close_data.notes,
        closed_by=user.user_id,
    )
    if not closed:
        raise HTTPException(status_code=404, detail="Case not found")
    return _to_case_response(closed)


@router.get("/")
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    user: User = Depends(require_permission("read:cases")),
):
    """List cases with pagination."""
    result = await neo4j_service.list_cases(
        page=page,
        page_size=page_size,
        status=status,
        assigned_to=assigned_to,
    )
    return {
        "items": result["items"],
        "total": result["total"],
        "page": page,
        "page_size": page_size,
    }
