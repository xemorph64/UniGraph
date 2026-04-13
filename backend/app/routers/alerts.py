from fastapi import APIRouter, Query, HTTPException
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
    primary_fraud_type: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    assigned_to: Optional[str] = None


@router.get("/")
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    min_risk_score: Optional[int] = None,
    transaction_id_prefix: Optional[str] = None,
):
    """List alerts with pagination and filters."""
    alerts = await neo4j_service.get_alerts(
        status=status,
        min_risk_score=min_risk_score,
        transaction_id_prefix=transaction_id_prefix,
        limit=page_size,
    )
    return {"items": alerts, "page": page, "page_size": page_size, "total": len(alerts)}


@router.get("/{alert_id}")
async def get_alert(alert_id: str):
    """Get single alert by ID."""
    alert = await neo4j_service.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
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
        raise HTTPException(status_code=404, detail="Alert not found")

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

    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    linked_accounts: set[str] = set()
    for edge in edges:
        source = str(edge.get("source") or edge.get("from") or "")
        target = str(edge.get("target") or edge.get("to") or "")
        if source == account_id and target and target != account_id:
            linked_accounts.add(target)
        if target == account_id and source and source != account_id:
            linked_accounts.add(source)

    tx_snapshot_parts: list[str] = []
    if transaction:
        tx_snapshot_parts = [
            f"txn_id={transaction.get('txn_id', transaction_id) or transaction_id}",
            f"amount={transaction.get('amount', 'NA')}",
            f"channel={transaction.get('channel', 'NA')}",
            f"from={transaction.get('from_account', 'NA')}",
            f"to={transaction.get('to_account', 'NA')}",
            f"timestamp={transaction.get('timestamp') or transaction.get('created_at') or 'NA'}",
            f"score_source={transaction.get('scoring_source', 'NA')}",
            f"model_version={transaction.get('model_version', 'NA')}",
        ]
    transaction_snapshot = (
        "; ".join(tx_snapshot_parts)
        if tx_snapshot_parts
        else "No transaction snapshot available"
    )

    linked_accounts_text = ", ".join(sorted(linked_accounts)[:8]) or "none"

    llm_case_data = {
        "account_id": account_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "alert_count": 1,
        "primary_fraud_type": alert.get("primary_fraud_type") or "UNSPECIFIED",
        "rule_violations": rule_flags,
        "shap_reasons": shap_top3,
        "recommendation": recommendation,
        "pattern_description": (
            f"{len(nodes)} linked nodes, {len(edges)} fund-flow edges, "
            f"counterparty accounts near anchor: {linked_accounts_text}"
        ),
        "graph_summary": (
            f"Subgraph depth={hops}; nodes={len(nodes)}; edges={len(edges)}; "
            f"linked_accounts={linked_accounts_text}"
        ),
        "transaction_snapshot": transaction_snapshot,
    }
    note = await llm_service.summarize_case(llm_case_data)

    return {
        "alert": alert,
        "transaction": transaction,
        "graph": graph,
        "investigation_note": note,
    }
