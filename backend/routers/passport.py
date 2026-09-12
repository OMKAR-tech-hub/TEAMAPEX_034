"""
Trust Passport router
GET  /passport/me            — farmer's own passport
POST /passport/generate      — generate/refresh passport
GET  /passport/{farmer_id}   — lender/FPO access (consent-gated)
POST /passport/what-if       — simulation, no DB mutation
GET  /passport/market-prices — market intelligence
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from backend.database import get_db
from backend.models import (
    Farmer, User, UserRole, TrustPassport, Consent, DataAccessLog,
    Lender
)
from backend.schemas import TrustPassportResponse, WhatIfRequest, WhatIfResponse, MarketPriceResponse
from backend.auth.dependencies import get_current_user, get_farmer_profile
from backend.services.passport_engine import (
    generate_trust_passport, calculate_repayment_capacity,
    calculate_safe_credit_limit, score_agricultural_risk,
    recommend_credit_purpose, get_risk_haircut,
)
from backend.services.market_intelligence import (
    get_market_prices, calculate_market_stats,
    get_benchmark_yield, get_weather_risk,
)
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=TrustPassportResponse)
def get_my_passport(
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    """Farmer retrieves their own Trust Passport."""
    passport = db.query(TrustPassport).filter(TrustPassport.farmer_id == farmer.id).first()
    if not passport:
        # Auto-generate on first access
        passport = generate_trust_passport(farmer, db)
    return passport


@router.post("/generate", response_model=TrustPassportResponse)
def generate_passport(
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    """Generate or refresh farmer's Trust Passport."""
    passport = generate_trust_passport(farmer, db)
    return passport


