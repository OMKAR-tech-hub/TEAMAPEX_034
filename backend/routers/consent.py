"""
Consent management router — farmer controls who can see their data.
"""
import hashlib, json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from backend.database import get_db
from backend.models import (
    Consent, DataAccessLog, Farmer, Lender, User, UserRole
)
from backend.schemas import (
    ConsentRequest, ConsentGrant, ConsentResponse, DataAccessLogResponse,
)
from backend.auth.dependencies import get_current_user, get_farmer_profile

router = APIRouter()
logger = logging.getLogger(__name__)


def _compute_log_hash(previous_hash: str, log_payload: dict) -> str:
    """SHA-256 hash chain: current = SHA256(prev_hash + canonical_payload)"""
    canonical = previous_hash + json.dumps(log_payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ─────────────────────────────────────────────
# LENDER: Request consent from farmer
# ─────────────────────────────────────────────

@router.post("/request", response_model=ConsentResponse, status_code=201)
def request_consent(
    consent_req: ConsentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lender requests consent from a farmer to view their data."""
    if current_user.role != UserRole.LENDER:
        raise HTTPException(403, "Only lenders can request consent")
    if not current_user.lender_profile:
        raise HTTPException(403, "Lender profile not found")

    farmer = db.query(Farmer).filter(Farmer.id == consent_req.farmer_id).first()
    if not farmer:
        raise HTTPException(404, "Farmer not found")

    # Check no existing active consent
    existing = db.query(Consent).filter(
        Consent.farmer_id == consent_req.farmer_id,
        Consent.lender_id == current_user.lender_profile.id,
        Consent.is_active == True,
    ).first()
    if existing:
        raise HTTPException(400, "An active consent already exists")

    consent = Consent(
        farmer_id=consent_req.farmer_id,
        lender_id=current_user.lender_profile.id,
        data_fields_granted=consent_req.data_fields_requested,
        purpose=consent_req.purpose,
        request_message=consent_req.request_message,
        is_active=False,  # pending farmer's approval
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    logger.info(f"Consent requested by lender {current_user.lender_profile.id} for farmer {consent_req.farmer_id}")
    return consent


# ─────────────────────────────────────────────
# FARMER: List pending consent requests
# ─────────────────────────────────────────────

@router.get("/pending", response_model=List[ConsentResponse])
def get_pending_consents(
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    """Farmer sees all pending (is_active=False, not revoked) consent requests."""
    return db.query(Consent).filter(
        Consent.farmer_id == farmer.id,
        Consent.is_active == False,
        Consent.revoked_at == None,
        Consent.granted_at == None,
    ).all()


@router.get("/", response_model=List[ConsentResponse])
def list_consents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all consents. Farmer sees own. Lender sees their requests."""
    if current_user.role == UserRole.FARMER and current_user.farmer_profile:
        return db.query(Consent).filter(Consent.farmer_id == current_user.farmer_profile.id).all()
    elif current_user.role == UserRole.LENDER and current_user.lender_profile:
        return db.query(Consent).filter(Consent.lender_id == current_user.lender_profile.id).all()
    elif current_user.role == UserRole.ADMIN:
        return db.query(Consent).all()
    return []


# ─────────────────────────────────────────────
# FARMER: Grant consent
# ─────────────────────────────────────────────

@router.post("/{consent_id}/grant", response_model=ConsentResponse)
def grant_consent(
    consent_id: int,
    grant: ConsentGrant,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    """Farmer grants a pending consent request, optionally limiting fields."""
    consent = db.query(Consent).filter(
        Consent.id == consent_id,
        Consent.farmer_id == farmer.id,
    ).first()
    if not consent:
        raise HTTPException(404, "Consent request not found")
    if consent.is_active:
        raise HTTPException(400, "Consent is already active")
    if consent.revoked_at:
        raise HTTPException(400, "Consent was revoked and cannot be re-granted")

    consent.data_fields_granted = grant.data_fields_granted
    consent.granted_at = datetime.utcnow()
    consent.expires_at = datetime.utcnow() + timedelta(days=grant.expires_days or 90)
    consent.is_active = True
    db.commit()
    db.refresh(consent)

    # Audit log with hash chain
    prev = db.query(DataAccessLog).filter(
        DataAccessLog.farmer_id == farmer.id
    ).order_by(DataAccessLog.id.desc()).first()
    prev_hash = prev.current_hash if prev and hasattr(prev, 'current_hash') else "GENESIS"
    payload = {
        "action": "consent_granted",
        "farmer_id": farmer.id,
        "consent_id": consent_id,
        "lender_id": consent.lender_id,
        "fields": grant.data_fields_granted,
        "ts": datetime.utcnow().isoformat(),
    }
    curr_hash = _compute_log_hash(prev_hash, payload)
    log = DataAccessLog(
        farmer_id=farmer.id,
        consent_id=consent_id,
        accessor_user_id=farmer.user_id,
        accessor_role="farmer",
        fields_accessed=grant.data_fields_granted,
        purpose="consent_granted",
        accessed_at=datetime.utcnow(),
        ip_address=None,
    )
    # Attach hashes if columns exist (they're in model via migration)
    if hasattr(log, 'previous_hash'):
        log.previous_hash = prev_hash
        log.current_hash = curr_hash
    db.add(log)
    db.commit()
    logger.info(f"Consent {consent_id} granted by farmer {farmer.id}")
    return consent


# ─────────────────────────────────────────────
# FARMER: Revoke consent
# ─────────────────────────────────────────────

@router.post("/{consent_id}/revoke", response_model=ConsentResponse)
def revoke_consent(
    consent_id: int,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    """Farmer revokes an active consent."""
    consent = db.query(Consent).filter(
        Consent.id == consent_id,
        Consent.farmer_id == farmer.id,
    ).first()
    if not consent:
        raise HTTPException(404, "Consent not found")

    consent.revoked_at = datetime.utcnow()
    consent.is_active = False
    db.commit()
    db.refresh(consent)
    logger.info(f"Consent {consent_id} revoked by farmer {farmer.id}")
    return consent


# ─────────────────────────────────────────────
# FARMER: Data access history
# ─────────────────────────────────────────────

@router.get("/data-access-history", response_model=List[DataAccessLogResponse])
def get_data_access_history(
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    """Farmer sees who accessed their data and when."""
    return db.query(DataAccessLog).filter(
        DataAccessLog.farmer_id == farmer.id
    ).order_by(DataAccessLog.accessed_at.desc()).limit(100).all()
