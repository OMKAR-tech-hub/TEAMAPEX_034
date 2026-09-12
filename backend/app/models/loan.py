from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = Column(Integer, primary_key=True, index=True)
    application_uid = Column(String(20), unique=True, index=True, nullable=False)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    credit_profile_id = Column(Integer, ForeignKey("credit_profiles.id"), nullable=True)
    principal = Column(Float, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    annual_interest_rate = Column(Float, nullable=False)
    origination_fee_rate = Column(Float, nullable=False, default=0.0175)
    purpose_category = Column(String(40), nullable=False, default="working_capital")
    purpose_note = Column(String(200), nullable=True)
    status = Column(String(20), default="underwritten")  # underwritten|queued|approved|disbursing|active|repaid|written_off
    psl_category = Column(String(50), nullable=True)
    psl_eligible = Column(Boolean, default=False, nullable=False)
    amount_disbursed = Column(Float, nullable=False, default=0.0)
    amount_repaid = Column(Float, nullable=False, default=0.0)
    emi_paused = Column(Boolean, default=False, nullable=False)
    decided_by = Column(String(255), nullable=True)
    underwrite_snapshot = Column(JSON, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="loan_applications")
    tranches = relationship(
        "DisbursementTranche",
        back_populates="loan",
        cascade="all, delete-orphan",
        order_by="DisbursementTranche.tranche_no",
    )
    settlements = relationship(
        "Settlement", back_populates="loan", cascade="all, delete-orphan"
    )
    risk_events = relationship(
        "RiskEvent", back_populates="loan", cascade="all, delete-orphan"
    )


class DisbursementTranche(Base):
    __tablename__ = "disbursement_tranches"

    id = Column(Integer, primary_key=True, index=True)
    loan_application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=False)
    tranche_no = Column(Integer, nullable=False)
    label = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    payee_type = Column(String(20), nullable=False)  # vendor|farmer|escrow
    payee_ref = Column(String(100), nullable=False)
    status = Column(String(20), default="scheduled")  # scheduled|released|blocked|failed|reversed
    release_rule = Column(JSON, nullable=False, default=dict)
    released_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    loan = relationship("LoanApplication", back_populates="tranches")


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(Integer, primary_key=True, index=True)
    loan_application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=False)
    sale_value = Column(Float, nullable=False)
    crop = Column(String(100), nullable=True)
    agmarknet_price_per_q = Column(Float, nullable=True)
    fpo_facilitation_amt = Column(Float, nullable=False, default=0.0)
    platform_settlement_fee = Column(Float, nullable=False, default=0.0)
    emi_paid = Column(Float, nullable=False, default=0.0)
    residual_to_farmer = Column(Float, nullable=False, default=0.0)
    receipt_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    loan = relationship("LoanApplication", back_populates="settlements")


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, index=True)
    loan_application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=False)
    event_type = Column(String(20), nullable=False)  # drought|flood|pest|hail|disease
    severity = Column(String(10), nullable=False, default="moderate")  # mild|moderate|severe
    loss_ratio = Column(Float, nullable=False, default=0.0)
    declared_at = Column(DateTime, default=datetime.utcnow)
    action = Column(String(30), nullable=False, default="recalibrate")  # recalibrate|block_tranches|moratorium|pause

    loan = relationship("LoanApplication", back_populates="risk_events")