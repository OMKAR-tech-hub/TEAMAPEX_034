"""Deterministic credit engine.

Pure-Python business logic. Every output is a pure function of the farmer's
profile, their FPO verification and the mock market reference - no randomness,
no third-party data.

    Safe Credit Limit     = Acreage * Yield_per_acre * Benchmark_price * (1 - RiskHaircut)
    Repayment Coverage    = Net Income / Repayment Demand
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.market import (
    MOCK_CROP_MARKET,
    COVERAGE_SCALE,
    FULL_LANDHOLDING_ACRES,
    PRODUCTION_COST_RATIO,
    get_market_reference,
    normalize_crop,
)
from app.models.farmer import Farmer, CreditApplication
from app.models.fpo_verification import FPOVerification


@dataclass(frozen=True)
class PassportResult:
    safe_credit_limit: float
    repayment_coverage: Optional[float]
    component_scores: Dict[str, float]
    risk_haircut: float
    yield_per_acre: float
    benchmark_price: float
    gross_income: float
    net_income: float
    repayment_demand: float
    credit_tier: str
    range_low: float = 0.0
    range_high: float = 0.0
    agri_risk_tier: str = "medium"


def compute_repayment_demand(applications: List[CreditApplication]) -> float:
    return round(
        sum(a.amount_requested for a in applications if a.status != "rejected"),
        2,
    )


def _identity_score(farmer: Farmer) -> float:
    required = [farmer.name, farmer.mobile, farmer.village, farmer.district, farmer.state]
    populated = [f for f in required if f]
    base = round((len(populated) / 5.0) * 60.0, 2)
    if farmer.profile_photo:
        base += 15.0
    if farmer.fpo_membership:
        base += 15.0
    return round(min(100.0, base), 2)


def _landholding_score(acreage: float) -> float:
    if acreage <= 0:
        return 0.0
    score = 20.0 + 16.0 * acreage
    if acreage >= FULL_LANDHOLDING_ACRES:
        score = max(score, 100.0)
    return round(min(100.0, score), 2)


def _production_score(farmer: Farmer, gross_income: float) -> float:
    known_crop = normalize_crop(farmer.primary_crop or "") in MOCK_CROP_MARKET
    score = 100.0 if known_crop else 40.0
    if gross_income < 50000.0:
        score -= 20.0
    if gross_income >= 1000000.0:
        score += 10.0
    return round(min(100.0, max(0.0, score)), 2)


def _verification_score(verification: Optional[FPOVerification]) -> float:
    if verification is None:
        return 20.0
    status = verification.verification_status
    if status == "verified":
        return 100.0 if verification.member_integrity_flag else 70.0
    if status == "rejected":
        return 10.0
    return 50.0


def _repayment_score(coverage: Optional[float]) -> float:
    if coverage is None:
        return 100.0
    return round(min(100.0, coverage * COVERAGE_SCALE), 2)


def _stability_score(farmer: Farmer) -> float:
    created_at = farmer.created_at or datetime.utcnow()
    days = (datetime.utcnow() - created_at).days
    if days < 30:
        return 40.0
    if days < 180:
        return 60.0
    if days < 365:
        return 80.0
    return 100.0


def _risk_haircut(verification: Optional[FPOVerification]) -> float:
    if verification is None:
        return 0.20
    status = verification.verification_status
    if status == "verified":
        return 0.15 if verification.member_integrity_flag else 0.20
    if status == "rejected":
        return 0.35
    return 0.25


def _credit_tier(safe_credit_limit: float) -> str:
    if safe_credit_limit < 50000.0:
        return "Low"
    if safe_credit_limit < 200000.0:
        return "Medium"
    return "High"


def compute_passport(
    farmer: Farmer,
    verification: Optional[FPOVerification],
    repayment_demand: float,
) -> PassportResult:
    market = get_market_reference(farmer.primary_crop or "other")
    yield_per_acre = market["yield_per_acre"]
    benchmark_price = market["benchmark_price"]

    gross_income = round(farmer.acreage * yield_per_acre * benchmark_price, 2)
    net_income = round(gross_income * (1.0 - PRODUCTION_COST_RATIO), 2)
    risk_haircut = round(_risk_haircut(verification), 2)
    safe_credit_limit = round(gross_income * (1.0 - risk_haircut), 2)

    try:
        from app.services.risk_engine import credit_capacity_range

        capacity = credit_capacity_range(farmer, verification, repayment_demand)
        safe_credit_limit = capacity["recommended_credit"]
        range_low = capacity["range_low"]
        range_high = capacity["range_high"]
        agri_risk_tier = capacity["agri_risk"]["risk_tier"]
    except Exception:
        range_low, range_high, agri_risk_tier = 0.0, 0.0, "medium"

    if repayment_demand and repayment_demand > 0:
        repayment_coverage = round(net_income / repayment_demand, 2)
    else:
        repayment_coverage = None

    component_scores = {
        "identity": _identity_score(farmer),
        "landholding": _landholding_score(farmer.acreage),
        "production": _production_score(farmer, gross_income),
        "verification": _verification_score(verification),
        "repayment": _repayment_score(repayment_coverage),
        "stability": _stability_score(farmer),
        "agricultural_risk": 100.0 - _agri_risk_proxy(farmer),
    }

    return PassportResult(
        safe_credit_limit=safe_credit_limit,
        repayment_coverage=repayment_coverage,
        component_scores=component_scores,
        risk_haircut=risk_haircut,
        yield_per_acre=yield_per_acre,
        benchmark_price=benchmark_price,
        gross_income=gross_income,
        net_income=net_income,
        repayment_demand=round(repayment_demand, 2),
        credit_tier=(
            {"low": "Low", "medium": "Medium", "high": "High"}.get(agri_risk_tier)
            or _credit_tier(safe_credit_limit)
        ),
        range_low=range_low,
        range_high=range_high,
        agri_risk_tier=agri_risk_tier,
    )


def _agri_risk_proxy(farmer: Farmer) -> float:
    """0–100 normalized agricultural-risk proxy used for scorecard display."""
    base = 30.0
    if farmer.crop_insured:
        base -= 8.0
    if farmer.insurance_sum_assured and farmer.insurance_sum_assured > 0:
        base -= 5.0
    if (getattr(farmer, "farm_experience_years", 0) or 0) >= 5:
        base -= 7.0
    return max(0.0, min(100.0, base))


def build_passport_record(db: Session, farmer_id: int) -> Tuple[dict, dict]:
    """Assemble the persistence payload plus the engine inputs for transparency."""
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if farmer is None:
        raise ValueError("farmer not found")

    verification = (
        db.query(FPOVerification)
        .filter(FPOVerification.farmer_id == farmer_id)
        .order_by(FPOVerification.id.desc())
        .first()
    )
    applications = db.query(CreditApplication).filter(CreditApplication.farmer_id == farmer_id).all()
    repayment_demand = compute_repayment_demand(applications)

    result = compute_passport(farmer, verification, repayment_demand)

    record = {
        "farmer_id": farmer.id,
        "crop_season": farmer.crop_season,
        "safe_credit_limit": result.safe_credit_limit,
        "repayment_coverage": result.repayment_coverage,
        "component_scores": result.component_scores,
        "risk_haircut": result.risk_haircut,
        "yield_per_acre": result.yield_per_acre,
        "benchmark_price": result.benchmark_price,
        "gross_income": result.gross_income,
        "net_income": result.net_income,
        "repayment_demand": result.repayment_demand,
        "credit_tier": result.credit_tier,
        "range_low": result.range_low,
        "range_high": result.range_high,
        "agri_risk_tier": result.agri_risk_tier,
    }

    inputs = {
        "farmer_id": farmer.id,
        "farmer_id_string": farmer.farmer_id,
        "acreage": farmer.acreage,
        "primary_crop": farmer.primary_crop,
        "crop_season": farmer.crop_season,
        "verification_status": (
            verification.verification_status if verification is not None else None
        ),
        "member_integrity_flag": (
            verification.member_integrity_flag if verification is not None else None
        ),
        "repayment_demand": repayment_demand,
        "yield_per_acre": result.yield_per_acre,
        "benchmark_price": result.benchmark_price,
        "production_cost_ratio": PRODUCTION_COST_RATIO,
    }
    return record, inputs