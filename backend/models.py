"""
KisanSetu Database Models
Complete model definitions for all entities
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    Text, Boolean, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from backend.database import Base


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────

class UserRole(str, enum.Enum):
    FARMER = "farmer"
    FPO_MANAGER = "fpo_manager"
    LENDER = "lender"
    ADMIN = "admin"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class MembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


# ─────────────────────────────────────────────
# User (Authentication)
# ─────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.FARMER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farmer_profile = relationship("Farmer", back_populates="user", uselist=False)
    fpo_manager_profile = relationship("FPOManager", back_populates="user", uselist=False)
    lender_profile = relationship("Lender", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")


# ─────────────────────────────────────────────
# Farmer
# ─────────────────────────────────────────────

class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=True)
    village = Column(String(255), nullable=True)
    district = Column(String(255), nullable=True)
    state = Column(String(255), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String(20), nullable=True)
    # Legacy field - total farm size summary
    farm_size = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="farmer_profile")
    farms = relationship("Farm", back_populates="farmer", cascade="all, delete-orphan")
    production_records = relationship("ProductionRecord", back_populates="farmer", cascade="all, delete-orphan")
    sales_records = relationship("SalesRecord", back_populates="farmer", cascade="all, delete-orphan")
    credit_applications = relationship("CreditApplication", back_populates="farmer", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="farmer", cascade="all, delete-orphan")
    fpo_memberships = relationship("FPOMembership", back_populates="farmer", cascade="all, delete-orphan")
    trust_passports = relationship("TrustPassport", back_populates="farmer", cascade="all, delete-orphan")
    consents_given = relationship("Consent", back_populates="farmer", cascade="all, delete-orphan")
    data_access_logs = relationship("DataAccessLog", back_populates="farmer")


# ─────────────────────────────────────────────
# Farm
# ─────────────────────────────────────────────

class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    farm_name = Column(String(255), nullable=False)
    village = Column(String(255), nullable=True)
    district = Column(String(255), nullable=False)
    state = Column(String(255), nullable=False)
    location = Column(String(500), nullable=True)
    total_area_acres = Column(Float, nullable=False)
    soil_type = Column(String(100), nullable=True)
    irrigation_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farmer = relationship("Farmer", back_populates="farms")
    crop_seasons = relationship("CropSeason", back_populates="farm", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Crop Season
# ─────────────────────────────────────────────

class CropSeason(Base):
    __tablename__ = "crop_seasons"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    crop_name = Column(String(100), nullable=False)
    season = Column(String(50), nullable=False)   # kharif, rabi, zaid
    year = Column(Integer, nullable=False)
    area_sown_acres = Column(Float, nullable=False)
    sowing_date = Column(DateTime, nullable=True)
    expected_harvest_date = Column(DateTime, nullable=True)
    expected_yield_quintals = Column(Float, nullable=True)
    actual_yield_quintals = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farm = relationship("Farm", back_populates="crop_seasons")
    production_records = relationship("ProductionRecord", back_populates="crop_season")


# ─────────────────────────────────────────────
# Production Record
# ─────────────────────────────────────────────

class ProductionRecord(Base):
    __tablename__ = "production_records"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    crop_season_id = Column(Integer, ForeignKey("crop_seasons.id"), nullable=True)
    crop_type = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), default="quintals")
    season = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    area_acres = Column(Float, nullable=True)
    # Verification
    verified = Column(Boolean, default=False)
    fpo_verified = Column(Boolean, default=False)
    verified_by = Column(String(255), nullable=True)
    verification_date = Column(DateTime, nullable=True)
    evidence_url = Column(String(500), nullable=True)
    # Data source label
    data_source = Column(String(100), default="farmer_provided")  # farmer_provided, fpo_verified, benchmark
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farmer = relationship("Farmer", back_populates="production_records")
    crop_season = relationship("CropSeason", back_populates="production_records")
    sales_records = relationship("SalesRecord", back_populates="production_record")


# ─────────────────────────────────────────────
# Sales Record
# ─────────────────────────────────────────────

class SalesRecord(Base):
    __tablename__ = "sales_records"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    production_record_id = Column(Integer, ForeignKey("production_records.id"), nullable=True)
    crop_name = Column(String(100), nullable=False)
    quantity_sold = Column(Float, nullable=False)
    unit = Column(String(20), default="quintals")
    price_per_unit = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=True)
    market_name = Column(String(255), nullable=True)
    district = Column(String(255), nullable=True)
    state = Column(String(255), nullable=True)
    sale_date = Column(DateTime, nullable=False)
    buyer_type = Column(String(100), nullable=True)  # mandi, private, fpo, government
    # Verification
    verified = Column(Boolean, default=False)
    fpo_verified = Column(Boolean, default=False)
    verified_by = Column(String(255), nullable=True)
    verification_date = Column(DateTime, nullable=True)
    evidence_url = Column(String(500), nullable=True)
    data_source = Column(String(100), default="farmer_provided")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farmer = relationship("Farmer", back_populates="sales_records")
    production_record = relationship("ProductionRecord", back_populates="sales_records")


# ─────────────────────────────────────────────
# FPO
# ─────────────────────────────────────────────

class FPO(Base):
    __tablename__ = "fpos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    registration_number = Column(String(100), unique=True, nullable=True)
    district = Column(String(255), nullable=False)
    state = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    memberships = relationship("FPOMembership", back_populates="fpo", cascade="all, delete-orphan")
    managers = relationship("FPOManager", back_populates="fpo")


class FPOManager(Base):
    __tablename__ = "fpo_managers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    fpo_id = Column(Integer, ForeignKey("fpos.id"), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="fpo_manager_profile")
    fpo = relationship("FPO", back_populates="managers")


class FPOMembership(Base):
    __tablename__ = "fpo_memberships"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    fpo_id = Column(Integer, ForeignKey("fpos.id"), nullable=False)
    membership_date = Column(DateTime, nullable=True)
    membership_number = Column(String(100), nullable=True)
    status = Column(SAEnum(MembershipStatus), default=MembershipStatus.ACTIVE)
    verified = Column(Boolean, default=False)
    verified_by = Column(String(255), nullable=True)
    verification_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farmer = relationship("Farmer", back_populates="fpo_memberships")
    fpo = relationship("FPO", back_populates="memberships")


# ─────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────

class Verification(Base):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    verification_type = Column(String(100), nullable=False)
    record_type = Column(String(100), nullable=True)   # production, sales, membership, identity
    record_id = Column(Integer, nullable=True)          # ID of the specific record
    status = Column(SAEnum(VerificationStatus), default=VerificationStatus.PENDING)
    requested_by = Column(String(255), nullable=True)
    verified_by = Column(String(255), nullable=True)
    fpo_id = Column(Integer, ForeignKey("fpos.id"), nullable=True)
    verification_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    farmer = relationship("Farmer", back_populates="verifications")


# ─────────────────────────────────────────────
# Trust Passport / Credit Assessment
# ─────────────────────────────────────────────

class TrustPassport(Base):
    __tablename__ = "trust_passports"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    methodology_version = Column(String(20), default="1.0-baseline")

    # Core Scores (0-100)
    production_stability_score = Column(Float, nullable=True)
    market_stability_score = Column(Float, nullable=True)
    repayment_capacity_score = Column(Float, nullable=True)
    agricultural_risk_score = Column(Float, nullable=True)
    fpo_community_score = Column(Float, nullable=True)
    overall_creditworthiness = Column(Float, nullable=True)

    # Financial Estimates
    expected_crop_revenue = Column(Float, nullable=True)
    estimated_cultivation_cost = Column(Float, nullable=True)
    expected_net_agricultural_income = Column(Float, nullable=True)
    proposed_repayment = Column(Float, nullable=True)
    repayment_coverage = Column(Float, nullable=True)
    safe_credit_limit = Column(Float, nullable=True)
    safe_credit_limit_min = Column(Float, nullable=True)
    safe_credit_limit_max = Column(Float, nullable=True)

    # Recommendations
    recommended_credit_purpose = Column(String(500), nullable=True)

    # Detailed JSON fields
    explanation = Column(JSON, nullable=True)
    verification_status = Column(JSON, nullable=True)
    data_sources_used = Column(JSON, nullable=True)
    score_breakdown = Column(JSON, nullable=True)
    assumptions = Column(JSON, nullable=True)

    # Relationships
    farmer = relationship("Farmer", back_populates="trust_passports")
    credit_applications = relationship("CreditApplication", back_populates="assessment")


# ─────────────────────────────────────────────
# Lender
# ─────────────────────────────────────────────

class Lender(Base):
    __tablename__ = "lenders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    organization_name = Column(String(255), nullable=False)
    lender_type = Column(String(100), nullable=True)  # bank, nbfc, cooperative, mfi
    license_number = Column(String(100), nullable=True)
    district = Column(String(255), nullable=True)
    state = Column(String(255), nullable=True)
    contact_person = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="lender_profile")
    consents_received = relationship("Consent", back_populates="lender")
    credit_applications = relationship("CreditApplication", back_populates="lender")


# ─────────────────────────────────────────────
# Credit Application
# ─────────────────────────────────────────────

class CreditApplication(Base):
    __tablename__ = "credit_applications"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    lender_id = Column(Integer, ForeignKey("lenders.id"), nullable=True)
    assessment_id = Column(Integer, ForeignKey("trust_passports.id"), nullable=True)

    amount_requested = Column(Float, nullable=False)
    purpose = Column(Text, nullable=False)
    recommended_purpose = Column(String(500), nullable=True)
    recommended_limit = Column(Float, nullable=True)
    lender_type = Column(String(100), nullable=True)

    status = Column(SAEnum(ApplicationStatus), default=ApplicationStatus.PENDING)
    lender_notes = Column(Text, nullable=True)

    application_date = Column(DateTime, default=datetime.utcnow)
    decision_date = Column(DateTime, nullable=True)

    # Relationships
    farmer = relationship("Farmer", back_populates="credit_applications")
    lender = relationship("Lender", back_populates="credit_applications")
    assessment = relationship("TrustPassport", back_populates="credit_applications")


# ─────────────────────────────────────────────
# Consent & Data Ownership
# ─────────────────────────────────────────────

class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    lender_id = Column(Integer, ForeignKey("lenders.id"), nullable=False)
    data_fields_granted = Column(JSON, nullable=False)   # list of field names
    purpose = Column(Text, nullable=True)
    granted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=False)
    request_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    farmer = relationship("Farmer", back_populates="consents_given")
    lender = relationship("Lender", back_populates="consents_received")
    access_logs = relationship("DataAccessLog", back_populates="consent")


class DataAccessLog(Base):
    __tablename__ = "data_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    consent_id = Column(Integer, ForeignKey("consents.id"), nullable=True)
    accessor_user_id = Column(Integer, nullable=True)
    accessor_role = Column(String(50), nullable=True)
    accessor_name = Column(String(255), nullable=True)
    fields_accessed = Column(JSON, nullable=True)
    purpose = Column(Text, nullable=True)
    accessed_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(50), nullable=True)
    # Tamper-evident hash chain: current_hash = SHA256(previous_hash + canonical_payload)
    previous_hash = Column(String(64), nullable=True)
    current_hash = Column(String(64), nullable=True)

    # Relationships
    farmer = relationship("Farmer", back_populates="data_access_logs")
    consent = relationship("Consent", back_populates="access_logs")


# ─────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
