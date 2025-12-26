"""ML and collection intelligence endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.loan import Loan
from app.models.case import Case
from app.services.collection_intelligence import (
    calculate_priority_score,
    get_collection_strategy,
    calculate_simple_risk_score,
    get_bucket_from_dpd,
)

router = APIRouter()


class PriorityRequest(BaseModel):
    overdue_amount: Decimal
    principal_amount: Decimal
    dpd: int
    risk_score: Optional[float] = None


class StrategyRequest(BaseModel):
    dpd: int
    risk_level: str = "Medium"


class RiskRequest(BaseModel):
    dpd: int
    overdue_amount: Decimal
    principal_amount: Decimal
    total_attempts: int = 0
    promises_broken: int = 0


@router.post("/priority/calculate")
async def calculate_priority(
    request: PriorityRequest,
    current_user: User = Depends(get_current_user),
):
    """Calculate collection priority score for given loan data."""
    result = calculate_priority_score(
        overdue_amount=request.overdue_amount,
        principal_amount=request.principal_amount,
        dpd=request.dpd,
        risk_score=request.risk_score,
    )
    return result


@router.post("/strategy/recommend")
async def recommend_strategy(
    request: StrategyRequest,
    current_user: User = Depends(get_current_user),
):
    """Get recommended collection strategy based on DPD."""
    result = get_collection_strategy(
        dpd=request.dpd,
        risk_level=request.risk_level,
    )
    return result


@router.post("/risk/assess")
async def assess_risk(
    request: RiskRequest,
    current_user: User = Depends(get_current_user),
):
    """Calculate simple risk score (heuristic-based)."""
    result = calculate_simple_risk_score(
        dpd=request.dpd,
        overdue_amount=request.overdue_amount,
        principal_amount=request.principal_amount,
        total_attempts=request.total_attempts,
        promises_broken=request.promises_broken,
    )
    return result


@router.get("/loans/{loan_id}/intelligence")
async def get_loan_intelligence(
    loan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full intelligence report for a loan."""
    result = await db.execute(
        select(Loan).where(
            Loan.id == loan_id,
            Loan.organization_id == current_user.organization_id,
        )
    )
    loan = result.scalar_one_or_none()

    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found",
        )

    # Get associated case for attempt data
    case_result = await db.execute(
        select(Case).where(Case.loan_id == loan_id)
    )
    case = case_result.scalar_one_or_none()

    total_attempts = case.total_attempts if case else 0
    promises_broken = 0  # TODO: Track this in case model

    # Calculate all intelligence
    risk = calculate_simple_risk_score(
        dpd=loan.dpd or 0,
        overdue_amount=loan.overdue_amount or Decimal(0),
        principal_amount=loan.principal_amount or Decimal(1),
        total_attempts=total_attempts,
        promises_broken=promises_broken,
    )

    priority = calculate_priority_score(
        overdue_amount=loan.overdue_amount or Decimal(0),
        principal_amount=loan.principal_amount or Decimal(1),
        dpd=loan.dpd or 0,
        risk_score=risk["score"],
    )

    strategy = get_collection_strategy(
        dpd=loan.dpd or 0,
        risk_level=risk["risk_level"],
    )

    return {
        "loan_id": str(loan.id),
        "loan_account_number": loan.loan_account_number,
        "dpd": loan.dpd,
        "bucket": get_bucket_from_dpd(loan.dpd or 0),
        "overdue_amount": float(loan.overdue_amount or 0),
        "risk": risk,
        "priority": priority,
        "strategy": strategy,
    }


@router.post("/cases/{case_id}/recalculate")
async def recalculate_case_priority(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recalculate and update priority for a case."""
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.organization_id == current_user.organization_id,
        )
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    # Get loan data
    loan_result = await db.execute(
        select(Loan).where(Loan.id == case.loan_id)
    )
    loan = loan_result.scalar_one_or_none()

    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found for case",
        )

    # Calculate risk
    risk = calculate_simple_risk_score(
        dpd=loan.dpd or 0,
        overdue_amount=loan.overdue_amount or Decimal(0),
        principal_amount=loan.principal_amount or Decimal(1),
        total_attempts=case.total_attempts or 0,
        promises_broken=0,
    )

    # Calculate priority
    priority = calculate_priority_score(
        overdue_amount=loan.overdue_amount or Decimal(0),
        principal_amount=loan.principal_amount or Decimal(1),
        dpd=loan.dpd or 0,
        risk_score=risk["score"],
    )

    # Update case and loan
    case.priority = priority["priority_level"]
    if case.extra_data is None:
        case.extra_data = {}
    case.extra_data["ml_priority"] = priority

    loan.risk_score = risk

    await db.commit()

    return {
        "case_id": str(case.id),
        "updated_priority": priority["priority_level"],
        "priority_details": priority,
        "risk_details": risk,
    }


@router.post("/batch/recalculate-priorities")
async def batch_recalculate_priorities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recalculate priorities for all active cases in organization."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can run batch operations",
        )

    # Get all active cases with loans
    result = await db.execute(
        select(Case, Loan)
        .join(Loan, Case.loan_id == Loan.id)
        .where(
            Case.organization_id == current_user.organization_id,
            Case.status.in_(["open", "in_progress", "pending"]),
        )
    )

    updated = 0
    for case, loan in result.all():
        risk = calculate_simple_risk_score(
            dpd=loan.dpd or 0,
            overdue_amount=loan.overdue_amount or Decimal(0),
            principal_amount=loan.principal_amount or Decimal(1),
            total_attempts=case.total_attempts or 0,
            promises_broken=0,
        )

        priority = calculate_priority_score(
            overdue_amount=loan.overdue_amount or Decimal(0),
            principal_amount=loan.principal_amount or Decimal(1),
            dpd=loan.dpd or 0,
            risk_score=risk["score"],
        )

        case.priority = priority["priority_level"]
        if case.extra_data is None:
            case.extra_data = {}
        case.extra_data["ml_priority"] = priority
        loan.risk_score = risk
        updated += 1

    await db.commit()

    return {
        "status": "success",
        "cases_updated": updated,
    }
