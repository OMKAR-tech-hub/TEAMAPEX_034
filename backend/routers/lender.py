"""
Lender portal router.
All farmer data access requires active consent.
Lender makes the final credit decision — KisanSetu provides the assessment.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from backend.database import get_db
from backend.models import (
    Lender, Farmer, Consent, CreditApplication, TrustPassport,
    User, UserRole, ApplicationStatus, DataAccessLog
)
from backend.schemas import (
    LenderResponse, CreditApplicationResponse, CreditApplicationUpdate,
    TrustPassportResponse,
)
from backend.auth.dependencies import get_current_user, get_lender_profile
from backend.services.passport_engine import generate_trust_passport
from backend.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=LenderResponse)
def get_lender_profile_endpoint(
    lender: Lender = Depends(get_lender_profile),
):
    return lender


@router.get("/consented-farmers")
def list_consented_farmers(
    lender: Lender = Depends(get_lender_profile),
    db: Session = Depends(get_db),
):
    """List farmers who have granted active consent to this lender."""
    consents = db.query(Consent).filter(
        Consent.lender_id == lender.id,
        Consent.is_active == True,
    ).all()
    result = []
    for c in consents:
        farmer = db.query(Farmer).filter(Farmer.id == c.farmer_id).first()
        if farmer:
            result.append({
                "farmer_id": farmer.id,
                "farmer_name": farmer.name,
                "village": farmer.village,
                "district": farmer.district,
                "state": farmer.state,
                "consent_id": c.id,
                "data_fields_granted": c.data_fields_granted,
                "granted_at": c.granted_at,
                "expires_at": c.expires_at,
            })
    return result


@router.get("/farmers/{farmer_id}/passport", response_model=TrustPassportResponse)
def get_farmer_passport_for_lender(
    farmer_id: int,
    lender: Lender = Depends(get_lender_profile),
    db: Session = Depends(get_db),
):
    """Get farmer's Trust Passport — requires active farmer consent."""
    consent = db.query(Consent).filter(
        Consent.farmer_id == farmer_id,
        Consent.lender_id == lender.id,
        Consent.is_active == True,
    ).first()
    if not consent:
        raise HTTPException(
            403,
            "Farmer has not granted you consent to view their passport. "
            "Request consent first and wait for farmer approval."
        )

    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(404, "Farmer not found")

    passport = db.query(TrustPassport).filter(TrustPassport.farmer_id == farmer_id).first()
    if not passport:
        passport = generate_trust_passport(farmer, db)

    # Log access
    log = DataAccessLog(
        farmer_id=farmer_id,
        consent_id=consent.id,
        accessor_user_id=lender.user_id,
        accessor_role="lender",
        accessor_name=lender.organization_name,
        fields_accessed=consent.data_fields_granted,
        purpose=consent.purpose or "credit assessment",
        accessed_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()

    return passport


@router.get("/applications", response_model=List[CreditApplicationResponse])
def list_lender_applications(
    status_filter: Optional[str] = Query(None, alias="status"),
    lender: Lender = Depends(get_lender_profile),
    db: Session = Depends(get_db),
):
    """List all credit applications assigned to this lender."""
    q = db.query(CreditApplication).filter(
        CreditApplication.lender_id == lender.id
    )
    if status_filter:
        q = q.filter(CreditApplication.status == status_filter)
    return q.order_by(CreditApplication.application_date.desc()).all()


@router.get("/applications/all")
def list_all_pending_applications(
    lender: Lender = Depends(get_lender_profile),
    db: Session = Depends(get_db),
):
    """List all pending unassigned applications (lender can pick up)."""
    apps = db.query(CreditApplication).filter(
        CreditApplication.status == ApplicationStatus.PENDING,
        CreditApplication.lender_id == None,
    ).all()
    return apps


@router.post("/applications/{application_id}/decision", response_model=CreditApplicationResponse)
def make_credit_decision(
    application_id: int,
    decision: CreditApplicationUpdate,
    lender: Lender = Depends(get_lender_profile),
    db: Session = Depends(get_db),
):
    """
    Lender records their credit decision.
    IMPORTANT: This is the LENDER's decision. KisanSetu provides assessment only.
    """
    app = db.query(CreditApplication).filter(CreditApplication.id == application_id).first()
    if not app:
        raise HTTPException(404, "Application not found")

    if app.lender_id and app.lender_id != lender.id:
        raise HTTPException(403, "This application belongs to another lender")

    if decision.status in [ApplicationStatus.APPROVED, ApplicationStatus.REJECTED]:
        app.lender_id = lender.id
        app.decision_date = datetime.utcnow()

    for k, v in decision.model_dump(exclude_unset=True).items():
        setattr(app, k, v)

    db.commit()
    db.refresh(app)
    logger.info(f"Lender {lender.id} decision on application {application_id}: {decision.status}")
    return app
