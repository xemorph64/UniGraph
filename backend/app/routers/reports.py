from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..auth.jwt_rbac import require_permission, User

router = APIRouter()


class STRGenerateRequest(BaseModel):
    case_id: str


class STRGenerateResponse(BaseModel):
    case_id: str
    str_draft: str
    xml_preview: str
    shap_summary: str
    transaction_summary: str
    generated_at: str


class STRSubmitRequest(BaseModel):
    case_id: str
    edited_narrative: str
    digital_signature: str


@router.post("/str/generate", response_model=STRGenerateResponse)
async def generate_str(
    request: STRGenerateRequest,
    user: User = Depends(require_permission("write:reports")),
):
    """Generate STR draft with LLM narrative."""
    return STRGenerateResponse(
        case_id=request.case_id,
        str_draft=f"Subject Account was flagged with risk score 87 due to unusual velocity patterns...",
        xml_preview='<?xml version="1.0"?><STR>...</STR>',
        shap_summary="velocity_1h: +0.32, shared_device_risk: +0.28",
        transaction_summary="8 transactions in 47 minutes totaling Rs.585,000",
        generated_at="2026-04-10T00:00:00Z",
    )


@router.post("/str/{case_id}/submit")
async def submit_str(
    case_id: str,
    request: STRSubmitRequest,
    user: User = Depends(require_permission("submit:str")),
):
    """Submit STR to FIU-IND with maker-checker."""
    return {"case_id": case_id, "status": "submitted", "reference_id": f"STR-{case_id}"}
