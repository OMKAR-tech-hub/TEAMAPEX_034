from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base


class Farmer(Base):
    """Farmer model representing agricultural producers"""
    __tablename__ = "farmers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=True)
    farm_size = Column(Float, nullable=True)  # in acres
    crops = Column(Text, nullable=True)  # JSON string of crops
    fpo_membership = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    production_records = relationship("ProductionRecord", back_populates="farmer", cascade="all, delete-orphan")
    credit_applications = relationship("CreditApplication", back_populates="farmer", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="farmer", cascade="all, delete-orphan")


class ProductionRecord(Base):
    """Production record for tracking farmer's agricultural output"""
    __tablename__ = "production_records"
    
    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    crop_type = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False)  # in quintals or tons
    season = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    farmer = relationship("Farmer", back_populates="production_records")


class CreditApplication(Base):
    """Credit application model for loan requests"""
    __tablename__ = "credit_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    amount_requested = Column(Float, nullable=False)
    purpose = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, approved, rejected
    lender_type = Column(String(100), nullable=True)  # bank, nbfc, cooperative
    application_date = Column(DateTime, default=datetime.utcnow)
    decision_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    farmer = relationship("Farmer", back_populates="credit_applications")


class Verification(Base):
    """Verification records for farmer data validation"""
    __tablename__ = "verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    verification_type = Column(String(100), nullable=False)  # identity, production, fpo_membership
    status = Column(String(50), default="pending")  # pending, verified, rejected
    verified_by = Column(String(255), nullable=True)
    verification_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    farmer = relationship("Farmer", back_populates="verifications")
