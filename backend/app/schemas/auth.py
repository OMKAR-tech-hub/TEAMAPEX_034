from typing import Optional

from pydantic import BaseModel, Field


class RegisterFarmerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    mobile: str = Field(pattern=r"^\d{10}$")
    password: str = Field(min_length=6, max_length=128)
    village: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    acreage: float = Field(gt=0, le=10000)
    primary_crop: str = Field(min_length=1, max_length=100)
    crop_season: str = Field(default="Kharif 2025", max_length=100)
    fpo_membership: Optional[str] = Field(None, max_length=255)


class RegisterOrgRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    name: str
    farmer_id: Optional[int] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: UserResponse