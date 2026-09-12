"""
Verification router — used by FPO managers to verify farmer data
Farmers can view their own verifications.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from backend.database import get_db
from backend.models import Verification, Farmer, User, UserRole, VerificationStatus
from backend.schemas import VerificationCreate, VerificationUpdate, VerificationResponse
from backend.auth.dependencies import get_current_user
from backend.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
def create_verification(
    verification: VerificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a verification request. FPO managers or farmers can initiate."""
    farmer = db.query(Farmer).filter(Farmer.id == verification.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    db_verification = Verification(
        farmer_id=verification.farmer_id,
        verification_type=verification.verification_type,
        record_type=verification.record_type,
        record_id=verification.record_id,
        notes=verification.notes,
        requested_by=current_user.email,
        status=VerificationStatus.PENDING,
    )
    db.add(db_verification)
    db.commit()
    db.refresh(db_verification)
    logger.info(f"Verification created: {db_verification.id}")
    return db_verification


@router.get("/", response_model=List[VerificationResponse])
def list_verifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    farmer_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    verification_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List verifications. Farmers see only their own."""
    query = db.query(Verification)

    if current_user.role == UserRole.FARMER:
        if current_user.farmer_profile:
            query = query.filter(Verification.farmer_id == current_user.farmer_profile.id)
        else:
            return []
    elif farmer_id:
        query = query.filter(Verification.farmer_id == farmer_id)

    if status_filter:
        query = query.filter(Verification.status == status_filter)
    if verification_type:
        query = query.filter(Verification.verification_type == verification_type)

    return query.offset(skip).limit(limit).all()


@router.get("/{verification_id}", response_model=VerificationResponse)
def get_verification(
    verification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a verification by ID."""
    verification = db.query(Verification).filter(Verification.id == verification_id).first()
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    if current_user.role == UserRole.FARMER:
        if not current_user.farmer_profile or verification.farmer_id != current_user.farmer_profile.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return verification


@router.put("/{verification_id}", response_model=VerificationResponse)
def update_verification(
    verification_id: int,
    verification_update: VerificationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a verification status. FPO managers and admins only."""
    if current_user.role == UserRole.FARMER:
        raise HTTPException(status_code=403, detail="Farmers cannot update verification status")

    db_verification = db.query(Verification).filter(Verification.id == verification_id).first()
    if not db_verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    update_data = verification_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_verification, field, value)

    if verification_update.status in [VerificationStatus.VERIFIED, VerificationStatus.REJECTED]:
        db_verification.verification_date = datetime.utcnow()
        db_verification.verified_by = current_user.email

    db.commit()
    db.refresh(db_verification)
    logger.info(f"Verification updated: {verification_id} by {current_user.email}")
    return db_verification
