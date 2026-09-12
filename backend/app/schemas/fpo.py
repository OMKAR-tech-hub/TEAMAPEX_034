from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VerificationCreate(BaseModel):
    farmer_id: int
    verification_status: str = Field(default="pending", pattern="^(pending|verified|rejected)$")
    member_integrity_flag: bool = False
    notes: Optional[str] = Field(None, max_length=500)


class VerificationUpdate(BaseModel):
    verification_status: Optional[str] = Field(None, pattern="^(pending|verified|rejected)$")
    member_integrity_flag: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)


class VerificationResponse(BaseModel):
    id: int
    farmer_id: int
    fpo_name: str
    verification_status: str
    member_integrity_flag: bool
    verified_by: Optional[str] = None
    notes: Optional[str] = None
    verification_date: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}