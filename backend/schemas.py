from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# Farmer Schemas
class FarmerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    address: Optional[str] = None
    farm_size: Optional[float] = Field(None, gt=0)
    crops: Optional[str] = None
    fpo_membership: Optional[str] = None


class FarmerCreate(FarmerBase):
    pass


class FarmerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    address: Optional[str] = None
    farm_size: Optional[float] = Field(None, gt=0)
    crops: Optional[str] = None
    fpo_membership: Optional[str] = None


class FarmerResponse(FarmerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


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
