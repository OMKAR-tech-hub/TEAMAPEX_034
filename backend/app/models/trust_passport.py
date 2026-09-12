from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class TrustPassport(Base):
    __tablename__ = "trust_passports"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    crop_season = Column(String(100), nullable=True)
    safe_credit_limit = Column(Float, nullable=False)
    repayment_coverage = Column(Float, nullable=True)
    component_scores = Column(JSON, nullable=False)
    risk_haircut = Column(Float, nullable=False)
    yield_per_acre = Column(Float, nullable=False)
    benchmark_price = Column(Float, nullable=False)
    gross_income = Column(Float, nullable=False)
    net_income = Column(Float, nullable=False)
    repayment_demand = Column(Float, nullable=False, default=0.0)
    credit_tier = Column(String(20), nullable=False)
    range_low = Column(Float, nullable=True)
    range_high = Column(Float, nullable=True)
    agri_risk_tier = Column(String(20), nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="passports")