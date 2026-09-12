from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class CreditProfile(Base):
    __tablename__ = "credit_profiles"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow)
    safe_credit_limit = Column(Float, nullable=False)
    repayment_coverage = Column(Float, nullable=True)
    component_scores = Column(JSON, nullable=False)
    risk_haircut = Column(Float, nullable=False)
    credit_tier = Column(String(20), nullable=False)
    model_version = Column(String(20), nullable=False, default="kisansetu-v1")
    input_snapshot = Column(JSON, nullable=False)
    weather_loss_ratio = Column(Float, nullable=True)
    recommended_range_low = Column(Float, nullable=True)
    recommended_range_high = Column(Float, nullable=True)
    agri_risk_tier = Column(String(20), nullable=True)
    agri_risk_score = Column(Float, nullable=True)
    top_reasons = Column(JSON, nullable=True)

    farmer = relationship("Farmer", back_populates="credit_profiles")