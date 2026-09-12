"""
Credit application router — auth-gated, role-enforced
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from backend.database import get_db
from backend.models import CreditApplication, Farmer, User, UserRole, ApplicationStatus, AuditLog
from backend.schemas import CreditApplicationCreate, CreditApplicationUpdate, CreditApplicationResponse
from backend.auth.dependencies import get_current_user, get_farmer_profile, require_role
from backend.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=CreditApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_credit_application(
    application: CreditApplicationCreate,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    """Create a new credit application. Farmer only — farmer_id comes from JWT."""
    db_application = CreditApplication(
        farmer_id=farmer.id,
        amount_requested=application.amount_requested,
        purpose=application.purpose,
        lender_type=application.lender_type,
        status=ApplicationStatus.PENDING,
    )
    db.add(db_application)
    audit = AuditLog(
        user_id=farmer.user_id,
        action="credit_application_created",
        resource_type="credit_application",
        details={"amount": application.amount_requested, "purpose": application.purpose},
    )
    db.add(audit)
    db.commit()
    db.refresh(db_application)
    logger.info(f"Credit application created: {db_application.id} farmer: {farmer.id}")
    return db_application


@router.get("/", response_model=List[CreditApplicationResponse])
def list_credit_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List credit applications.
    - Farmers see only their own.
    - Lenders/Admin see all (or can filter).
    """
    query = db.query(CreditApplication)

    if current_user.role == UserRole.FARMER:
        if not current_user.farmer_profile:
            return []
        query = query.filter(CreditApplication.farmer_id == current_user.farmer_profile.id)
    elif current_user.role == UserRole.LENDER:
        if current_user.lender_profile:
            query = query.filter(CreditApplication.lender_id == current_user.lender_profile.id)

    if status_filter:
        query = query.filter(CreditApplication.status == status_filter)

    return query.offset(skip).limit(limit).all()


@router.get("/{application_id}", response_model=CreditApplicationResponse)
def get_credit_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a credit application. Farmer can only see their own."""
    application = db.query(CreditApplication).filter(
        CreditApplication.id == application_id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Credit application not found")

    if current_user.role == UserRole.FARMER:
        if not current_user.farmer_profile or application.farmer_id != current_user.farmer_profile.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return application


@router.put("/{application_id}", response_model=CreditApplicationResponse)
def update_credit_application(
    application_id: int,
    application_update: CreditApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a credit application.
    - Farmers CANNOT approve/reject their own application.
    - Only lenders and admins can set approved/rejected status.
    """
    db_application = db.query(CreditApplication).filter(
        CreditApplication.id == application_id
    ).first()
    if not db_application:
        raise HTTPException(status_code=404, detail="Credit application not found")

    # Ownership check for farmers
    if current_user.role == UserRole.FARMER:
        if not current_user.farmer_profile or db_application.farmer_id != current_user.farmer_profile.id:
            raise HTTPException(status_code=403, detail="Access denied")
        # Farmers cannot change decision status
        if application_update.status in [ApplicationStatus.APPROVED, ApplicationStatus.REJECTED]:
            raise HTTPException(
                status_code=403,
                detail="Farmers cannot approve or reject their own application"
            )

    update_data = application_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_application, field, value)

    if application_update.status in [ApplicationStatus.APPROVED, ApplicationStatus.REJECTED]:
        db_application.decision_date = datetime.utcnow()
        audit = AuditLog(
            user_id=current_user.id,
            action="credit_decision",
            resource_type="credit_application",
            resource_id=application_id,
            details={"decision": application_update.status.value if application_update.status else None},
        )
        db.add(audit)

    db.commit()
    db.refresh(db_application)
    logger.info(f"Credit application updated: {application_id}")
    return db_application
