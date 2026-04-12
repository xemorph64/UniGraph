from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
from ..auth.jwt_rbac import require_permission, User
from ..config import settings
from ..services.finacle_service import FinacleService
from ..services.ncrp_service import NCRPService
from ..services.neo4j_service import neo4j_service

router = APIRouter()


class LienRequest(BaseModel):
    accountId: str
    reason: str
    alertId: str
    amount: float
    initiatedBy: str
    requiresMakerChecker: bool = True


class FreezeRequest(BaseModel):
    accountId: str
    reason: str
    caseId: str
    initiatedBy: str
    requiresMakerChecker: bool = True


class NCRPReportRequest(BaseModel):
    complaintId: str
    accountId: str
    action: str
    evidence: dict


class HoldRequest(BaseModel):
    transactionId: str
    reason: str
    initiatedBy: str
    requiresMakerChecker: bool = True


class EnforcementReviewRequest(BaseModel):
    notes: str = ""


def _finacle_is_configured() -> bool:
    return bool(
        settings.FINACLE_API_URL
        and settings.FINACLE_CLIENT_ID
        and settings.FINACLE_CLIENT_SECRET
    )


def _ncrp_is_configured() -> bool:
    return bool(settings.NCRP_API_URL and settings.NCRP_API_KEY)


def _merge_metadata(action: dict, updates: dict) -> dict:
    existing = action.get("metadata") or {}
    if not isinstance(existing, dict):
        existing = {}
    return {**existing, **updates}


@router.get("/actions/{action_id}")
async def get_enforcement_action(
    action_id: str,
    user: User = Depends(require_permission("read:reports")),
):
    """Get a single enforcement action by id."""
    action = await neo4j_service.get_enforcement_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Enforcement action not found")
    return action


@router.get("/actions")
async def list_enforcement_actions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    action_type: Optional[str] = None,
    status: Optional[str] = None,
    account_id: Optional[str] = None,
    user: User = Depends(require_permission("read:reports")),
):
    """List enforcement actions with filters and pagination."""
    result = await neo4j_service.list_enforcement_actions(
        page=page,
        page_size=page_size,
        action_type=action_type.upper() if action_type else None,
        status=status.upper() if status else None,
        account_id=account_id,
    )
    return {
        "items": result["items"],
        "total": result["total"],
        "page": page,
        "page_size": page_size,
    }


@router.post("/actions/{action_id}/approve")
async def approve_enforcement_action(
    action_id: str,
    request: EnforcementReviewRequest,
    user: User = Depends(require_permission("approve:enforcement")),
):
    """Approve pending maker-checker enforcement action and execute provider call if configured."""
    action = await neo4j_service.get_enforcement_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Enforcement action not found")

    current_status = str(action.get("status", "")).upper()
    if current_status not in {"PENDING_APPROVAL", "PENDING"}:
        raise HTTPException(
            status_code=409,
            detail=f"Action cannot be approved from status {current_status or 'UNKNOWN'}",
        )

    provider_response = {}
    next_status = "APPROVED_DEMO"
    action_type = str(action.get("action_type", "")).upper()
    metadata = action.get("metadata") or {}
    reason = str(action.get("reason", ""))

    try:
        if action_type == "LIEN" and _finacle_is_configured():
            finacle = FinacleService(
                api_url=settings.FINACLE_API_URL,
                client_id=settings.FINACLE_CLIENT_ID,
                client_secret=settings.FINACLE_CLIENT_SECRET,
            )
            provider_response = await finacle.mark_lien(
                account_id=str(action.get("account_id", "")),
                amount=float((metadata or {}).get("amount", 0.0)),
                reason=reason,
            )
            next_status = "ACCEPTED" if provider_response else "REJECTED"
        elif action_type == "FREEZE" and _finacle_is_configured():
            finacle = FinacleService(
                api_url=settings.FINACLE_API_URL,
                client_id=settings.FINACLE_CLIENT_ID,
                client_secret=settings.FINACLE_CLIENT_SECRET,
            )
            provider_response = await finacle.freeze_account(
                account_id=str(action.get("account_id", "")),
                reason=reason,
                case_id=str((metadata or {}).get("case_id", "")),
            )
            next_status = "ACCEPTED" if provider_response else "REJECTED"
        elif action_type == "HOLD" and _finacle_is_configured():
            finacle = FinacleService(
                api_url=settings.FINACLE_API_URL,
                client_id=settings.FINACLE_CLIENT_ID,
                client_secret=settings.FINACLE_CLIENT_SECRET,
            )
            provider_response = await finacle.hold_transaction(
                txn_id=str((metadata or {}).get("transaction_id", "")),
                reason=reason,
            )
            next_status = "ACCEPTED" if provider_response else "REJECTED"
        elif action_type == "NCRP_REPORT" and _ncrp_is_configured():
            ncrp = NCRPService(api_url=settings.NCRP_API_URL, api_key=settings.NCRP_API_KEY)
            provider_response = await ncrp.submit_complaint(
                {
                    "complaintId": action.get("reference_id"),
                    "accountId": action.get("account_id"),
                    "action": reason,
                    "evidence": (metadata or {}).get("evidence", {}),
                }
            )
            next_status = "SUBMITTED" if provider_response else "QUEUED"
    except Exception:
        next_status = "REJECTED"

    updated = await neo4j_service.update_enforcement_action_status(
        action_id=action_id,
        status=next_status,
        reviewed_by=user.user_id,
        review_notes=request.notes,
        metadata=_merge_metadata(
            action,
            {
                "provider_response": provider_response,
                "approved_by": user.user_id,
            },
        ),
    )
    return {
        "action_id": action_id,
        "status": next_status,
        "provider_response": provider_response,
        "action": updated,
    }


