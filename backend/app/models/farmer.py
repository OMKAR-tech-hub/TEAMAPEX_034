from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    mobile = Column(String(15), unique=True, index=True, nullable=False)
    village = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    profile_photo = Column(String(500), nullable=True)
    fpo_membership = Column(String(255), nullable=True)
    acreage = Column(Float, nullable=False, default=0.0)
    primary_crop = Column(String(100), nullable=True)
    crop_season = Column(String(100), nullable=True)
    crop_insured = Column(Boolean, nullable=False, default=False)
    insurance_sum_assured = Column(Float, nullable=True)
    farm_experience_years = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="farmer", foreign_keys="User.farmer_id",
                        uselist=False, cascade="all, delete-orphan")
    production_records = relationship("ProductionRecord", back_populates="farmer", cascade="all, delete-orphan")
    credit_applications = relationship("CreditApplication", back_populates="farmer", cascade="all, delete-orphan")
    verifications = relationship("FPOVerification", back_populates="farmer", cascade="all, delete-orphan")
    passports = relationship("TrustPassport", back_populates="farmer", cascade="all, delete-orphan")
    consents = relationship("ConsentLog", back_populates="farmer", cascade="all, delete-orphan")
    credit_profiles = relationship("CreditProfile", back_populates="farmer", cascade="all, delete-orphan")
    loan_applications = relationship("LoanApplication", back_populates="farmer", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="farmer", cascade="all, delete-orphan")


class ProductionRecord(Base):
    __tablename__ = "production_records"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    crop_type = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False)
    season = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    verified = Column(Integer, default=0)
    weather_distress_observed = Column(Boolean, nullable=False, default=False)
    realized_price_per_q = Column(Float, nullable=True)  # actual mandi sale realization
    created_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="production_records")


class CreditApplication(Base):
    __tablename__ = "credit_applications"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    amount_requested = Column(Float, nullable=False)
    purpose = Column(String(255), nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="credit_applications")