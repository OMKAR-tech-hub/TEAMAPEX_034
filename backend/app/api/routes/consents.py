import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.consent_log import ConsentLog
from app.models.farmer import Farmer
from app.models.user import Role, User
from app.schemas.consent import ConsentCreate, ConsentResponse, ConsentUpdate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/grant", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
def grant_consent(
    payload: ConsentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != Role.FARMER.value:
        raise HTTPException(status_code=403, detail="Only farmers can grant consent")
    if user.farmer_id is None:
        raise HTTPException(status_code=409, detail="Farmer profile is not linked to this account")

    bank = db.query(User).filter(User.id == payload.bank_user_id).first()
    if bank is None or bank.role != Role.BANK.value:
        raise HTTPException(status_code=400, detail="Invalid bank account")

    active = (
        db.query(ConsentLog)
        .filter(
            ConsentLog.farmer_id == user.farmer_id,
            ConsentLog.bank_user_id == payload.bank_user_id,
            ConsentLog.granted.is_(True),
        )
        .count()
    )
    if active >= settings.MAX_CONSENT_GRANTS:
        raise HTTPException(status_code=400, detail="Consent grant limit reached for this bank")

    consent = ConsentLog(
        farmer_id=user.farmer_id,
        bank_user_id=payload.bank_user_id,
        bank_name=bank.name,
        attributes=payload.attributes,
        masked_attributes=payload.masked_attributes,
        expires_at=payload.expires_at,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    logger.info(f"Consent {consent.id} granted by farmer {user.farmer_id} to bank {bank.name}")
    return consent


@router.get("", response_model=list[ConsentResponse])
def list_consents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == Role.FARMER.value:
        query = db.query(ConsentLog).filter(ConsentLog.farmer_id == user.farmer_id)
    elif user.role == Role.BANK.value:
        query = db.query(ConsentLog).filter(ConsentLog.bank_user_id == user.id)
    else:
        raise HTTPException(status_code=403, detail="Only farmers and banks can list consents")
    return query.order_by(ConsentLog.id.desc()).all()


@router.put("/{consent_id}", response_model=ConsentResponse)
def update_consent(
    consent_id: int,
    payload: ConsentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    consent = db.query(ConsentLog).filter(ConsentLog.id == consent_id).first()
    if consent is None:
        raise HTTPException(status_code=404, detail="Consent not found")

    if user.role == Role.FARMER.value:
        if consent.farmer_id != user.farmer_id:
            raise HTTPException(status_code=403, detail="Not your consent grant")
    elif user.role == Role.BANK.value:
        if consent.bank_user_id != user.id:
            raise HTTPException(status_code=403, detail="Not your consent grant")
    else:
        raise HTTPException(status_code=403, detail="Only farmers and banks can modify consent")

    consent.granted = payload.granted
    if payload.granted:
        consent.granted_at = datetime.utcnow()
        consent.revoked_at = None
    else:
        consent.revoked_at = datetime.utcnow()

    db.commit()
    db.refresh(consent)
    logger.info(f"Consent {consent.id} {'granted' if payload.granted else 'revoked'}")
    return consent


@router.delete("/{consent_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_consent(
    consent_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    consent = db.query(ConsentLog).filter(ConsentLog.id == consent_id).first()
    if consent is None:
        raise HTTPException(status_code=404, detail="Consent not found")
    if user.role == Role.FARMER.value and consent.farmer_id != user.farmer_id:
        raise HTTPException(status_code=403, detail="Not your consent grant")
    if user.role == Role.BANK.value and consent.bank_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your consent grant")
    if user.role not in (Role.FARMER.value, Role.BANK.value, Role.FPO.value):
        raise HTTPException(status_code=403, detail="Not permitted")

    consent.granted = False
    consent.revoked_at = datetime.utcnow()
    db.commit()
    return None


@router.post("/revoke", response_model=dict)
def revoke_consent_post(
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cid = payload.get("consent_id") or payload.get("id")
    if cid is None:
        raise HTTPException(status_code=400, detail="consent_id is required")
    consent = db.query(ConsentLog).filter(ConsentLog.id == int(cid)).first()
    if consent is None:
        raise HTTPException(status_code=404, detail="Consent not found")
    if user.role == Role.FARMER.value and consent.farmer_id != user.farmer_id:
        raise HTTPException(status_code=403, detail="Not your consent grant")
    if user.role == Role.BANK.value and consent.bank_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your consent grant")

    consent.granted = False
    consent.revoked_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "message": f"Consent {consent.id} revoked successfully"}