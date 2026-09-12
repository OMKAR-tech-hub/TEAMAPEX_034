from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FarmerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    village: Optional[str] = Field(None, min_length=1, max_length=100)
    district: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=1, max_length=100)
    profile_photo: Optional[str] = Field(None, max_length=500)
    fpo_membership: Optional[str] = Field(None, max_length=255)
    acreage: Optional[float] = Field(None, gt=0, le=10000)
    primary_crop: Optional[str] = Field(None, min_length=1, max_length=100)
    crop_season: Optional[str] = Field(None, max_length=100)


class FarmerResponse(BaseModel):
    id: int
    farmer_id: str
    name: str
    mobile: str
    village: str
    district: str
    state: str
    profile_photo: Optional[str] = None
    fpo_membership: Optional[str] = None
    acreage: float
    primary_crop: Optional[str] = None
    crop_season: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}