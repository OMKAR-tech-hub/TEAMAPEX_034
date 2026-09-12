"""
FPO management router — create FPO, manage members, verify records
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from backend.database import get_db
from backend.models import (
    FPO, FPOMembership, FPOManager, Farmer, User, UserRole,
    ProductionRecord, SalesRecord, Verification, VerificationStatus,
    MembershipStatus, AuditLog
)
from backend.schemas import (
    FPOCreate, FPOResponse, FPOMembershipCreate, FPOMembershipResponse,
    VerificationCreate, VerificationUpdate, VerificationResponse,
)
from backend.auth.dependencies import get_current_user, get_fpo_manager_profile
from backend.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# FPO CRUD (admin / public registration)
# ─────────────────────────────────────────────

@router.get("/", response_model=List[FPOResponse])
def list_fpos(db: Session = Depends(get_db)):
    """Public list of FPOs for registration."""
    return db.query(FPO).all()


@router.post("/", response_model=FPOResponse, status_code=201)
def create_fpo(
    fpo_in: FPOCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin can create FPOs."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(403, "Only admins can create FPOs")
    fpo = FPO(**fpo_in.model_dump())
    db.add(fpo)
    db.commit()
    db.refresh(fpo)
    return fpo


@router.get("/{fpo_id}", response_model=FPOResponse)
def get_fpo(fpo_id: int, db: Session = Depends(get_db)):
    fpo = db.query(FPO).filter(FPO.id == fpo_id).first()
    if not fpo:
        raise HTTPException(404, "FPO not found")
    return fpo


# ─────────────────────────────────────────────
# FPO MEMBERS
# ─────────────────────────────────────────────

@router.get("/my/members", response_model=List[FPOMembershipResponse])
def list_my_fpo_members(
    manager: FPOManager = Depends(get_fpo_manager_profile),
    db: Session = Depends(get_db),
):
    return db.query(FPOMembership).filter(
        FPOMembership.fpo_id == manager.fpo_id
    ).all()


@router.post("/my/members", response_model=FPOMembershipResponse, status_code=201)
def add_member(
    member_in: FPOMembershipCreate,
    manager: FPOManager = Depends(get_fpo_manager_profile),
    db: Session = Depends(get_db),
):
    """FPO manager adds a farmer as member."""
    farmer = db.query(Farmer).filter(Farmer.id == member_in.farmer_id).first()
    if not farmer:
        raise HTTPException(404, "Farmer not found")
    existing = db.query(FPOMembership).filter(
        FPOMembership.fpo_id == manager.fpo_id,
        FPOMembership.farmer_id == member_in.farmer_id
    ).first()
    if existing:
        raise HTTPException(400, "Farmer is already a member of this FPO")
    membership = FPOMembership(
        fpo_id=manager.fpo_id,
        farmer_id=member_in.farmer_id,
        membership_date=member_in.membership_date or datetime.utcnow(),
        membership_number=member_in.membership_number,
        status=MembershipStatus.ACTIVE,
        verified=True,
        verified_by=manager.name,
        verification_date=datetime.utcnow(),
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


# ─────────────────────────────────────────────
# FPO VERIFICATION
# ─────────────────────────────────────────────

@router.get("/my/verifications", response_model=List[VerificationResponse])
def list_fpo_verifications(
    status_filter: Optional[str] = Query(None, alias="status"),
    manager: FPOManager = Depends(get_fpo_manager_profile),
    db: Session = Depends(get_db),
):
    q = db.query(Verification).filter(Verification.fpo_id == manager.fpo_id)
    if status_filter:
        q = q.filter(Verification.status == status_filter)
    return q.all()


@router.post("/my/verify", response_model=VerificationResponse, status_code=201)
def verify_farmer_record(
    verification_in: VerificationCreate,
    manager: FPOManager = Depends(get_fpo_manager_profile),
    db: Session = Depends(get_db),
):
    """FPO manager creates a verification for a farmer record."""
    # Only members of this FPO
    membership = db.query(FPOMembership).filter(
        FPOMembership.fpo_id == manager.fpo_id,
        FPOMembership.farmer_id == verification_in.farmer_id
    ).first()
    if not membership:
        raise HTTPException(403, "Farmer is not a member of your FPO")

    db_v = Verification(
        farmer_id=verification_in.farmer_id,
        fpo_id=manager.fpo_id,
        verification_type=verification_in.verification_type,
        record_type=verification_in.record_type,
        record_id=verification_in.record_id,
        notes=verification_in.notes,
        requested_by=manager.name,
        status=VerificationStatus.PENDING,
    )
    db.add(db_v)
    db.commit()
    db.refresh(db_v)
    return db_v


@router.put("/my/verify/{verification_id}", response_model=VerificationResponse)
def update_fpo_verification(
    verification_id: int,
    update_in: VerificationUpdate,
    manager: FPOManager = Depends(get_fpo_manager_profile),
    db: Session = Depends(get_db),
):
    v = db.query(Verification).filter(
        Verification.id == verification_id,
        Verification.fpo_id == manager.fpo_id
    ).first()
    if not v:
        raise HTTPException(404, "Verification not found")

    for k, val in update_in.model_dump(exclude_unset=True).items():
        setattr(v, k, val)
    if update_in.status in [VerificationStatus.VERIFIED, VerificationStatus.REJECTED]:
        v.verified_by = manager.name
        v.verification_date = datetime.utcnow()
        # Update underlying record's fpo_verified flag
        if v.record_type == "production" and v.record_id:
            rec = db.query(ProductionRecord).filter(ProductionRecord.id == v.record_id).first()
            if rec:
                rec.fpo_verified = (update_in.status == VerificationStatus.VERIFIED)
                rec.verified_by = manager.name
        elif v.record_type == "sales" and v.record_id:
            rec = db.query(SalesRecord).filter(SalesRecord.id == v.record_id).first()
            if rec:
                rec.fpo_verified = (update_in.status == VerificationStatus.VERIFIED)
                rec.verified_by = manager.name

    db.commit()
    db.refresh(v)
    logger.info(f"Verification {verification_id} updated by FPO manager {manager.id}")
    return v
