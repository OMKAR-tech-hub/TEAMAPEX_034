import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.loan import LoanApplication
from app.models.user import Role, User
from app.schemas.loan import SettlementRequest
from app.services.loan_service import loan_to_dict, process_settlement

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=dict)
def create_settlement(
    payload: SettlementRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in (Role.FARMER.value, Role.BANK.value, Role.FPO.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    loan = db.query(LoanApplication).filter(LoanApplication.id == payload.loan_id).first()
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if user.role == Role.FARMER.value and loan.farmer_id != user.farmer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your loan")

    try:
        settlement = process_settlement(
            db, loan, payload.sale_value, payload.crop, payload.agmarknet_price_per_q
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    logger.info(
        f"{user.name} settled sale INR {settlement.sale_value} on loan {loan.application_uid}; "
        f"EMI {settlement.emi_paid}, FPO fee {settlement.fpo_facilitation_amt}, "
        f"residual to farmer {settlement.residual_to_farmer}"
    )
    return loan_to_dict(db, loan)