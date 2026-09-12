from typing import Dict, Optional, Union

from pydantic import BaseModel, Field


class UnderwriteRequest(BaseModel):
    farmer_id: Union[str, int]
    requested_amount: float = Field(gt=0)
    tenure_months: int = Field(ge=3, le=60)
    annual_interest_rate: float = Field(default=0.11, ge=0.0, le=0.30)
    origination_fee_rate: float = Field(default=0.0175, ge=0.015, le=0.020)
    purpose_category: Optional[str] = Field(default="working_capital", max_length=40)


class UnderwriteResult(BaseModel):
    credit_profile_id: int
    farmer_id: str
    decision: str
    reason: str
    purpose: Dict[str, object]
    safe_credit_limit: float
    safe_credit_range: Dict[str, float]
    credit_tier: str
    requested_amount: float
    repayment_coverage: Optional[float]
    risk_haircut: float
    component_scores: Dict[str, float]
    model_version: str
    risk_model_version: str
    agri_risk: Dict[str, object]
    amortization: Dict[str, float]
    origination_fee: Dict[str, object]
    breakdown: Dict[str, object]
    inputs: Dict[str, object]