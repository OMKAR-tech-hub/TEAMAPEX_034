from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
import logging

from backend.database import get_db
from backend.models import Farmer
from backend.schemas import LoginRequest, TokenResponse, FarmerResponse
from backend.security import verify_password, create_access_token, decode_access_token

router = APIRouter()
logger = logging.getLogger(__name__)


def get_current_farmer(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> Farmer:
    """Dependency that resolves the authenticated farmer from the Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    subject = decode_access_token(authorization.split(" ", 1)[1])
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    farmer = db.query(Farmer).filter(Farmer.id == int(subject)).first()
    if farmer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Farmer no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return farmer


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a farmer with mobile number and password."""
    try:
        farmer = db.query(Farmer).filter(Farmer.mobile == payload.mobile).first()
        if not farmer or not verify_password(payload.password, farmer.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid mobile number or password",
            )

        token = create_access_token(str(farmer.id))
        logger.info(f"Farmer logged in: {farmer.farmer_id}")
        return TokenResponse(access_token=token, farmer=farmer)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to authenticate"
        )


@router.get("/me", response_model=FarmerResponse)
def get_me(current_farmer: Farmer = Depends(get_current_farmer)):
    """Return the identity of the currently authenticated farmer."""
    return current_farmer