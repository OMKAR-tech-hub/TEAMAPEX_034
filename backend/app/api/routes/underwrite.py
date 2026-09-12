import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, resolve_farmer
from app.core.database import get_db
from app.models.credit_profile import CreditProfile
from app.models.user import User
from app.schemas.underwrite import UnderwriteRequest, UnderwriteResult
from app.services.underwrite_service import evaluate_underwrite

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/evaluate", response_model=UnderwriteResult)
def underwrite_evaluate(
    payload: UnderwriteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farmer = resolve_farmer(db, payload.farmer_id)
    result = evaluate_underwrite(
        db,
        farmer,
        requested_amount=payload.requested_amount,
        tenure_months=payload.tenure_months,
        annual_interest_rate=payload.annual_interest_rate,
        origination_fee_rate=payload.origination_fee_rate,
        purpose_category=payload.purpose_category,
    )
    logger.info(
        f"Underwrite decision={result['decision']} for {farmer.farmer_id} "
        f"(limit Rs {result['safe_credit_limit']:,.0f}) by {user.name}"
    )
    return result


@router.get("/profiles/{farmer_id}", response_model=dict)
def latest_profile(
    farmer_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farmer = resolve_farmer(db, farmer_id)
    profile = (
        db.query(CreditProfile)
        .filter(CreditProfile.farmer_id == farmer.id)
        .order_by(CreditProfile.id.desc())
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No underwrite profile yet for this farmer. Call POST /underwrite/evaluate first.",
        )
    return {
        "credit_profile_id": profile.id,
        "farmer_id": farmer.farmer_id,
        "computed_at": profile.computed_at.isoformat() if profile.computed_at else None,
        "safe_credit_limit": profile.safe_credit_limit,
        "safe_credit_range": {
            "low": profile.recommended_range_low,
            "high": profile.recommended_range_high,
        },
        "agri_risk_tier": profile.agri_risk_tier,
        "agri_risk_score": profile.agri_risk_score,
        "top_reasons": profile.top_reasons,
        "purpose_category": (profile.input_snapshot or {}).get("purpose_category"),
        "community_vouch": (profile.input_snapshot or {}).get("community_vouch", False),
        "repayment_coverage": profile.repayment_coverage,
        "credit_tier": profile.credit_tier,
        "risk_haircut": profile.risk_haircut,
        "component_scores": profile.component_scores,
        "model_version": profile.model_version,
        "weather_loss_ratio": profile.weather_loss_ratio,
    }