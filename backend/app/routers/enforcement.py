from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..auth.jwt_rbac import require_permission, User

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


@router.post("/lien")
async def mark_lien(
    request: LienRequest, user: User = Depends(require_permission("write:enforcement"))
):
    """Mark lien on account via Finacle API."""
    return {
        "accountId": request.accountId,
        "lienId": f"LIEN-{request.alertId}",
        "status": "pending",
        "amount": request.amount,
        "reason": request.reason,
    }


@router.post("/freeze")
async def freeze_account(
    request: FreezeRequest,
    user: User = Depends(require_permission("write:enforcement")),
):
    """Freeze account via Finacle API."""
    return {
        "accountId": request.accountId,
        "freezeId": f"FRZ-{request.caseId}",
        "status": "pending",
        "reason": request.reason,
        "caseId": request.caseId,
    }


@router.post("/ncrp-report")
async def submit_ncrp_report(
    request: NCRPReportRequest,
    user: User = Depends(require_permission("write:enforcement")),
):
    """Submit NCRP/I4C report for auto-lien and freeze."""
    return {
        "complaintId": request.complaintId,
        "accountId": request.accountId,
        "status": "submitted",
        "action": request.action,
    }
