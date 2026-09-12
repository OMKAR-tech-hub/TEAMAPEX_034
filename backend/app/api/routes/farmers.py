import logging
import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import ensure_owns_farmer, get_current_user, require_roles, resolve_farmer
from app.core.database import get_db
from app.core.config import settings
from app.models.farmer import Farmer
from app.models.user import Role, User
from app.schemas.farmer import FarmerResponse, FarmerUpdate

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.get("", response_model=list[FarmerResponse])
def list_farmers(
    skip: int = Query(0, ge=0),
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farmers = (
        db.query(Farmer)
        .order_by(Farmer.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return farmers


@router.get("/{farmer_id}", response_model=FarmerResponse)
def get_farmer(
    farmer_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return resolve_farmer(db, farmer_id)


@router.put("/{farmer_id}", response_model=FarmerResponse)
def update_farmer(
    farmer_id: str,
    payload: FarmerUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_farmer = resolve_farmer(db, farmer_id)
    ensure_owns_farmer(user, db_farmer, roles_allowed=[Role.FPO.value])

    data = payload.model_dump(exclude_unset=True)
    if "acreage" in data and data["acreage"] <= 0:
        raise HTTPException(status_code=422, detail="Acreage must be greater than zero")
    for field, value in data.items():
        setattr(db_farmer, field, value)

    db.commit()
    db.refresh(db_farmer)
    return db_farmer


@router.delete("/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farmer(
    farmer_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_farmer = resolve_farmer(db, farmer_id)
    ensure_owns_farmer(user, db_farmer, roles_allowed=[Role.FPO.value])

    db.delete(db_farmer)
    db.commit()
    return None


@router.post("/{farmer_id}/photo", response_model=FarmerResponse)
async def upload_photo(
    farmer_id: str,
    photo: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_farmer = resolve_farmer(db, farmer_id)
    ensure_owns_farmer(user, db_farmer, roles_allowed=[])

    if photo.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Photo must be a JPEG, PNG or WEBP image")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(photo.filename or "")[1] or ".jpg"
    filename = f"{db_farmer.farmer_id}-{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    db_farmer.profile_photo = f"/uploads/{filename}"
    db.commit()
    db.refresh(db_farmer)
    return db_farmer