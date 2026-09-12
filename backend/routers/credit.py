from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

from backend.database import get_db
from backend.models import CreditApplication, Farmer
from backend.schemas import CreditApplicationCreate, CreditApplicationUpdate, CreditApplicationResponse
from backend.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=CreditApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_credit_application(
    application: CreditApplicationCreate,
    db: Session = Depends(get_db)
):
    """Create a new credit application"""
    try:
        # Verify farmer exists
        farmer = db.query(Farmer).filter(Farmer.id == application.farmer_id).first()
        if not farmer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Farmer not found"
            )
        
        db_application = CreditApplication(**application.model_dump())
        db.add(db_application)
        db.commit()
        db.refresh(db_application)
        
        logger.info(f"Created credit application: {db_application.id} for farmer: {application.farmer_id}")
        return db_application
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating credit application: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create credit application"
        )


@router.get("/", response_model=List[CreditApplicationResponse])
def list_credit_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    farmer_id: int = Query(None),
    status_filter: str = Query(None, alias="status"),
    db: Session = Depends(get_db)
):
    """List credit applications with optional filters"""
    try:
        query = db.query(CreditApplication)
        
        if farmer_id:
            query = query.filter(CreditApplication.farmer_id == farmer_id)
        
        if status_filter:
            query = query.filter(CreditApplication.status == status_filter)
        
        applications = query.offset(skip).limit(limit).all()
        return applications
    except Exception as e:
        logger.error(f"Error listing credit applications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credit applications"
        )


@router.get("/{application_id}", response_model=CreditApplicationResponse)
def get_credit_application(application_id: int, db: Session = Depends(get_db)):
    """Get a specific credit application by ID"""
    try:
        application = db.query(CreditApplication).filter(
            CreditApplication.id == application_id
        ).first()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit application not found"
            )
        
        return application
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving credit application {application_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credit application"
        )


@router.put("/{application_id}", response_model=CreditApplicationResponse)
def update_credit_application(
    application_id: int,
    application_update: CreditApplicationUpdate,
    db: Session = Depends(get_db)
):
    """Update a credit application (typically for status changes)"""
    try:
        db_application = db.query(CreditApplication).filter(
            CreditApplication.id == application_id
        ).first()
        
        if not db_application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit application not found"
            )
        
        # Update only provided fields
        update_data = application_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_application, field, value)
        
        # Set decision date if status is being changed to approved or rejected
        if "status" in update_data and update_data["status"] in ["approved", "rejected"]:
            db_application.decision_date = datetime.utcnow()
        
        db.commit()
        db.refresh(db_application)
        
        logger.info(f"Updated credit application: {application_id}")
        return db_application
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating credit application {application_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update credit application"
        )


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credit_application(application_id: int, db: Session = Depends(get_db)):
    """Delete a credit application"""
    try:
        db_application = db.query(CreditApplication).filter(
            CreditApplication.id == application_id
        ).first()
        
        if not db_application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit application not found"
            )
        
        db.delete(db_application)
        db.commit()
        
        logger.info(f"Deleted credit application: {application_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting credit application {application_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete credit application"
        )
