import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, resolve_farmer
from app.core.database import get_db
from app.models.trust_passport import TrustPassport
from app.models.user import User
from app.schemas.passport import ComputeRequest, ComputeResponse, TrustPassportResponse
from app.services.credit_engine import build_passport_record

router = APIRouter()
logger = logging.getLogger(__name__)


def _latest_passport(db: Session, farmer_id: int) -> TrustPassport:
    return (
        db.query(TrustPassport)
        .filter(TrustPassport.farmer_id == farmer_id)
        .order_by(TrustPassport.id.desc())
        .first()
    )


@router.post("/compute/{farmer_id}", response_model=ComputeResponse)
def compute_passport(
    farmer_id: str,
    payload: ComputeRequest = ComputeRequest(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_farmer = resolve_farmer(db, farmer_id)

    existing = _latest_passport(db, db_farmer.id)
    if existing is not None and not payload.force_recompute:
        existing.crop_season = db_farmer.crop_season
        db.commit()
        db.refresh(existing)
        return ComputeResponse(
            passport=TrustPassportResponse.model_validate(existing),
            inputs={"note": "returned existing passport; pass force_recompute=true to recalculate"},
        )

    record, inputs = build_passport_record(db, db_farmer.id)
    passport = TrustPassport(**record)
    db.add(passport)
    db.commit()
    db.refresh(passport)
    logger.info(f"Computed passport {passport.id} for farmer {db_farmer.farmer_id}")
    return ComputeResponse(
        passport=TrustPassportResponse.model_validate(passport),
        inputs=inputs,
    )


@router.get("/{farmer_id}", response_model=TrustPassportResponse)
def get_passport(
    farmer_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_farmer = resolve_farmer(db, farmer_id)
    passport = _latest_passport(db, db_farmer.id)
    if passport is None:
        raise HTTPException(status_code=404, detail="Passport not computed yet. Trigger the credit engine first.")
    return passport