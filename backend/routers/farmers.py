from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
import logging

from backend.database import get_db
from backend.models import Farmer
from backend.schemas import FarmerCreate, FarmerUpdate, FarmerResponse
from backend.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=FarmerResponse, status_code=status.HTTP_201_CREATED)
def create_farmer(farmer: FarmerCreate, db: Session = Depends(get_db)):
    """Create a new farmer profile"""
    try:
        # Check if email already exists
        existing_farmer = db.query(Farmer).filter(Farmer.email == farmer.email).first()
        if existing_farmer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        db_farmer = Farmer(**farmer.model_dump())
        db.add(db_farmer)
        db.commit()
        db.refresh(db_farmer)
        
        logger.info(f"Created farmer profile: {db_farmer.id}")
        return db_farmer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating farmer: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create farmer profile"
        )


@router.get("/", response_model=List[FarmerResponse])
def list_farmers(
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    db: Session = Depends(get_db)
):
    """List all farmers with pagination"""
    try:
        farmers = db.query(Farmer).offset(skip).limit(limit).all()
        return farmers
    except Exception as e:
        logger.error(f"Error listing farmers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve farmers"
        )


@router.get("/{farmer_id}", response_model=FarmerResponse)
def get_farmer(farmer_id: int, db: Session = Depends(get_db)):
    """Get a specific farmer by ID"""
    try:
        farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
        if not farmer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Farmer not found"
            )
        return farmer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving farmer {farmer_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve farmer"
        )


@router.put("/{farmer_id}", response_model=FarmerResponse)
def update_farmer(
    farmer_id: int,
    farmer_update: FarmerUpdate,
    db: Session = Depends(get_db)
):
    """Update a farmer profile"""
    try:
        db_farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
        if not db_farmer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Farmer not found"
            )
        
        # Update only provided fields
        update_data = farmer_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_farmer, field, value)
        
        db.commit()
        db.refresh(db_farmer)
        
        logger.info(f"Updated farmer profile: {farmer_id}")
        return db_farmer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating farmer {farmer_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update farmer profile"
        )


@router.delete("/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farmer(farmer_id: int, db: Session = Depends(get_db)):
    """Delete a farmer profile"""
    try:
        db_farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
        if not db_farmer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Farmer not found"
            )
        
        db.delete(db_farmer)
        db.commit()
        
        logger.info(f"Deleted farmer profile: {farmer_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting farmer {farmer_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete farmer profile"
        )
