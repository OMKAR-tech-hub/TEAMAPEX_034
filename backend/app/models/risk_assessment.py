from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class RiskAssessment(Base):
    """Persisted snapshot of the explainable agricultural-risk + credit-capacity run."""

    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    risk_tier = Column(String(20), nullable=False)  # low | medium | high
    risk_score = Column(Float, nullable=False)  # 0-100, higher = riskier
    factor_scores = Column(JSON, nullable=False)
    factor_weights = Column(JSON, nullable=False)
    top_reasons = Column(JSON, nullable=False)
    recommended_range_low = Column(Float, nullable=False)
    recommended_range_high = Column(Float, nullable=False)
    recommended_credit = Column(Float, nullable=False)
    servicing_tdsr_low = Column(Float, nullable=False)
    servicing_tdsr_high = Column(Float, nullable=False)
    net_income_expected = Column(Float, nullable=False)
    repayment_capacity = Column(Float, nullable=False)
    insurance_uplift = Column(Float, nullable=False, default=0.0)
    model_version = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="risk_assessments")