from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from ..services.neo4j_service import neo4j_service
from ..services.llm_service import llm_service

router = APIRouter()


class AlertResponse(BaseModel):
    id: str
    transaction_id: str
    account_id: str
    risk_score: float
    risk_level: str
    recommendation: str
    shap_top3: list[str]
    rule_flags: list[str]
    status: str
    created_at: Optional[str] = None
    assigned_to: Optional[str] = None


@router.get("/")
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    min_risk_score: Optional[int] = None,
):
    """List alerts with pagination and filters."""
    alerts = await neo4j_service.get_alerts(
        status=status, min_risk_score=min_risk_score, limit=page_size
    )
    return {"items": alerts, "page": page, "page_size": page_size, "total": len(alerts)}


@router.get("/{alert_id}")
async def get_alert(alert_id: str):
    """Get single alert by ID."""
    alert = await neo4j_service.get_alert_by_id(alert_id)
    if not alert:
        return {"error": "Alert not found"}
    return alert


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Investigator takes ownership of alert."""
    updated = await neo4j_service.update_alert_status(alert_id, "INVESTIGATING")
    return {"alert_id": alert_id, "status": "INVESTIGATING", "assigned_to": "demo_user"}


@router.post("/{alert_id}/escalate")
async def escalate_alert(alert_id: str, reason: str = ""):
    """Escalate alert to supervisor."""
    updated = await neo4j_service.update_alert_status(
        alert_id, "ESCALATED", "SUPERVISOR"
    )
    return {"alert_id": alert_id, "status": "ESCALATED", "reason": reason}


@router.get("/{alert_id}/investigate")
async def investigate_alert(alert_id: str, hops: int = Query(2, ge=1, le=4)):
    """Get dynamic investigation payload with alert, graph and analyst note."""
    alert = await neo4j_service.get_alert_by_id(alert_id)
    if not alert:
        return {"error": "Alert not found"}

    account_id = alert.get("account_id", "")
    transaction_id = alert.get("transaction_id", "")
    graph = await neo4j_service.get_account_subgraph(account_id, hops=hops)
    transaction = (
        await neo4j_service.get_transaction(transaction_id) if transaction_id else None
    )

    rule_flags = alert.get("rule_flags") or []
    shap_top3 = alert.get("shap_top3") or []
    risk_score = alert.get("risk_score", 0)
    risk_level = alert.get("risk_level", "UNKNOWN")
    recommendation = alert.get("recommendation", "Review transaction flow")

    llm_case_data = {
        "account_id": account_id,
        "risk_score": risk_score,
        "alert_count": 1,
        "rule_violations": ", ".join(rule_flags) or "none",
        "pattern_description": f"{len(graph.get('nodes', []))} linked nodes, "
        f"{len(graph.get('edges', []))} fund-flow edges",
    }
    note = await llm_service.summarize_case(llm_case_data)

    return {
        "alert": alert,
        "transaction": transaction,
        "graph": graph,
        "investigation_note": note,
    }
