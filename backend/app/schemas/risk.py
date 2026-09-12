from typing import Optional

from pydantic import BaseModel, Field


class AssessResponse(BaseModel):
    assessment_id: int
    farmer_id: str
    assessed_at: Optional[str] = None
    risk_tier: str
    risk_score: float
    factor_scores: dict
    factor_reasons: dict
    top_reasons: list
    range_low: float
    range_high: float
    recommended_credit: float
    net_income_expected: float
    monthly_capacity: float
    repayment_coverage: Optional[float] = None
    risk_discount: float
    insurance_uplift: float
    community_vouch: bool
    mission_answers: list
    data_sources: list


class InsuranceUpdateRequest(BaseModel):
    crop_insured: bool = True
    insurance_sum_assured: Optional[float] = Field(default=None, ge=0)


class ProductionRecordCreateRequest(BaseModel):
    crop_type: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    season: str = Field(default="Kharif")
    year: int = Field(ge=2020, le=2027)
    verified: bool = True
    weather_distress_observed: bool = False
    realized_price_per_q: Optional[float] = Field(default=None, ge=0)


class SourcesResponse(BaseModel):
    sources: list


class VouchCreateRequest(BaseModel):
    farmer_id: int
    loan_application_id: Optional[int] = None
    guarantee_style: str = Field(default="first_loss", pattern="^(joint_review|first_loss)$")
    notes: Optional[str] = None
    score: Optional[int] = Field(default=None, ge=1, le=5)
    statement: Optional[str] = None
    season: Optional[str] = None
    year: Optional[int] = None
    fpo_id: Optional[int] = None
    attestor_user_id: Optional[int] = None