from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class FPOVerification(Base):
    __tablename__ = "fpo_verifications"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    fpo_name = Column(String(255), nullable=False)
    verification_status = Column(String(20), default="pending")  # pending | verified | rejected
    member_integrity_flag = Column(Boolean, default=False, nullable=False)
    verified_by = Column(String(255), nullable=True)
    notes = Column(String(500), nullable=True)
    verification_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="verifications")