import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles, resolve_farmer
from app.core.database import get_db
from app.models.credit_profile import CreditProfile
from app.models.farmer import Farmer
from app.models.loan import DisbursementTranche, LoanApplication, RiskEvent
from app.models.user import Role, User
from app.schemas.loan import (
    LoanCreateRequest,
    RiskEventCreateRequest,
    RiskEventResponse,
    TrancheReleaseRequest,
    WalletResponse,
)
from app.services.loan_service import (
    approve_loan,
    create_loan,
    declare_risk_event,
    loan_to_dict,
    release_tranche,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_loan(db: Session, loan_id: int) -> LoanApplication:
    loan = db.query(LoanApplication).filter(LoanApplication.id == loan_id).first()
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    return loan


@router.post("", response_model=dict)
def create_loan_request(
    payload: LoanCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role in ("fpo", "bank"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a farmer initiates a loan request in the demo",
        )
    farmer = None
    if user.role == Role.FARMER.value and user.farmer_id:
        farmer = db.query(Farmer).filter(Farmer.id == user.farmer_id).first()
    if farmer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer not found")

    if payload.credit_profile_id:
        profile = db.query(CreditProfile).filter(CreditProfile.id == payload.credit_profile_id).first()
    else:
        profile = (
            db.query(CreditProfile)
            .filter(CreditProfile.farmer_id == farmer.id)
            .order_by(CreditProfile.id.desc())
            .first()
        )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No credit profile yet - run /underwrite/evaluate first",
        )
    if payload.principal > profile.safe_credit_limit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Principal exceeds safe credit limit {profile.safe_credit_limit}",
        )

    loan = create_loan(
        db,
        farmer,
        profile,
        payload.principal,
        payload.tenure_months,
        payload.annual_interest_rate,
        payload.origination_fee_rate,
        payload.purpose_category,
        payload.purpose_note,
    )
    logger.info(f"Farmer {farmer.farmer_id} requested loan {loan.application_uid} INR {loan.principal}")
    return loan_to_dict(db, loan)


@router.get("", response_model=list[dict])
def list_loans(
    farmer_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(LoanApplication).order_by(LoanApplication.id.desc())
    if user.role == Role.FARMER.value:
        if user.farmer_id is None:
            return []
        q = q.filter(LoanApplication.farmer_id == user.farmer_id)
    elif user.role == Role.FPO.value:
        from app.models.farmer import Farmer

        member_names = [user.name, user.username]
        q = q.filter(LoanApplication.farmer.has(Farmer.fpo_membership.in_(member_names)))
    elif farmer_id:
        farmer = resolve_farmer(db, farmer_id)
        q = q.filter(LoanApplication.farmer_id == farmer.id)
    return [loan_to_dict(db, loan) for loan in q.all()]


@router.get("/{loan_id}", response_model=dict)
def get_loan(
    loan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = _get_loan(db, loan_id)
    if user.role == Role.FARMER.value and loan.farmer_id != user.farmer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your loan")
    return loan_to_dict(db, loan)


@router.post("/{loan_id}/approve", response_model=dict)
def approve_loan_request(
    loan_id: int,
    user: User = Depends(require_roles(Role.BANK)),
    db: Session = Depends(get_db),
):
    loan = _get_loan(db, loan_id)
    loan = approve_loan(db, loan, by=user)
    logger.info(f"Bank {user.name} approved loan {loan.application_uid}")
    return loan_to_dict(db, loan)


@router.post("/{loan_id}/release-tranche", response_model=dict)
def release_disbursement_tranche(
    loan_id: int,
    payload: TrancheReleaseRequest,
    user: User = Depends(require_roles(Role.BANK)),
    db: Session = Depends(get_db),
):
    loan = _get_loan(db, loan_id)
    tranche = (
        db.query(DisbursementTranche).filter(DisbursementTranche.id == payload.tranche_id).first()
    )
    if tranche is None or tranche.loan_application_id != loan.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tranche not found")
    try:
        release_tranche(db, loan, tranche)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    logger.info(f"Bank {user.name} released {tranche.label} INR {tranche.amount} on {loan.application_uid}")
    return loan_to_dict(db, loan)


@router.post("/{loan_id}/risk-events", response_model=RiskEventResponse)
def declare_event(
    loan_id: int,
    payload: RiskEventCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in (Role.FPO.value, Role.BANK.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FPO or bank declares risk events")
    loan = _get_loan(db, loan_id)
    if payload.loan_id != loan.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="loan_id mismatch")
    event = declare_risk_event(db, loan, payload.event_type, payload.severity, payload.loss_ratio)
    recalibrated = None
    if loan.credit_profile_id:
        profile = db.query(CreditProfile).filter(CreditProfile.id == loan.credit_profile_id).first()
        recalibrated = profile.safe_credit_limit if profile else None
    logger.info(f"{user.name} declared {event.event_type}/{event.severity} on {loan.application_uid}")
    return RiskEventResponse(
        id=event.id,
        loan_application_id=loan.id,
        event_type=event.event_type,
        severity=event.severity,
        loss_ratio=event.loss_ratio,
        action=event.action,
        declared_at=event.declared_at,
        recalibrated_safe_credit_limit=recalibrated,
        farmer_charged_fees=0.0,
    )


@router.get("/{loan_id}/risk-events", response_model=list[dict])
def list_risk_events(
    loan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = _get_loan(db, loan_id)
    if user.role == Role.FARMER.value and loan.farmer_id != user.farmer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your loan")
    events = (
        db.query(RiskEvent)
        .filter(RiskEvent.loan_application_id == loan.id)
        .order_by(RiskEvent.id.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "severity": e.severity,
            "loss_ratio": e.loss_ratio,
            "action": e.action,
            "declared_at": e.declared_at.isoformat() if e.declared_at else None,
        }
        for e in events
    ]


@router.get("/wallet/me", response_model=WalletResponse)
def my_wallet(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != Role.FPO.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only FPO wallets")
    tally = 0.0
    from app.models.farmer import Farmer
    from app.models.loan import Settlement

    total_fpo = (
        db.query(Settlement.fpo_facilitation_amt)
        .join(LoanApplication, Settlement.loan_application_id == LoanApplication.id)
        .join(Farmer, LoanApplication.farmer_id == Farmer.id)
        .filter((Farmer.fpo_membership == user.name) | (Farmer.fpo_membership == user.username))
        .all()
    )
    tally = round(sum(x[0] for x in total_fpo), 2)
    return WalletResponse(
        user_id=user.id,
        role=user.role,
        wallet_balance=user.wallet_balance,
        facilitation_tally=tally,
    )