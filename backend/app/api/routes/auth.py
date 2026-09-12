import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.farmer import Farmer
from app.models.user import Role, User
from app.schemas.auth import (
    LoginRequest,
    RegisterFarmerRequest,
    RegisterOrgRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _generate_farmer_id() -> str:
    return f"FAR-{uuid.uuid4().hex[:6].upper()}"


def _org_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        name=user.name,
        farmer_id=user.farmer_id,
    )


@router.post("/register/farmer", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_farmer(payload: RegisterFarmerRequest, db: Session = Depends(get_db)):
    try:
        if db.query(Farmer).filter(Farmer.mobile == payload.mobile).first():
            raise HTTPException(status_code=400, detail="Mobile number already registered")
        if db.query(User).filter(User.username == payload.mobile).first():
            raise HTTPException(status_code=400, detail="Mobile number already registered")

        farmer = Farmer(
            farmer_id=_generate_farmer_id(),
            name=payload.name,
            mobile=payload.mobile,
            village=payload.village,
            district=payload.district,
            state=payload.state,
            acreage=payload.acreage,
            primary_crop=payload.primary_crop,
            crop_season=payload.crop_season,
            fpo_membership=payload.fpo_membership,
        )
        db.add(farmer)
        db.flush()

        user = User(
            username=payload.mobile,
            password_hash=hash_password(payload.password),
            role=Role.FARMER.value,
            name=payload.name,
            farmer_id=farmer.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.refresh(farmer)

        logger.info(f"Registered farmer {farmer.farmer_id} (id={farmer.id})")
        return _org_response(user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Farmer registration failed: {exc}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register farmer")


@router.post("/register/fpo", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_fpo(payload: RegisterOrgRequest, db: Session = Depends(get_db)):
    try:
        if db.query(User).filter(User.username == payload.username).first():
            raise HTTPException(status_code=400, detail="Username already registered")
        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role=Role.FPO.value,
            name=payload.name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return _org_response(user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"FPO registration failed: {exc}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register FPO")


@router.post("/register/bank", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_bank(payload: RegisterOrgRequest, db: Session = Depends(get_db)):
    try:
        if db.query(User).filter(User.username == payload.username).first():
            raise HTTPException(status_code=400, detail="Username already registered")
        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role=Role.BANK.value,
            name=payload.name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return _org_response(user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Bank registration failed: {exc}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register bank")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user.id, user.role)
    logger.info(f"Login: {user.username} ({user.role})")
    return TokenResponse(
        access_token=token,
        role=user.role,
        user=_org_response(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return _org_response(current_user)


@router.get("/banks", response_model=list[UserResponse])
def list_banks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    banks = db.query(User).filter(User.role == Role.BANK.value).order_by(User.name.asc()).all()
    return [_org_response(b) for b in banks]