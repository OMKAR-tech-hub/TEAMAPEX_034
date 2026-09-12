"""
Authentication router - register, login, me
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging

from backend.database import get_db
from backend.models import User, UserRole, Farmer, FPOManager, Lender, FPO, AuditLog
from backend.schemas import (
    UserRegisterRequest, UserRegisterResponse, Token, UserMeResponse
)
from backend.auth.security import get_password_hash, verify_password, create_access_token
from backend.auth.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Role can be farmer, fpo_manager, or lender. Admin cannot self-register."""
    if request.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Cannot self-register as admin")

    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        role=request.role,
    )
    db.add(user)
    db.flush()

    # Create role-specific profile
    if request.role == UserRole.FARMER:
        farmer = Farmer(
            user_id=user.id,
            name=request.name,
            phone=request.phone or "",
            district=request.district,
            state=request.state,
        )
        db.add(farmer)

    elif request.role == UserRole.FPO_MANAGER:
        if not request.fpo_id:
            raise HTTPException(status_code=400, detail="fpo_id is required for FPO Manager registration")
        fpo = db.query(FPO).filter(FPO.id == request.fpo_id).first()
        if not fpo:
            raise HTTPException(status_code=404, detail="FPO not found")
        manager = FPOManager(
            user_id=user.id,
            fpo_id=request.fpo_id,
            name=request.name,
            phone=request.phone,
        )
        db.add(manager)

    elif request.role == UserRole.LENDER:
        lender = Lender(
            user_id=user.id,
            organization_name=request.organization_name or request.name,
            lender_type=request.lender_type,
            contact_person=request.name,
            phone=request.phone,
            district=request.district,
            state=request.state,
        )
        db.add(lender)

    # Audit
    audit = AuditLog(user_id=user.id, action="user_registered",
                     resource_type="user", details={"role": request.role.value})
    db.add(audit)
    db.commit()
    db.refresh(user)
    logger.info(f"User registered: {user.email} role={user.role}")
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with email + password, returns JWT access token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    audit = AuditLog(user_id=user.id, action="user_login",
                     resource_type="user", details={"email": user.email})
    db.add(audit)
    db.commit()
    return {"access_token": token, "token_type": "bearer", "role": user.role.value}


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user info."""
    profile_id = None
    if current_user.role == UserRole.FARMER and current_user.farmer_profile:
        profile_id = current_user.farmer_profile.id
    elif current_user.role == UserRole.FPO_MANAGER and current_user.fpo_manager_profile:
        profile_id = current_user.fpo_manager_profile.id
    elif current_user.role == UserRole.LENDER and current_user.lender_profile:
        profile_id = current_user.lender_profile.id
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "profile_id": profile_id,
    }
