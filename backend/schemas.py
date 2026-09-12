from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Farmer Schemas
class FarmerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    mobile: str = Field(..., pattern=r"^\d{10}$")
    village: str = Field(..., min_length=1, max_length=100)
    district: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    profile_photo: Optional[str] = Field(None, max_length=500)
    fpo_membership: Optional[str] = Field(None, max_length=255)


class FarmerCreate(FarmerBase):
    password: str = Field(..., min_length=6, max_length=128)
    farmer_id: Optional[str] = Field(None, max_length=50)


class FarmerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    mobile: Optional[str] = Field(None, pattern=r"^\d{10}$")
    village: Optional[str] = Field(None, min_length=1, max_length=100)
    district: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=1, max_length=100)
    profile_photo: Optional[str] = Field(None, max_length=500)
    fpo_membership: Optional[str] = Field(None, max_length=255)


class FarmerResponse(FarmerBase):
    id: int
    farmer_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Agricultural Profile Schemas
class AgriculturalProfileBase(BaseModel):
    farm_size: Optional[float] = Field(None, gt=0)
    crops: Optional[str] = None
    land_type: Optional[str] = Field(None, max_length=100)
    irrigation: Optional[str] = Field(None, max_length=100)


class AgriculturalProfileUpdate(AgriculturalProfileBase):
    pass


class AgriculturalProfileResponse(AgriculturalProfileBase):
    id: int
    farmer_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Auth Schemas
class LoginRequest(BaseModel):
    mobile: str = Field(..., pattern=r"^\d{10}$")
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    farmer: FarmerResponse


# Production Record Schemas
class ProductionRecordBase(BaseModel):
    crop_type: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    season: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=1900, le=2100)


class ProductionRecordCreate(ProductionRecordBase):
    farmer_id: int


class ProductionRecordResponse(ProductionRecordBase):
    id: int
    farmer_id: int
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Credit Application Schemas
class CreditApplicationBase(BaseModel):
    amount_requested: float = Field(..., gt=0)
    purpose: str = Field(..., min_length=1)
    lender_type: Optional[str] = Field(None, max_length=100)


class CreditApplicationCreate(CreditApplicationBase):
    farmer_id: int


class CreditApplicationUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|approved|rejected)$")
    notes: Optional[str] = None


class CreditApplicationResponse(CreditApplicationBase):
    id: int
    farmer_id: int
    status: str
    application_date: datetime
    decision_date: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# Verification Schemas
class VerificationBase(BaseModel):
    verification_type: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = None


class VerificationCreate(VerificationBase):
    farmer_id: int


class VerificationUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|verified|rejected)$")
    verified_by: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class VerificationResponse(VerificationBase):
    id: int
    farmer_id: int
    status: str
    verified_by: Optional[str] = None
    verification_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Pagination
class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    page_size: int
    total_pages: int