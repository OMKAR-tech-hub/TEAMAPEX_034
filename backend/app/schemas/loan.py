from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoanCreateRequest(BaseModel):
    farmer_id: Optional[int] = None
    principal: float = Field(gt=0, description="Loan principal in INR")
    tenure_months: int = Field(default=12, ge=1, le=36)
    annual_interest_rate: float = Field(default=0.135, ge=0.01, le=0.30)
    origination_fee_rate: float = Field(default=0.0175, ge=0.0, le=0.05)
    credit_profile_id: Optional[int] = None
    purpose_category: str = Field(default="working_capital", max_length=40)
    purpose_note: Optional[str] = Field(default=None, max_length=200)


class TrancheReleaseRequest(BaseModel):
    tranche_id: int


class SettlementRequest(BaseModel):
    loan_id: int
    sale_value: float = Field(gt=0)
    crop: Optional[str] = None
    agmarknet_price_per_q: Optional[float] = None


class RiskEventCreateRequest(BaseModel):
    loan_id: int
    event_type: str = Field(pattern="^(drought|flood|pest|hail|disease)$")
    severity: str = Field(default="moderate", pattern="^(mild|moderate|severe)$")
    loss_ratio: Optional[float] = Field(default=None, ge=0.0, le=0.9)


class RiskEventResponse(BaseModel):
    id: int
    loan_application_id: int
    event_type: str
    severity: str
    loss_ratio: float
    action: str
    declared_at: datetime
    recalibrated_safe_credit_limit: Optional[float] = None
    farmer_charged_fees: float = 0.0


class WalletResponse(BaseModel):
    user_id: int
    role: str
    wallet_balance: float
    facilitation_tally: float = 0.0