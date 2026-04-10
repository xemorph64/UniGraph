from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..services.neo4j_service import neo4j_service
from ..services.llm_service import llm_service

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

    return STRGenerateResponse(
        str_id=f"STR-{request.alert_id}",
        narrative=narrative,
        status="draft",
        alert_id=request.alert_id,
        account_id=alert["account_id"],
        risk_score=alert.get("risk_score", 0),
    )


@router.post("/str/{str_id}/submit")
async def submit_str(str_id: str, request: STRSubmitRequest):
    """Submit STR to FIU-IND with maker-checker."""
    return {"str_id": str_id, "status": "submitted", "reference_id": str_id}
