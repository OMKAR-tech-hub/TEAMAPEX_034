from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class FpoVouch(Base):
    """Community credit enhancement: the FPO vouches a member's loan request.

    A vouch is a first-loss style community guarantee. When active it de-risks
    the loan (risk discount reduced) and prices a lower credit cost for the
    farmer — this is how the community reduces lending risk (mission Q5).
    """

    __tablename__ = "fpo_vouches"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    fpo_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    loan_application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=True)
    guarantee_amount = Column(Float, nullable=True)  # optional explicit community stake
    guarantee_style = Column(String(30), default="joint_review")  # joint_review | first_loss
    status = Column(String(20), default="active")  # active | withdrawn
    notes = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer")
    vouch_by_user = relationship("User")