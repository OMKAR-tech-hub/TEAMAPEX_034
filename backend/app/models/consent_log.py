from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class ConsentLog(Base):
    __tablename__ = "consent_logs"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    bank_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bank_name = Column(String(255), nullable=False)
    attributes = Column(JSON, nullable=False, default=list)
    masked_attributes = Column(JSON, nullable=False, default=list)
    granted = Column(Boolean, default=True, nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="consents")