"""
KisanSetu Pydantic Schemas
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from backend.models import UserRole, VerificationStatus, ApplicationStatus, MembershipStatus


# ─────────────────────────────────────────────
# Auth Schemas
# ─────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.FARMER
    name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    district: Optional[str] = None
    state: Optional[str] = None
    # FPO Manager fields
    fpo_id: Optional[int] = None
    # Lender fields
    organization_name: Optional[str] = None
    lender_type: Optional[str] = None


class UserRegisterResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str


class UserMeResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    profile_id: Optional[int] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Farmer Schemas
# ─────────────────────────────────────────────

class FarmerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    gender: Optional[str] = None


class FarmerResponse(BaseModel):
    id: int
    user_id: int
    name: str
    phone: str
    address: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    gender: Optional[str] = None
    farm_size: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Farm Schemas
# ─────────────────────────────────────────────

class FarmCreate(BaseModel):
    farm_name: str = Field(..., min_length=1, max_length=255)
    village: Optional[str] = None
    district: str
    state: str
    location: Optional[str] = None
    total_area_acres: float = Field(..., gt=0)
    soil_type: Optional[str] = None
    irrigation_type: Optional[str] = None


class FarmUpdate(BaseModel):
    farm_name: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    location: Optional[str] = None
    total_area_acres: Optional[float] = Field(None, gt=0)
    soil_type: Optional[str] = None
    irrigation_type: Optional[str] = None


class FarmResponse(BaseModel):
    id: int
    farmer_id: int
    farm_name: str
    village: Optional[str] = None
    district: str
    state: str
    location: Optional[str] = None
    total_area_acres: float
    soil_type: Optional[str] = None
    irrigation_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Crop Season Schemas
# ─────────────────────────────────────────────

class CropSeasonCreate(BaseModel):
    crop_name: str = Field(..., min_length=1, max_length=100)
    season: str = Field(..., pattern="^(kharif|rabi|zaid|other)$")
    year: int = Field(..., ge=2000, le=2100)
    area_sown_acres: float = Field(..., gt=0)
    sowing_date: Optional[datetime] = None
    expected_harvest_date: Optional[datetime] = None
    expected_yield_quintals: Optional[float] = Field(None, gt=0)


class CropSeasonResponse(BaseModel):
    id: int
    farm_id: int
    crop_name: str
    season: str
    year: int
    area_sown_acres: float
    sowing_date: Optional[datetime] = None
    expected_harvest_date: Optional[datetime] = None
    expected_yield_quintals: Optional[float] = None
    actual_yield_quintals: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Production Record Schemas
# ─────────────────────────────────────────────

class ProductionRecordCreate(BaseModel):
    crop_type: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    unit: str = "quintals"
    season: str
    year: int = Field(..., ge=2000, le=2100)
    area_acres: Optional[float] = Field(None, gt=0)
    crop_season_id: Optional[int] = None
    evidence_url: Optional[str] = None


class ProductionRecordResponse(BaseModel):
    id: int
    farmer_id: int
    crop_type: str
    quantity: float
    unit: str
    season: str
    year: int
    area_acres: Optional[float] = None
    verified: bool
    fpo_verified: bool
    verified_by: Optional[str] = None
    verification_date: Optional[datetime] = None
    data_source: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Sales Record Schemas
# ─────────────────────────────────────────────

class SalesRecordCreate(BaseModel):
    crop_name: str = Field(..., min_length=1, max_length=100)
    quantity_sold: float = Field(..., gt=0)
    unit: str = "quintals"
    price_per_unit: float = Field(..., gt=0)
    market_name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    sale_date: datetime
    buyer_type: Optional[str] = None
    production_record_id: Optional[int] = None
    evidence_url: Optional[str] = None


class SalesRecordResponse(BaseModel):
    id: int
    farmer_id: int
    crop_name: str
    quantity_sold: float
    unit: str
    price_per_unit: float
    total_amount: Optional[float] = None
    market_name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    sale_date: datetime
    buyer_type: Optional[str] = None
    verified: bool
    fpo_verified: bool
    verified_by: Optional[str] = None
    data_source: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# FPO Schemas
# ─────────────────────────────────────────────

class FPOCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    registration_number: Optional[str] = None
    district: str
    state: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class FPOResponse(BaseModel):
    id: int
    name: str
    registration_number: Optional[str] = None
    district: str
    state: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FPOMembershipCreate(BaseModel):
    farmer_id: int
    fpo_id: int
    membership_date: Optional[datetime] = None
    membership_number: Optional[str] = None


class FPOMembershipResponse(BaseModel):
    id: int
    farmer_id: int
    fpo_id: int
    membership_date: Optional[datetime] = None
    membership_number: Optional[str] = None
    status: MembershipStatus
    verified: bool
    verified_by: Optional[str] = None
    verification_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Verification Schemas
# ─────────────────────────────────────────────

class VerificationCreate(BaseModel):
    farmer_id: int
    verification_type: str
    record_type: Optional[str] = None
    record_id: Optional[int] = None
    notes: Optional[str] = None


class VerificationUpdate(BaseModel):
    status: Optional[VerificationStatus] = None
    notes: Optional[str] = None


class VerificationResponse(BaseModel):
    id: int
    farmer_id: int
    verification_type: str
    record_type: Optional[str] = None
    record_id: Optional[int] = None
    status: VerificationStatus
    verified_by: Optional[str] = None
    verification_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Credit Application Schemas
# ─────────────────────────────────────────────

class CreditApplicationCreate(BaseModel):
    amount_requested: float = Field(..., gt=0)
    purpose: str = Field(..., min_length=1)
    lender_type: Optional[str] = None


class CreditApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    lender_notes: Optional[str] = None


class CreditApplicationResponse(BaseModel):
    id: int
    farmer_id: int
    lender_id: Optional[int] = None
    assessment_id: Optional[int] = None
    amount_requested: float
    purpose: str
    recommended_purpose: Optional[str] = None
    recommended_limit: Optional[float] = None
    lender_type: Optional[str] = None
    status: ApplicationStatus
    lender_notes: Optional[str] = None
    application_date: datetime
    decision_date: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Trust Passport Schemas
# ─────────────────────────────────────────────

class ScoreFactor(BaseModel):
    factor_name: str
    raw_value: Optional[float] = None
    normalized_score: float
    weight: float
    contribution: float
    direction: str  # positive, negative, neutral
    data_source: str
    verification_status: str
    explanation: str


class TrustPassportResponse(BaseModel):
    id: int
    farmer_id: int
    generated_at: datetime
    methodology_version: str

    # Core scores
    production_stability_score: Optional[float] = None
    market_stability_score: Optional[float] = None
    repayment_capacity_score: Optional[float] = None
    agricultural_risk_score: Optional[float] = None
    fpo_community_score: Optional[float] = None
    overall_creditworthiness: Optional[float] = None

    # Financials
    expected_crop_revenue: Optional[float] = None
    estimated_cultivation_cost: Optional[float] = None
    expected_net_agricultural_income: Optional[float] = None
    proposed_repayment: Optional[float] = None
    repayment_coverage: Optional[float] = None
    safe_credit_limit: Optional[float] = None
    safe_credit_limit_min: Optional[float] = None
    safe_credit_limit_max: Optional[float] = None

    # Recommendations
    recommended_credit_purpose: Optional[str] = None

    # Detailed
    explanation: Optional[Dict[str, Any]] = None
    verification_status: Optional[Dict[str, Any]] = None
    data_sources_used: Optional[List[str]] = None
    score_breakdown: Optional[List[Dict[str, Any]]] = None
    assumptions: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Consent Schemas
# ─────────────────────────────────────────────

class ConsentRequest(BaseModel):
    farmer_id: int
    data_fields_requested: List[str]
    purpose: Optional[str] = None
    request_message: Optional[str] = None


class ConsentGrant(BaseModel):
    consent_id: int
    data_fields_granted: List[str]
    expires_days: Optional[int] = 90


class ConsentResponse(BaseModel):
    id: int
    farmer_id: int
    lender_id: int
    data_fields_granted: List[str]
    purpose: Optional[str] = None
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    is_active: bool
    request_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DataAccessLogResponse(BaseModel):
    id: int
    farmer_id: int
    consent_id: Optional[int] = None
    accessor_role: Optional[str] = None
    accessor_name: Optional[str] = None
    fields_accessed: Optional[List[str]] = None
    purpose: Optional[str] = None
    accessed_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# What-If Schemas
# ─────────────────────────────────────────────

class WhatIfRequest(BaseModel):
    hypothetical_crop: Optional[str] = None
    hypothetical_area_acres: Optional[float] = Field(None, gt=0)
    hypothetical_price_per_quintal: Optional[float] = Field(None, gt=0)
    hypothetical_yield_quintals_per_acre: Optional[float] = Field(None, gt=0)
    hypothetical_cultivation_cost: Optional[float] = Field(None, gt=0)
    requested_loan_amount: Optional[float] = Field(None, gt=0)


class WhatIfResponse(BaseModel):
    current: Dict[str, Any]
    hypothetical: Dict[str, Any]
    delta: Dict[str, Any]
    note: str = "What-If simulation only. Real farmer data has NOT been modified."


# ─────────────────────────────────────────────
# Lender Schemas
# ─────────────────────────────────────────────

class LenderResponse(BaseModel):
    id: int
    user_id: int
    organization_name: str
    lender_type: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Market Data Schemas
# ─────────────────────────────────────────────

class MarketPriceResponse(BaseModel):
    crop: str
    market: str
    district: str
    state: str
    modal_price: float
    min_price: float
    max_price: float
    date: str
    source: str = "AGMARKNET (demo dataset)"
    data_caveat: str = "Regional market benchmark. Not individual farmer sale price."
