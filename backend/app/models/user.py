from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Role(str, Enum):
    FARMER = "farmer"
    FPO = "fpo"
    BANK = "bank"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    name = Column(String(255), nullable=False)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True)
    wallet_balance = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="user",
                          foreign_keys=[farmer_id], uselist=False)