from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
from ..auth.jwt_rbac import require_permission, User
from ..services.neo4j_service import neo4j_service
from ..services.llm_service import llm_service
from ..services.fiu_ind_service import FIUIndService
from ..config import settings

router = APIRouter()


class STRGenerateRequest(BaseModel):
    alert_id: str
    case_notes: Optional[str] = ""


class STRGenerateResponse(BaseModel):
    str_id: str
    narrative: str
    status: str
    alert_id: str
    account_id: str
    risk_score: float


class STRSubmitRequest(BaseModel):
    str_id: str
    edited_narrative: str
    digital_signature: str


class STRReviewRequest(BaseModel):
    notes: str = ""


@router.get("/str/{str_id}")
async def get_str_report(str_id: str):
    """Get persisted STR details and current submission status."""
    str_report = await neo4j_service.get_str_report(str_id)
    if not str_report:
        raise HTTPException(status_code=404, detail="STR not found")
    return str_report


@router.get("/str")
async def list_str_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    account_id: Optional[str] = None,
):
    """List STR reports with filters and pagination."""
    result = await neo4j_service.list_str_reports(
        page=page,
        page_size=page_size,
        status=status.upper() if status else None,
        account_id=account_id,
    )
    return {
        "items": result["items"],
        "total": result["total"],
        "page": page,
        "page_size": page_size,
    }


@router.post("/str/generate", response_model=STRGenerateResponse)
async def generate_str(request: STRGenerateRequest):
    """Generate STR draft with LLM narrative."""
    alert = await neo4j_service.get_alert_by_id(request.alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    subgraph = await neo4j_service.get_account_subgraph(alert["account_id"], hops=2)
    case_data = {
        "case_id": f"CASE-{request.alert_id}",
        "account_id": alert["account_id"],
        "risk_score": alert.get("risk_score", 0),
        "risk_level": alert.get("risk_level", "HIGH"),
        "rule_violations": alert.get("rule_flags", []),
        "shap_top3": alert.get("shap_top3", []),
        "transaction_chain": f"Account {alert['account_id']} has {len(subgraph.get('nodes', []))} connected nodes",
    }

    narrative = await llm_service.generate_str_narrative(case_data)
    str_id = f"STR-{request.alert_id}"

    try:
        await neo4j_service.create_str_report(
            str_id=str_id,
            alert_id=request.alert_id,
            account_id=alert["account_id"],
            risk_score=alert.get("risk_score", 0),
            narrative=narrative,
            generated_by="LLM",
        )
    except Exception:
        # Keep generation successful even if persistence is temporarily unavailable.
        pass

    return STRGenerateResponse(
        str_id=str_id,
        narrative=narrative,
        status="draft",
        alert_id=request.alert_id,
        account_id=alert["account_id"],
        risk_score=alert.get("risk_score", 0),
    )


@router.post("/str/{str_id}/submit")
async def submit_str(str_id: str, request: STRSubmitRequest):
    """Submit STR to FIU-IND with maker-checker."""
    str_report = await neo4j_service.get_str_report(str_id)
    if not str_report:
        raise HTTPException(status_code=404, detail="STR not found")

    if not settings.DEMO_MODE and str(str_report.get("status", "")).upper() != "APPROVED":
        raise HTTPException(
            status_code=409,
            detail="STR must be approved before submission",
        )

    reference_id = f"DEMO-{uuid4().hex[:12].upper()}"
    status = "submitted-demo"
    provider_response: dict = {}

    fiu_is_configured = (
        bool(settings.FIU_IND_API_URL)
        and bool(settings.FIU_IND_MTLS_CERT_PATH)
        and bool(settings.FIU_IND_MTLS_KEY_PATH)
    )

    if fiu_is_configured:
        try:
            fiu_service = FIUIndService(
                api_url=settings.FIU_IND_API_URL,
                mtls_cert_path=settings.FIU_IND_MTLS_CERT_PATH,
                mtls_key_path=settings.FIU_IND_MTLS_KEY_PATH,
            )
            provider_response = await fiu_service.submit_str(
                str_xml=request.edited_narrative,
                digital_signature=request.digital_signature,
            )
            if provider_response:
                reference_id = (
                    provider_response.get("reference_id")
                    or provider_response.get("referenceId")
                    or reference_id
                )
                status = "submitted"
            else:
                status = "queued"
        except Exception:
            status = "queued"

    try:
        await neo4j_service.submit_str_report(
            str_id=str_id,
            edited_narrative=request.edited_narrative,
            digital_signature=request.digital_signature,
            reference_id=reference_id,
            status=status.upper(),
        )
    except Exception:
        pass

    return {
        "str_id": str_id,
        "status": status,
        "reference_id": reference_id,
        "provider_response": provider_response,
    }


@router.post("/str/{str_id}/approve")
async def approve_str(
    str_id: str,
    request: STRReviewRequest,
    user: User = Depends(require_permission("approve:str")),
):
    """Approve STR for submission as checker step."""
    str_report = await neo4j_service.get_str_report(str_id)
    if not str_report:
        raise HTTPException(status_code=404, detail="STR not found")

    status = str(str_report.get("status", "")).upper()
    if status.startswith("SUBMITTED"):
        raise HTTPException(status_code=409, detail="Submitted STR cannot be re-approved")

    updated = await neo4j_service.update_str_review(
        str_id=str_id,
        status="APPROVED",
        reviewed_by=user.user_id,
        review_notes=request.notes,
    )
    return {"str_id": str_id, "status": "APPROVED", "review": updated}


@router.post("/str/{str_id}/reject")
async def reject_str(
    str_id: str,
    request: STRReviewRequest,
    user: User = Depends(require_permission("approve:str")),
):
    """Reject STR in checker step."""
    str_report = await neo4j_service.get_str_report(str_id)
    if not str_report:
        raise HTTPException(status_code=404, detail="STR not found")

    status = str(str_report.get("status", "")).upper()
    if status.startswith("SUBMITTED"):
        raise HTTPException(status_code=409, detail="Submitted STR cannot be rejected")

    updated = await neo4j_service.update_str_review(
        str_id=str_id,
        status="REJECTED",
        reviewed_by=user.user_id,
        review_notes=request.notes,
    )
    return {"str_id": str_id, "status": "REJECTED", "review": updated}
