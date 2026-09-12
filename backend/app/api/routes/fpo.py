import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.farmer import Farmer
from app.models.fpo_verification import FPOVerification
from app.models.user import Role, User
from app.api.deps import require_roles
from app.schemas.fpo import VerificationCreate, VerificationResponse, VerificationUpdate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/verifications", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
def submit_verification(
    payload: VerificationCreate,
    user: User = Depends(require_roles(Role.FPO)),
    db: Session = Depends(get_db),
):
    try:
        farmer = db.query(Farmer).filter(Farmer.id == payload.farmer_id).first()
        if farmer is None:
            raise HTTPException(status_code=404, detail="Farmer not found")

        verification = FPOVerification(
            farmer_id=payload.farmer_id,
            fpo_name=user.name,
            verification_status=payload.verification_status,
            member_integrity_flag=payload.member_integrity_flag,
            verified_by=user.name,
            notes=payload.notes,
            verification_date=(
                datetime.utcnow() if payload.verification_status != "pending" else None
            ),
        )
        db.add(verification)
        db.commit()
        db.refresh(verification)
        logger.info(f"FPO {user.name} submitted verification {verification.id}")
        return verification
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Verification submit failed: {exc}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to submit verification")


@router.get("/verifications", response_model=list[VerificationResponse])
def list_verifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    farmer_id: int = Query(None),
    verification_status: str = Query(None, pattern="^(pending|verified|rejected)$"),
    user: User = Depends(require_roles(Role.FPO, Role.BANK, Role.FARMER)),
    db: Session = Depends(get_db),
):
    query = db.query(FPOVerification)
    if farmer_id is not None:
        query = query.filter(FPOVerification.farmer_id == farmer_id)
    if verification_status:
        query = query.filter(FPOVerification.verification_status == verification_status)
    return query.order_by(FPOVerification.id.desc()).offset(skip).limit(limit).all()


@router.put("/verifications/{verification_id}", response_model=VerificationResponse)
def update_verification(
    verification_id: int,
    payload: VerificationUpdate,
    user: User = Depends(require_roles(Role.FPO)),
    db: Session = Depends(get_db),
):
    verification = db.query(FPOVerification).filter(FPOVerification.id == verification_id).first()
    if verification is None:
        raise HTTPException(status_code=404, detail="Verification not found")

    data = payload.model_dump(exclude_unset=True)
    if "verification_status" in data:
        if data["verification_status"] != "pending":
            verification.verification_date = datetime.utcnow()
            verification.verified_by = user.name
        else:
            verification.verification_date = None

    for field, value in data.items():
        setattr(verification, field, value)

    db.commit()
    db.refresh(verification)
    return verification