from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel


class TrustPassportResponse(BaseModel):
    id: int
    farmer_id: int
    crop_season: Optional[str] = None
    safe_credit_limit: float
    repayment_coverage: Optional[float] = None
    component_scores: Dict[str, float]
    risk_haircut: float
    yield_per_acre: float
    benchmark_price: float
    gross_income: float
    net_income: float
    repayment_demand: float
    credit_tier: str
    range_low: Optional[float] = None
    range_high: Optional[float] = None
    agri_risk_tier: Optional[str] = None
    calculated_at: datetime

    model_config = {"from_attributes": True}


class ComputeRequest(BaseModel):
    force_recompute: bool = False


class ComputeResponse(BaseModel):
    passport: TrustPassportResponse
    inputs: Dict[str, object]