from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import logging
import os
import uuid
import shutil

from backend.database import get_db
from backend.models import Farmer
from backend.schemas import FarmerCreate, FarmerUpdate, FarmerResponse
from backend.config import settings
from backend.security import hash_password

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _generate_farmer_id() -> str:
    return f"FAR-{uuid.uuid4().hex[:6].upper()}"


@router.post("", response_model=FarmerResponse, status_code=status.HTTP_201_CREATED)
def create_farmer(farmer: FarmerCreate, db: Session = Depends(get_db)):
    """Create a new farmer account with basic identity information."""
    try:
        if db.query(Farmer).filter(Farmer.mobile == farmer.mobile).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile number already registered"
            )

        if farmer.farmer_id and db.query(Farmer).filter(Farmer.farmer_id == farmer.farmer_id).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Farmer ID already registered"
            )

        data = farmer.model_dump()
        data["farmer_id"] = data.get("farmer_id") or _generate_farmer_id()
        data["password_hash"] = hash_password(data.pop("password"))

        db_farmer = Farmer(**data)
        db.add(db_farmer)
        db.commit()
        db.refresh(db_farmer)

        logger.info(f"Created farmer account: {db_farmer.farmer_id} (id={db_farmer.id})")
        return db_farmer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating farmer: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create farmer account"
        )


@router.get("", response_model=List[FarmerResponse])
def list_farmers(
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    mobile: str = Query(None, description="Filter by mobile number"),
    db: Session = Depends(get_db)
):
    """List all farmers with pagination and optional mobile filter."""
    try:
        query = db.query(Farmer)
        if mobile:
            query = query.filter(Farmer.mobile == mobile)
        farmers = query.offset(skip).limit(limit).all()
        return farmers
    except Exception as e:
        logger.error(f"Error listing farmers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve farmers"
        )


def _resolve_farmer(db: Session, farmer_id: str) -> Farmer:
    """Resolve a farmer by numeric database id or string Farmer ID."""
    farmer = None
    if farmer_id.isdigit():
        farmer = db.query(Farmer).filter(Farmer.id == int(farmer_id)).first()
    if farmer is None:
        farmer = db.query(Farmer).filter(Farmer.farmer_id == farmer_id).first()
    if farmer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farmer not found"
        )
    return farmer


@router.get("/{farmer_id}", response_model=FarmerResponse)
def get_farmer(farmer_id: str, db: Session = Depends(get_db)):
    """Get a specific farmer by database id or Farmer ID."""
    try:
        return _resolve_farmer(db, farmer_id)
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
    farmer_id: str,
    farmer_update: FarmerUpdate,
    db: Session = Depends(get_db)
):
    """Update a farmer's identity information."""
    try:
        db_farmer = _resolve_farmer(db, farmer_id)

        update_data = farmer_update.model_dump(exclude_unset=True)

        if "mobile" in update_data and update_data["mobile"] != db_farmer.mobile:
            if db.query(Farmer).filter(Farmer.mobile == update_data["mobile"]).first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mobile number already registered"
                )

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
def delete_farmer(farmer_id: str, db: Session = Depends(get_db)):
    """Delete a farmer profile."""
    try:
        db_farmer = _resolve_farmer(db, farmer_id)

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


@router.post("/{farmer_id}/photo", response_model=FarmerResponse)
async def upload_farmer_photo(
    farmer_id: str,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload an optional profile photo for a farmer."""
    try:
        db_farmer = _resolve_farmer(db, farmer_id)

        if photo.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Photo must be a JPEG, PNG, or WEBP image"
            )

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = os.path.splitext(photo.filename or "")[1] or ".jpg"
        filename = f"{db_farmer.farmer_id}-{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

        db_farmer.profile_photo = f"/uploads/{filename}"
        db.commit()
        db.refresh(db_farmer)

        logger.info(f"Uploaded profile photo for farmer: {farmer_id}")
        return db_farmer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading photo for farmer {farmer_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload profile photo"
        )