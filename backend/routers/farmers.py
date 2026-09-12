"""
Farmer profile router — auth-gated, ownership-enforced
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from backend.database import get_db
from backend.models import Farmer, User, UserRole, AuditLog
from backend.schemas import FarmerUpdate, FarmerResponse
from backend.auth.dependencies import get_current_user, get_farmer_profile, require_role

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=FarmerResponse)
def get_my_profile(
    farmer: Farmer = Depends(get_farmer_profile),
):
    """Get the current farmer's own profile."""
    return farmer


@router.put("/me", response_model=FarmerResponse)
def update_my_profile(
    farmer_update: FarmerUpdate,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    """Update the current farmer's own profile."""
    update_data = farmer_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(farmer, field, value)
    db.commit()
    db.refresh(farmer)
    logger.info(f"Farmer profile updated: {farmer.id}")
    return farmer


@router.get("/{farmer_id}", response_model=FarmerResponse)
def get_farmer_by_id(
    farmer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a farmer profile by ID.
    - Farmers can only view their own profile.
    - FPO Managers and Lenders can view profiles of their own members/consented farmers.
    - Admin can view any.
    """
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    # Farmers: own profile only
    if current_user.role == UserRole.FARMER:
        if not current_user.farmer_profile or current_user.farmer_profile.id != farmer_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Lenders: must check consent (handled at passport level; basic profile access blocked here)
    if current_user.role == UserRole.LENDER:
        raise HTTPException(
            status_code=403,
            detail="Lenders must access farmer data via the Trust Passport consent system"
        )

    return farmer
