from typing import List, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.farmer import Farmer
from app.models.user import Role, User


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    resolved = decode_access_token(authorization.split(" ", 1)[1])
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id, role = resolved
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.role != role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*roles: Role):
    allowed = {r.value for r in roles}

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return dependency


def resolve_farmer(db: Session, farmer_id: str) -> Farmer:
    farmer = None
    if isinstance(farmer_id, int):
        farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    elif farmer_id.isdigit():
        farmer = db.query(Farmer).filter(Farmer.id == int(farmer_id)).first()
    if farmer is None:
        farmer = db.query(Farmer).filter(Farmer.farmer_id == farmer_id).first()
    if farmer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer not found")
    return farmer


def ensure_owns_farmer(user: User, farmer: Farmer, roles_allowed: List[str]) -> None:
    if user.role in roles_allowed:
        return
    if user.role == Role.FARMER.value and user.farmer_id == farmer.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to perform this action",
    )