@router.get("/{farmer_id}", response_model=TrustPassportResponse)
def get_farmer_passport(
    farmer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a farmer's passport.
    - Farmer: own only
    - Lender: requires active consent
    - FPO Manager / Admin: allowed
    """
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(404, "Farmer not found")

    # Ownership check for farmers
    if current_user.role == UserRole.FARMER:
        if not current_user.farmer_profile or current_user.farmer_profile.id != farmer_id:
            raise HTTPException(403, "Access denied")

    # Lender must have active consent
    if current_user.role == UserRole.LENDER:
        if not current_user.lender_profile:
            raise HTTPException(403, "Lender profile not found")
        consent = db.query(Consent).filter(
            Consent.farmer_id == farmer_id,
            Consent.lender_id == current_user.lender_profile.id,
            Consent.is_active == True,
        ).first()
        if not consent:
            raise HTTPException(
                403,
                "No active consent from farmer. Farmer must grant data access before you can view their passport."
            )
        # Log the access
        log = DataAccessLog(
            farmer_id=farmer_id,
            consent_id=consent.id,
            accessor_user_id=current_user.id,
            accessor_role="lender",
            accessor_name=current_user.lender_profile.organization_name,
            fields_accessed=["trust_passport", "credit_scores", "safe_credit_limit"],
            purpose=consent.purpose or "credit assessment",
            accessed_at=datetime.utcnow(),
        )
        db.add(log)
        db.commit()

    passport = db.query(TrustPassport).filter(TrustPassport.farmer_id == farmer_id).first()
    if not passport:
        passport = generate_trust_passport(farmer, db)
    return passport


@router.get("/{farmer_id}/explanation")
def get_passport_explanation(
    farmer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the full plain-language explanation for a farmer's passport."""
    passport = db.query(TrustPassport).filter(TrustPassport.farmer_id == farmer_id).first()
    if not passport:
        raise HTTPException(404, "Passport not found. Generate it first.")
    return {
        "farmer_id": farmer_id,
        "overall_creditworthiness": passport.overall_creditworthiness,
        "safe_credit_limit": passport.safe_credit_limit,
        "score_breakdown": passport.score_breakdown,
        "explanation": passport.explanation,
        "assumptions": passport.assumptions,
        "data_sources_used": passport.data_sources_used,
        "generated_at": passport.generated_at,
        "methodology_version": passport.methodology_version,
        "lender_note": "KisanSetu provides an explainable profile. Lender makes the final credit decision.",
    }


@router.post("/what-if", response_model=WhatIfResponse)
def what_if_simulation(
    request: WhatIfRequest,
    farmer: Farmer = Depends(get_farmer_profile),
    db: Session = Depends(get_db),
):
    """
    Simulate how the passport changes with hypothetical inputs.
    DOES NOT modify real farmer data.
    """
    farms = farmer.farms
    current_area = sum(f.total_area_acres for f in farms) if farms else (farmer.farm_size or 2.0)
    current_crop = (farmer.production_records[0].crop_type
                    if farmer.production_records else "wheat")
    state = farmer.state

    # Current values
    current_rep = calculate_repayment_capacity(current_crop, current_area, state)
    current_risk = score_agricultural_risk(current_crop, state, farms)
    current_credit = calculate_safe_credit_limit(current_crop, current_area, state, current_risk["score"])

    # Hypothetical values
    hypo_crop  = request.hypothetical_crop or current_crop
    hypo_area  = request.hypothetical_area_acres or current_area

    # Use custom price/yield if provided, else market defaults
    from backend.services.market_intelligence import calculate_market_stats, get_benchmark_yield as gbm
    hypo_mkt = calculate_market_stats(hypo_crop, state)
    hypo_benchmark = gbm(hypo_crop)

    hypo_yield    = request.hypothetical_yield_quintals_per_acre or hypo_benchmark["benchmark_yield"]
    hypo_price    = request.hypothetical_price_per_quintal or hypo_mkt.get("conservative_price", 1500)
    hypo_cost     = request.hypothetical_cultivation_cost or (hypo_area * 15000)

    hypo_production = hypo_area * hypo_yield
    hypo_revenue    = hypo_production * hypo_price
    hypo_net_income = hypo_revenue - hypo_cost

    loan = request.requested_loan_amount or current_credit["safe_credit_limit"]
    hypo_coverage   = hypo_net_income / loan if loan and loan > 0 else None

    hypo_risk = score_agricultural_risk(hypo_crop, state, farms)
    haircut, haircut_desc = get_risk_haircut(hypo_risk["score"])
    hypo_safe_limit = hypo_area * hypo_yield * hypo_price * haircut

    within_limit = (loan <= hypo_safe_limit) if loan else None

    current_out = {
        "crop": current_crop,
        "area_acres": current_area,
        "expected_revenue": current_rep["expected_revenue"],
        "net_income": current_rep["net_income"],
        "safe_credit_limit": current_credit["safe_credit_limit"],
        "repayment_coverage": current_rep.get("repayment_coverage"),
    }
    hypo_out = {
        "crop": hypo_crop,
        "area_acres": hypo_area,
        "yield_per_acre": hypo_yield,
        "price_per_quintal": hypo_price,
        "expected_production_quintals": round(hypo_production, 2),
        "expected_revenue": round(hypo_revenue, 2),
        "cultivation_cost": round(hypo_cost, 2),
        "net_income": round(hypo_net_income, 2),
        "repayment_coverage": round(hypo_coverage, 2) if hypo_coverage else None,
        "safe_credit_limit": round(hypo_safe_limit, 0),
        "requested_loan": loan,
        "within_safe_limit": within_limit,
        "risk_haircut": haircut,
        "risk_haircut_description": haircut_desc,
    }
    delta = {
        "revenue_change": round(hypo_revenue - current_rep["expected_revenue"], 2),
        "net_income_change": round(hypo_net_income - current_rep["net_income"], 2),
        "safe_limit_change": round(hypo_safe_limit - current_credit["safe_credit_limit"], 2),
    }

    return WhatIfResponse(
        current=current_out,
        hypothetical=hypo_out,
        delta=delta,
        note="What-If simulation only. Real farmer data has NOT been modified.",
    )


@router.get("/market/prices", response_model=List[MarketPriceResponse])
def get_market_prices_endpoint(
    crop: str = Query(...),
    state: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get market price data for a crop."""
    prices = get_market_prices(crop, state)
    return [
        MarketPriceResponse(
            crop=p["crop"], market=p["market"], district=p["district"],
            state=p["state"], modal_price=p["modal_price"],
            min_price=p["min_price"], max_price=p["max_price"],
            date=p["date"], source=p["source"],
            data_caveat="DEMO/SYNTHETIC dataset. Not live government AGMARKNET data.",
        ) for p in prices
    ]
