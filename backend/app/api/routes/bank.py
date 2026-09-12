import csv
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles, resolve_farmer
from app.core.database import get_db
from app.models.consent_log import ConsentLog
from app.models.farmer import Farmer
from app.models.loan import LoanApplication
from app.models.trust_passport import TrustPassport
from app.models.user import Role, User
from app.schemas.consent import BankViewResponse
from app.services.bank_view import build_bank_view
from app.services.loan_service import loan_to_dict

router = APIRouter()
logger = logging.getLogger(__name__)


def _active_consent(db: Session, user: User, farmer: Farmer) -> ConsentLog:
    consent = (
        db.query(ConsentLog)
        .filter(
            ConsentLog.farmer_id == farmer.id,
            ConsentLog.bank_user_id == user.id,
            ConsentLog.granted.is_(True),
        )
        .order_by(ConsentLog.id.desc())
        .first()
    )
    if consent is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active consent grant from this farmer to your bank",
        )
    return consent


def _latest_passport(db: Session, farmer_id: int) -> TrustPassport:
    return (
        db.query(TrustPassport)
        .filter(TrustPassport.farmer_id == farmer_id)
        .order_by(TrustPassport.id.desc())
        .first()
    )


@router.get("/farmers", response_model=list[dict])
def list_consented_farmers(
    user: User = Depends(require_roles(Role.BANK)),
    db: Session = Depends(get_db),
):
    consents = (
        db.query(ConsentLog)
        .filter(ConsentLog.bank_user_id == user.id, ConsentLog.granted.is_(True))
        .order_by(ConsentLog.id.desc())
        .all()
    )
    result = []
    for consent in consents:
        farmer = db.query(Farmer).filter(Farmer.id == consent.farmer_id).first()
        if farmer is None:
            continue
        passport = _latest_passport(db, farmer.id)
        result.append(
            {
                "consent_id": consent.id,
                "farmer_id": farmer.farmer_id,
                "farmer_name": farmer.name,
                "village": farmer.village,
                "granted_at": consent.granted_at,
                "safe_credit_limit": passport.safe_credit_limit if passport else None,
                "credit_tier": passport.credit_tier if passport else None,
            }
        )
    return result


@router.get("/farmers/{farmer_id}/view", response_model=BankViewResponse)
def bank_view(
    farmer_id: str,
    user: User = Depends(require_roles(Role.BANK)),
    db: Session = Depends(get_db),
):
    farmer = resolve_farmer(db, farmer_id)
    consent = _active_consent(db, user, farmer)
    passport = _latest_passport(db, farmer.id)

    view = build_bank_view(farmer, consent, passport)
    logger.info(f"Bank {user.name} viewed farmer {farmer.farmer_id} under consent {consent.id}")
    return BankViewResponse(**view)


@router.get("/export/psl")
def export_psl_report(
    category: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    user: User = Depends(require_roles(Role.BANK)),
    db: Session = Depends(get_db),
):
    q = db.query(LoanApplication).filter(
        LoanApplication.psl_eligible.is_(True),
        LoanApplication.status.in_(["active", "disbursing", "repaid"]),
    )
    if category:
        q = q.filter(LoanApplication.psl_category.ilike(f"%{category}%"))
    if from_date:
        q = q.filter(LoanApplication.created_at >= from_date)
    if to_date:
        q = q.filter(LoanApplication.created_at <= f"{to_date} 23:59:59")

    rows = []
    for loan in q.order_by(LoanApplication.id.desc()).all():
        d = loan_to_dict(db, loan)
        rows.append(
            {
                "application_uid": loan.application_uid,
                "farmer_ref": loan.farmer.farmer_id if loan.farmer else "",
                "farmer_name": loan.farmer.name if loan.farmer else "",
                "psl_category": loan.psl_category,
                "status": loan.status,
                "principal_inr": loan.principal,
                "disbursed_inr": loan.amount_disbursed,
                "outstanding_inr": d["outstanding"],
                "repaid_inr": loan.amount_repaid,
                "interest_rate": loan.annual_interest_rate,
                "tenure_months": loan.tenure_months,
                "origination_fee_inr": round(loan.principal * loan.origination_fee_rate, 2),
                "psl_eligible": "yes",
            }
        )

    logger.info(f"Bank {user.name} exported PSL report: {len(rows)} loans")
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        buf.write("application_uid,farmer_ref,farmer_name,psl_category,status,principal_inr,disbursed_inr,outstanding_inr,repaid_inr,interest_rate,tenure_months,origination_fee_inr,psl_eligible\n")
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=psl_export.csv"},
    )