@router.post("/actions/{action_id}/reject")
async def reject_enforcement_action(
    action_id: str,
    request: EnforcementReviewRequest,
    user: User = Depends(require_permission("approve:enforcement")),
):
    """Reject pending maker-checker enforcement action."""
    action = await neo4j_service.get_enforcement_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Enforcement action not found")

    current_status = str(action.get("status", "")).upper()
    if current_status not in {"PENDING_APPROVAL", "PENDING"}:
        raise HTTPException(
            status_code=409,
            detail=f"Action cannot be rejected from status {current_status or 'UNKNOWN'}",
        )

    updated = await neo4j_service.update_enforcement_action_status(
        action_id=action_id,
        status="REJECTED",
        reviewed_by=user.user_id,
        review_notes=request.notes,
        metadata=_merge_metadata(action, {"rejected_by": user.user_id}),
    )

    return {
        "action_id": action_id,
        "status": "REJECTED",
        "action": updated,
    }


@router.post("/lien")
async def mark_lien(
    request: LienRequest, user: User = Depends(require_permission("write:enforcement"))
):
    """Mark lien on account via Finacle API."""
    if not request.accountId:
        raise HTTPException(status_code=400, detail="accountId is required")

    action_id = f"LIEN-{uuid4().hex[:12].upper()}"
    response_status = "PENDING_APPROVAL" if request.requiresMakerChecker else "ACCEPTED"
    provider_response = {}

    if not request.requiresMakerChecker and _finacle_is_configured():
        try:
            finacle = FinacleService(
                api_url=settings.FINACLE_API_URL,
                client_id=settings.FINACLE_CLIENT_ID,
                client_secret=settings.FINACLE_CLIENT_SECRET,
            )
            provider_response = await finacle.mark_lien(
                account_id=request.accountId,
                amount=request.amount,
                reason=request.reason,
            )
            response_status = "ACCEPTED" if provider_response else "REJECTED"
        except Exception:
            response_status = "REJECTED"

    try:
        await neo4j_service.create_enforcement_action(
            action_id=action_id,
            action_type="LIEN",
            account_id=request.accountId,
            reason=request.reason,
            initiated_by=user.user_id,
            status=response_status,
            reference_id=action_id,
            metadata={
                "alert_id": request.alertId,
                "amount": request.amount,
                "requires_maker_checker": request.requiresMakerChecker,
                "initiated_by": request.initiatedBy,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist lien action: {exc}",
        ) from exc

    return {
        "accountId": request.accountId,
        "lienId": action_id,
        "status": response_status,
        "amount": request.amount,
        "reason": request.reason,
        "providerResponse": provider_response,
    }


@router.post("/freeze")
async def freeze_account(
    request: FreezeRequest,
    user: User = Depends(require_permission("write:enforcement")),
):
    """Freeze account via Finacle API."""
    if not request.accountId:
        raise HTTPException(status_code=400, detail="accountId is required")

    action_id = f"FRZ-{uuid4().hex[:12].upper()}"
    response_status = "PENDING_APPROVAL" if request.requiresMakerChecker else "ACCEPTED"
    provider_response = {}

    if not request.requiresMakerChecker and _finacle_is_configured():
        try:
            finacle = FinacleService(
                api_url=settings.FINACLE_API_URL,
                client_id=settings.FINACLE_CLIENT_ID,
                client_secret=settings.FINACLE_CLIENT_SECRET,
            )
            provider_response = await finacle.freeze_account(
                account_id=request.accountId,
                reason=request.reason,
                case_id=request.caseId,
            )
            response_status = "ACCEPTED" if provider_response else "REJECTED"
        except Exception:
            response_status = "REJECTED"

    try:
        await neo4j_service.create_enforcement_action(
            action_id=action_id,
            action_type="FREEZE",
            account_id=request.accountId,
            reason=request.reason,
            initiated_by=user.user_id,
            status=response_status,
            reference_id=action_id,
            metadata={
                "case_id": request.caseId,
                "requires_maker_checker": request.requiresMakerChecker,
                "initiated_by": request.initiatedBy,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist freeze action: {exc}",
        ) from exc

    return {
        "accountId": request.accountId,
        "freezeId": action_id,
        "status": response_status,
        "reason": request.reason,
        "caseId": request.caseId,
        "providerResponse": provider_response,
    }


@router.post("/hold")
async def hold_transaction(
    request: HoldRequest,
    user: User = Depends(require_permission("write:enforcement")),
):
    """Hold a transaction via Finacle API."""
    if not request.transactionId:
        raise HTTPException(status_code=400, detail="transactionId is required")

    action_id = f"HOLD-{uuid4().hex[:12].upper()}"
    response_status = "PENDING_APPROVAL" if request.requiresMakerChecker else "ACCEPTED"
    provider_response = {}

    if not request.requiresMakerChecker and _finacle_is_configured():
        try:
            finacle = FinacleService(
                api_url=settings.FINACLE_API_URL,
                client_id=settings.FINACLE_CLIENT_ID,
                client_secret=settings.FINACLE_CLIENT_SECRET,
            )
            provider_response = await finacle.hold_transaction(
                txn_id=request.transactionId,
                reason=request.reason,
            )
            response_status = "ACCEPTED" if provider_response else "REJECTED"
        except Exception:
            response_status = "REJECTED"

    try:
        await neo4j_service.create_enforcement_action(
            action_id=action_id,
            action_type="HOLD",
            account_id="",
            reason=request.reason,
            initiated_by=user.user_id,
            status=response_status,
            reference_id=action_id,
            metadata={
                "transaction_id": request.transactionId,
                "requires_maker_checker": request.requiresMakerChecker,
                "initiated_by": request.initiatedBy,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist hold action: {exc}",
        ) from exc

    return {
        "transactionId": request.transactionId,
        "holdId": action_id,
        "status": response_status,
        "reason": request.reason,
        "providerResponse": provider_response,
    }


@router.post("/ncrp-report")
async def submit_ncrp_report(
    request: NCRPReportRequest,
    user: User = Depends(require_permission("write:enforcement")),
):
    """Submit NCRP/I4C report for auto-lien and freeze."""
    if not request.complaintId or not request.accountId:
        raise HTTPException(status_code=400, detail="complaintId and accountId are required")

    response_status = "submitted-demo"
    provider_response = {}

    if _ncrp_is_configured():
        try:
            ncrp = NCRPService(api_url=settings.NCRP_API_URL, api_key=settings.NCRP_API_KEY)
            provider_response = await ncrp.submit_complaint(
                {
                    "complaintId": request.complaintId,
                    "accountId": request.accountId,
                    "action": request.action,
                    "evidence": request.evidence,
                }
            )
            response_status = "submitted" if provider_response else "queued"
        except Exception:
            response_status = "queued"

    try:
        await neo4j_service.create_enforcement_action(
            action_id=f"NCRP-{request.complaintId}",
            action_type="NCRP_REPORT",
            account_id=request.accountId,
            reason=request.action,
            initiated_by=user.user_id,
            status=response_status.upper(),
            reference_id=request.complaintId,
            metadata={"evidence": request.evidence},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist NCRP action: {exc}",
        ) from exc

    return {
        "complaintId": request.complaintId,
        "accountId": request.accountId,
        "status": response_status,
        "action": request.action,
        "providerResponse": provider_response,
    }
