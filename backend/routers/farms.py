"""
Farms, Crop Seasons, Production Records, Sales Records
All ownership-enforced.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from backend.database import get_db
from backend.models import (
    Farmer, Farm, CropSeason, ProductionRecord, SalesRecord,
    User, UserRole, AuditLog, Verification, VerificationStatus
)
from backend.schemas import (
    FarmCreate, FarmUpdate, FarmResponse,
    CropSeasonCreate, CropSeasonResponse,
    ProductionRecordCreate, ProductionRecordResponse,
    SalesRecordCreate, SalesRecordResponse,
)
from backend.auth.dependencies import get_current_user, get_farmer_profile
from backend.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# FARMS
# ─────────────────────────────────────────────

@router.post("/farms", response_model=FarmResponse, status_code=201)
def create_farm(
    farm_in: FarmCreate,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    farm = Farm(farmer_id=farmer.id, **farm_in.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/farms", response_model=List[FarmResponse])
def list_farms(
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    return db.query(Farm).filter(Farm.farmer_id == farmer.id).all()


@router.get("/farms/{farm_id}", response_model=FarmResponse)
def get_farm(
    farm_id: int,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == farmer.id).first()
    if not farm:
        raise HTTPException(404, "Farm not found")
    return farm


@router.put("/farms/{farm_id}", response_model=FarmResponse)
def update_farm(
    farm_id: int,
    farm_in: FarmUpdate,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == farmer.id).first()
    if not farm:
        raise HTTPException(404, "Farm not found")
    for k, v in farm_in.model_dump(exclude_unset=True).items():
        setattr(farm, k, v)
    db.commit()
    db.refresh(farm)
    return farm


@router.delete("/farms/{farm_id}", status_code=204)
def delete_farm(
    farm_id: int,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == farmer.id).first()
    if not farm:
        raise HTTPException(404, "Farm not found")
    db.delete(farm)
    db.commit()


# ─────────────────────────────────────────────
# CROP SEASONS
# ─────────────────────────────────────────────

@router.post("/farms/{farm_id}/seasons", response_model=CropSeasonResponse, status_code=201)
def create_crop_season(
    farm_id: int,
    season_in: CropSeasonCreate,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == farmer.id).first()
    if not farm:
        raise HTTPException(404, "Farm not found")
    season = CropSeason(farm_id=farm_id, **season_in.model_dump())
    db.add(season)
    db.commit()
    db.refresh(season)
    return season


@router.get("/farms/{farm_id}/seasons", response_model=List[CropSeasonResponse])
def list_crop_seasons(
    farm_id: int,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.farmer_id == farmer.id).first()
    if not farm:
        raise HTTPException(404, "Farm not found")
    return db.query(CropSeason).filter(CropSeason.farm_id == farm_id).all()


# ─────────────────────────────────────────────
# PRODUCTION RECORDS
# ─────────────────────────────────────────────

@router.post("/production", response_model=ProductionRecordResponse, status_code=201)
def create_production_record(
    record_in: ProductionRecordCreate,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    record = ProductionRecord(
        farmer_id=farmer.id,
        **record_in.model_dump()
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/production", response_model=List[ProductionRecordResponse])
def list_production_records(
    year: Optional[int] = Query(None),
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    q = db.query(ProductionRecord).filter(ProductionRecord.farmer_id == farmer.id)
    if year:
        q = q.filter(ProductionRecord.year == year)
    return q.order_by(ProductionRecord.year.desc()).all()


@router.get("/production/{record_id}", response_model=ProductionRecordResponse)
def get_production_record(
    record_id: int,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    record = db.query(ProductionRecord).filter(
        ProductionRecord.id == record_id,
        ProductionRecord.farmer_id == farmer.id
    ).first()
    if not record:
        raise HTTPException(404, "Production record not found")
    return record


# ─────────────────────────────────────────────
# SALES RECORDS
# ─────────────────────────────────────────────

@router.post("/sales", response_model=SalesRecordResponse, status_code=201)
def create_sales_record(
    record_in: SalesRecordCreate,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    total = record_in.quantity_sold * record_in.price_per_unit
    record = SalesRecord(
        farmer_id=farmer.id,
        total_amount=total,
        **record_in.model_dump()
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/sales", response_model=List[SalesRecordResponse])
def list_sales_records(
    year: Optional[int] = Query(None),
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    q = db.query(SalesRecord).filter(SalesRecord.farmer_id == farmer.id)
    if year:
        q = q.filter(SalesRecord.sale_date >= datetime(year, 1, 1),
                     SalesRecord.sale_date < datetime(year + 1, 1, 1))
    return q.order_by(SalesRecord.sale_date.desc()).all()
