from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

from backend.database import get_db
from backend.models import Verification, Farmer
from backend.schemas import VerificationCreate, VerificationUpdate, VerificationResponse
from backend.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
def create_verification(
    verification: VerificationCreate,
    db: Session = Depends(get_db)
):
    """Create a new verification request"""
    try:
        # Verify farmer exists
        farmer = db.query(Farmer).filter(Farmer.id == verification.farmer_id).first()
        if not farmer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Farmer not found"
            )
        
        db_verification = Verification(**verification.model_dump())
        db.add(db_verification)
        db.commit()
        db.refresh(db_verification)
        
        logger.info(f"Created verification: {db_verification.id} for farmer: {verification.farmer_id}")
        return db_verification
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating verification: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create verification"
        )


@router.get("/", response_model=List[VerificationResponse])
def list_verifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    farmer_id: int = Query(None),
    status_filter: str = Query(None, alias="status"),
    verification_type: str = Query(None),
    db: Session = Depends(get_db)
):
    """List verifications with optional filters"""
    try:
        query = db.query(Verification)
        
        if farmer_id:
            query = query.filter(Verification.farmer_id == farmer_id)
        
        if status_filter:
            query = query.filter(Verification.status == status_filter)
        
        if verification_type:
            query = query.filter(Verification.verification_type == verification_type)
        
        verifications = query.offset(skip).limit(limit).all()
        return verifications
    except Exception as e:
        logger.error(f"Error listing verifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve verifications"
        )


@router.get("/{verification_id}", response_model=VerificationResponse)
def get_verification(verification_id: int, db: Session = Depends(get_db)):
    """Get a specific verification by ID"""
    try:
        verification = db.query(Verification).filter(
            Verification.id == verification_id
        ).first()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification not found"
            )
        
        return verification
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving verification {verification_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve verification"
        )


@router.put("/{verification_id}", response_model=VerificationResponse)
def update_verification(
    verification_id: int,
    verification_update: VerificationUpdate,
    db: Session = Depends(get_db)
):
    """Update a verification (typically for status changes)"""
    try:
        db_verification = db.query(Verification).filter(
            Verification.id == verification_id
        ).first()
        
        if not db_verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification not found"
            )
        
        # Update only provided fields
        update_data = verification_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_verification, field, value)
        
        # Set verification date if status is being changed to verified or rejected
        if "status" in update_data and update_data["status"] in ["verified", "rejected"]:
            db_verification.verification_date = datetime.utcnow()
        
        db.commit()
        db.refresh(db_verification)
        
        logger.info(f"Updated verification: {verification_id}")
        return db_verification
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating verification {verification_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update verification"
        )


@router.delete("/{verification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_verification(verification_id: int, db: Session = Depends(get_db)):
    """Delete a verification"""
    try:
        db_verification = db.query(Verification).filter(
            Verification.id == verification_id
        ).first()
        
        if not db_verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification not found"
            )
        
        db.delete(db_verification)
        db.commit()
        
        logger.info(f"Deleted verification: {verification_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting verification {verification_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete verification"
        )
