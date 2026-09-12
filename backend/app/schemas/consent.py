from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ConsentCreate(BaseModel):
    bank_user_id: int
    attributes: List[str] = Field(default_factory=list)
    masked_attributes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


class ConsentUpdate(BaseModel):
    granted: bool


class ConsentResponse(BaseModel):
    id: int
    farmer_id: int
    bank_user_id: int
    bank_name: str
    attributes: List[str]
    masked_attributes: List[str]
    granted: bool
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MaskedField(BaseModel):
    attribute: str
    value: str
    masked: bool


class BankViewResponse(BaseModel):
    farmer_id: str
    bank_name: str
    consent_id: int
    consent_expires_at: Optional[datetime] = None
    fields: List[MaskedField]
    safe_credit_limit: Optional[float] = None
    credit_tier: Optional[str] = None
    component_scores: Optional[dict] = None

    model_config = {"from_attributes": True}