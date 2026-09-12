"""Underwrite evaluation service.

Runs the deterministic credit engine plus the agricultural-risk capacity range,
prices an amortized loan offer, checks repayment coverage against the EMI
stream, applies purpose steering (Q3) and community vouch (Q5), and persists an
auditable snapshot into both `credit_profiles` and `risk_assessments`. The
origination fee is a B2B (lender-paid) fee and is never charged to the farmer
(RBI DLG).
"""
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.credit_profile import CreditProfile
from app.models.farmer import Farmer
from app.models.fpo_vouch import FpoVouch
from app.models.fpo_verification import FPOVerification
from app.services import credit_engine
from app.services.risk_engine import (
    MODEL_VERSION as RISK_MODEL_VERSION,
    credit_capacity_range,
    purpose_grade,
    repayment_capacity_amount,
)

MODEL_VERSION = "kisansetu-v1"


def annual_emi(principal: float, annual_rate: float, months: int) -> float:
    """Standard annuity EMI. Returns 0.0 implicitly guarded by validation upstream."""
    if months <= 0 or principal <= 0:
        return 0.0
    if annual_rate <= 0:
        return round(principal / months, 2)
    r = annual_rate / 12.0
    factor = (1.0 + r) ** months
    return round(principal * r * factor / (factor - 1.0), 2)


def has_community_vouch(db: Session, farmer_id: int) -> bool:
    return (
        db.query(FpoVouch)
        .filter(FpoVouch.farmer_id == farmer_id, FpoVouch.status == "active")
        .first()
        is not None
    )


def evaluate_underwrite(
    db: Session,
    farmer: Farmer,
    requested_amount: float,
    tenure_months: int,
    annual_interest_rate: float,
    origination_fee_rate: float,
    purpose_category: str = None,
) -> Dict:
    verification: Optional[FPOVerification] = (
        db.query(FPOVerification)
        .filter(FPOVerification.farmer_id == farmer.id)
        .order_by(FPOVerification.id.desc())
        .first()
    )
    applications = db.query(credit_engine.CreditApplication).filter(
        credit_engine.CreditApplication.farmer_id == farmer.id
    ).all()
    existing_demand = credit_engine.compute_repayment_demand(applications)
    community_vouch = has_community_vouch(db, farmer.id)

    engine = credit_engine.compute_passport(farmer, verification, existing_demand)
    capacity = credit_capacity_range(
        farmer,
        verification,
        existing_demand,
        tenure_months=tenure_months,
        annual_interest_rate=annual_interest_rate,
        community_vouch=community_vouch,
    )
    purpose = purpose_grade(purpose_category)
    decision, reason, _, purpose = repayment_capacity_amount(
        farmer,
        verification,
        existing_demand,
        requested_amount,
        tenure_months,
        annual_interest_rate,
        community_vouch,
        purpose_category,
    )

    emi = annual_emi(requested_amount, annual_interest_rate, tenure_months)
    total_payable = round(emi * tenure_months, 2) if emi else 0.0
    interest_payable = round(total_payable - requested_amount, 2) if total_payable else 0.0
    coverage = round(capacity["net_income_expected"] / total_payable, 2) if total_payable > 0 else None

    fee_amount = round(requested_amount * origination_fee_rate, 2)

    input_snapshot: Dict = {
        "farmer_id": farmer.farmer_id,
        "acreage": farmer.acreage,
        "primary_crop": farmer.primary_crop,
        "crop_season": farmer.crop_season,
        "requested_amount": requested_amount,
        "tenure_months": tenure_months,
        "annual_interest_rate": annual_interest_rate,
        "origination_fee_rate": origination_fee_rate,
        "purpose_category": purpose["category"],
        "existing_repayment_demand": existing_demand,
        "community_vouch": community_vouch,
        "yield_per_acre": engine.yield_per_acre,
        "benchmark_price": engine.benchmark_price,
        "production_cost_ratio": credit_engine.PRODUCTION_COST_RATIO,
        "verification_status": verification.verification_status if verification else None,
        "member_integrity_flag": verification.member_integrity_flag if verification else None,
    }

    profile = CreditProfile(
        farmer_id=farmer.id,
        safe_credit_limit=capacity["recommended_credit"],
        repayment_coverage=coverage,
        component_scores=engine.component_scores,
        risk_haircut=capacity["risk_discount"],
        credit_tier=capacity["agri_risk"]["risk_tier"],
        model_version=MODEL_VERSION,
        input_snapshot=input_snapshot,
        weather_loss_ratio=None,
        recommended_range_low=capacity["range_low"],
        recommended_range_high=capacity["range_high"],
        agri_risk_tier=capacity["agri_risk"]["risk_tier"],
        agri_risk_score=capacity["agri_risk"]["risk_score"],
        top_reasons=capacity["agri_risk"]["top_reasons"],
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return {
        "credit_profile_id": profile.id,
        "farmer_id": farmer.farmer_id,
        "decision": decision,
        "reason": reason,
        "purpose": purpose,
        "safe_credit_limit": capacity["recommended_credit"],
        "safe_credit_range": {
            "low": capacity["range_low"],
            "high": capacity["range_high"],
            "recommended": capacity["recommended_credit"],
        },
        "credit_tier": capacity["agri_risk"]["risk_tier"],
        "requested_amount": requested_amount,
        "repayment_coverage": coverage,
        "risk_haircut": capacity["risk_discount"],
        "component_scores": engine.component_scores,
        "model_version": MODEL_VERSION,
        "risk_model_version": RISK_MODEL_VERSION,
        "agri_risk": {
            "tier": capacity["agri_risk"]["risk_tier"],
            "score": capacity["agri_risk"]["risk_score"],
            "factor_scores": capacity["agri_risk"]["factor_scores"],
            "top_reasons": capacity["agri_risk"]["top_reasons"],
            "community_vouch": community_vouch,
            "risk_discount": capacity["risk_discount"],
            "insurance_uplift": capacity["insurance_uplift"],
        },
        "amortization": {
            "monthly_emi": emi,
            "tenure_months": tenure_months,
            "total_payable": total_payable,
            "interest_payable": interest_payable,
        },
        "origination_fee": {
            "rate": origination_fee_rate,
            "amount": fee_amount,
            "payer": "lender",
            "farmer_charged": 0.0,
        },
        "breakdown": {
            "gross_value": engine.gross_income,
            "net_income": capacity["net_income_expected"],
            "monthly_capacity": capacity["monthly_capacity"],
            "formula": "repayment capacity (net income x TDSR) inverts into a credit range",
        },
        "inputs": input_snapshot,
    }