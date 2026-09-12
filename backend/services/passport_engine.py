"""
Trust Passport Scoring Engine
Transparent weighted scorecard — NO black-box decisions.
All intermediate values exposed in explanation.

FORMULA (from PRD):
Safe Credit Limit = Acreage × NHB Benchmark Yield × Conservative AGMARKNET Price × Risk Haircut

Weights:
  Production Stability   25%
  Market Stability       20%
  Repayment Capacity     25%
  Agricultural Risk      15%
  FPO Community          15%
"""
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from datetime import datetime
import statistics
import logging

from backend.models import (
    Farmer, Farm, CropSeason, ProductionRecord, SalesRecord,
    FPOMembership, Verification, VerificationStatus, TrustPassport
)
from backend.services.market_intelligence import (
    calculate_market_stats, get_benchmark_yield,
    get_weather_risk, get_cultivation_cost,
)
from backend.config import settings

logger = logging.getLogger(__name__)

# Risk haircut table (maps agricultural_risk_score → haircut fraction)
RISK_HAIRCUT_TABLE = [
    (90, 1.00, "Excellent — no haircut"),
    (75, 0.90, "Low risk — 10% haircut"),
    (60, 0.75, "Moderate risk — 25% haircut"),
    (45, 0.60, "Higher risk — 40% haircut"),
    (0,  0.45, "High risk — 55% haircut"),
]

def get_risk_haircut(agri_risk_score: float) -> Tuple[float, str]:
    """Return (haircut_fraction, description) for a given agricultural risk score."""
    for threshold, haircut, desc in RISK_HAIRCUT_TABLE:
        if agri_risk_score >= threshold:
            return haircut, desc
    return 0.45, "High risk — 55% haircut"


# ─────────────────────────────────────────────
# COMPONENT 1: Production Stability Score
# ─────────────────────────────────────────────

def score_production_stability(
    production_records: List[ProductionRecord],
    verifications: List[Verification],
) -> Dict[str, Any]:
    """
    Score based on:
    - Number of production seasons recorded
    - FPO-verified records ratio
    - Yield consistency (low CV = high score)
    """
    if not production_records:
        return {
            "score": 20.0,
            "reason": "No production records available — minimum baseline score",
            "inputs": {"num_records": 0, "fpo_verified_ratio": 0, "yield_cv_pct": None},
            "data_source": "farmer_provided",
            "verification_status": "unverified",
        }

    n = len(production_records)
    fpo_verified = sum(1 for r in production_records if r.fpo_verified)
    fpo_ratio = fpo_verified / n if n > 0 else 0

    # Yield consistency
    yields = [r.quantity / r.area_acres for r in production_records if r.area_acres and r.area_acres > 0]
    if len(yields) >= 2:
        mean_y = statistics.mean(yields)
        std_y = statistics.stdev(yields)
        cv = (std_y / mean_y * 100) if mean_y > 0 else 100
    elif len(yields) == 1:
        cv = 0  # only one season, assume stable
    else:
        cv = 50

    # Sub-scores
    record_score = min(100, n * 15)          # 1 season=15, 2=30 ... 7+=100
    fpo_score    = fpo_ratio * 100           # 100 if all verified
    cv_score     = max(0, 100 - cv * 1.5)   # lower CV = higher score

    score = 0.35 * record_score + 0.40 * fpo_score + 0.25 * cv_score
    score = min(100, max(0, score))

    return {
        "score": round(score, 1),
        "reason": f"{n} seasons on record; {fpo_verified}/{n} FPO-verified; yield CV={cv:.1f}%",
        "inputs": {
            "num_seasons": n,
            "fpo_verified_count": fpo_verified,
            "fpo_verified_ratio": round(fpo_ratio, 2),
            "yield_cv_pct": round(cv, 1),
        },
        "data_source": "farmer_provided+fpo_verified",
        "verification_status": "fpo_verified" if fpo_verified > 0 else "farmer_provided",
    }


# ─────────────────────────────────────────────
# COMPONENT 2: Market Stability Score
# ─────────────────────────────────────────────

def score_market_stability(
    primary_crop: str,
    state: Optional[str],
    sales_records: List[SalesRecord],
) -> Dict[str, Any]:
    """Score based on market price stability for the farmer's primary crop."""
    mkt = calculate_market_stats(primary_crop, state)
    score = mkt.get("market_stability_score", 50)

    # Bonus if farmer has verified sales (shows market access)
    if sales_records:
        verified_sales = sum(1 for s in sales_records if s.fpo_verified)
        if verified_sales > 0:
            score = min(100, score + 5)

    return {
        "score": round(score, 1),
        "reason": f"Market stability for {primary_crop}: CV={mkt.get('price_volatility_pct', '?')}%, trend={mkt.get('trend','?')}",
        "inputs": {
            "crop": primary_crop,
            "conservative_price": mkt.get("conservative_price"),
            "average_price": mkt.get("average_price"),
            "price_volatility_pct": mkt.get("price_volatility_pct"),
            "trend": mkt.get("trend"),
            "num_market_records": mkt.get("num_records", 0),
        },
        "data_source": mkt.get("source", "DEMO/SYNTHETIC"),
        "verification_status": "market_reference",
    }


# ─────────────────────────────────────────────
# COMPONENT 3: Repayment Capacity Score
# ─────────────────────────────────────────────

def calculate_repayment_capacity(
    primary_crop: str,
    total_area_acres: float,
    state: Optional[str],
    proposed_repayment: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Formula:
      Expected Production = area × benchmark_yield
      Expected Revenue    = production × conservative_price
      Cultivation Cost    = area × cost_per_acre
      Net Income          = revenue - cost
      Repayment Coverage  = net_income / proposed_repayment  (if provided)
    """
    benchmark = get_benchmark_yield(primary_crop)
    mkt = calculate_market_stats(primary_crop, state)
    benchmark_yield = benchmark["benchmark_yield"]
    conservative_price = mkt.get("conservative_price", 1500)
    cultivation_cost = get_cultivation_cost(primary_crop, total_area_acres)

    expected_production = total_area_acres * benchmark_yield
    expected_revenue = expected_production * conservative_price
    net_income = expected_revenue - cultivation_cost
    repayment_coverage = None
    if proposed_repayment and proposed_repayment > 0:
        repayment_coverage = net_income / proposed_repayment

    # Score mapping
    if repayment_coverage is None:
        # Score on net income margin alone
        margin = (net_income / expected_revenue * 100) if expected_revenue > 0 else 0
        score = min(100, max(0, margin * 1.5))
    else:
        if repayment_coverage >= 3.0:   score = 95
        elif repayment_coverage >= 2.0: score = 85
        elif repayment_coverage >= 1.5: score = 75
        elif repayment_coverage >= 1.2: score = 65
        elif repayment_coverage >= 1.0: score = 55
        elif repayment_coverage >= 0.8: score = 40
        else:                           score = 20

    return {
        "score": round(score, 1),
        "expected_production_quintals": round(expected_production, 2),
        "expected_revenue": round(expected_revenue, 2),
        "cultivation_cost": round(cultivation_cost, 2),
        "net_income": round(net_income, 2),
        "repayment_coverage": round(repayment_coverage, 2) if repayment_coverage else None,
        "reason": f"Net income ₹{net_income:,.0f}; coverage {repayment_coverage:.2f}x" if repayment_coverage else f"Net income ₹{net_income:,.0f}",
        "inputs": {
            "area_acres": total_area_acres,
            "benchmark_yield_q_per_acre": benchmark_yield,
            "conservative_price_per_quintal": conservative_price,
            "cultivation_cost_total": round(cultivation_cost, 2),
        },
        "data_source": f"NHB={benchmark['source']};AGMARKNET={mkt.get('source','DEMO')}",
        "verification_status": "benchmark_reference",
    }


def score_repayment_capacity(repayment_data: Dict) -> float:
    return repayment_data["score"]


# ─────────────────────────────────────────────
# COMPONENT 4: Agricultural Risk Score
# ─────────────────────────────────────────────

def score_agricultural_risk(
    primary_crop: str,
    state: Optional[str],
    farms: List[Farm],
) -> Dict[str, Any]:
    """
    Based on:
    - PMFBY/weather risk index for state+crop
    - Irrigation availability (irrigated = lower risk)
    - Diversification (multiple farms/crops = lower risk)
    """
    risk_data = get_weather_risk(state or "default", primary_crop)
    base_score = risk_data.get("risk_score", 60)

    # Irrigation bonus
    irrigated = sum(1 for f in farms if f.irrigation_type and f.irrigation_type.lower() not in ["rainfed", "none", ""])
    if farms:
        irrigation_bonus = (irrigated / len(farms)) * 15
    else:
        irrigation_bonus = 0

    score = min(100, base_score + irrigation_bonus)

    return {
        "score": round(score, 1),
        "reason": f"Weather risk for {primary_crop} in {state}: base={base_score}; irrigation_bonus={irrigation_bonus:.1f}",
        "inputs": {
            "weather_risk_base": base_score,
            "rainfall_risk": risk_data.get("rainfall_risk"),
            "temperature_risk": risk_data.get("temperature_risk"),
            "irrigated_farms": irrigated,
            "total_farms": len(farms),
            "irrigation_bonus": round(irrigation_bonus, 1),
        },
        "data_source": risk_data.get("source", "DEMO/SYNTHETIC"),
        "verification_status": "risk_reference",
    }


# ─────────────────────────────────────────────
# COMPONENT 5: FPO Community Score
# ─────────────────────────────────────────────

def score_fpo_community(
    memberships: List[FPOMembership],
    verifications: List[Verification],
) -> Dict[str, Any]:
    """
    Based on:
    - Active FPO membership
    - Number of FPO-verified records
    - Membership duration
    """
    active = [m for m in memberships if m.status.value == "active"]
    verified_records = [v for v in verifications if v.status == VerificationStatus.VERIFIED]

    score = 0.0
    membership_score = min(40, len(active) * 40)   # 40 pts for any active membership
    verification_score = min(60, len(verified_records) * 15)  # 15 pts per verified record

    score = membership_score + verification_score
    score = min(100, score)

    return {
        "score": round(score, 1),
        "reason": f"{len(active)} active FPO membership(s); {len(verified_records)} FPO-verified records",
        "inputs": {
            "active_memberships": len(active),
            "fpo_verified_records": len(verified_records),
        },
        "data_source": "fpo_database",
        "verification_status": "fpo_verified" if active else "not_fpo_member",
        "important_note": "FPO membership acts as a trust/verification layer only. FPO does NOT guarantee loan repayment.",
    }


# ─────────────────────────────────────────────
# SAFE CREDIT LIMIT
# ─────────────────────────────────────────────

def calculate_safe_credit_limit(
    primary_crop: str,
    total_area_acres: float,
    state: Optional[str],
    agri_risk_score: float,
) -> Dict[str, Any]:
    """
    PRD Formula:
    Safe Credit Limit = Acreage × NHB Benchmark Yield × Conservative Price × Risk Haircut
    """
    benchmark = get_benchmark_yield(primary_crop)
    mkt = calculate_market_stats(primary_crop, state)
    haircut, haircut_desc = get_risk_haircut(agri_risk_score)

    benchmark_yield = benchmark["benchmark_yield"]
    conservative_price = mkt.get("conservative_price", 1500)

    safe_limit = total_area_acres * benchmark_yield * conservative_price * haircut
    safe_limit_min = safe_limit * 0.85
    safe_limit_max = safe_limit * 1.15

    return {
        "safe_credit_limit": round(safe_limit, 0),
        "safe_credit_limit_min": round(safe_limit_min, 0),
        "safe_credit_limit_max": round(safe_limit_max, 0),
        "formula": "Acreage × NHB Benchmark Yield × Conservative AGMARKNET Price × Risk Haircut",
        "inputs": {
            "acreage": total_area_acres,
            "nhb_benchmark_yield_q_per_acre": benchmark_yield,
            "conservative_agmarknet_price_per_quintal": conservative_price,
            "risk_haircut": haircut,
            "risk_haircut_description": haircut_desc,
            "agricultural_risk_score": agri_risk_score,
        },
        "data_sources": {
            "benchmark": benchmark["source"],
            "market": mkt.get("source", "DEMO/SYNTHETIC"),
        },
    }


# ─────────────────────────────────────────────
# CREDIT PURPOSE RECOMMENDATION
# ─────────────────────────────────────────────

CROP_PURPOSE_MAP = {
    "wheat":    ("seeds, fertilizer, irrigation, crop protection", "Pre-sowing inputs for Rabi wheat season"),
    "rice":     ("seeds, fertilizer, irrigation, transplanting labour", "Kharif paddy cultivation inputs"),
    "soybean":  ("seeds, fertilizer, crop protection", "Kharif soybean sowing inputs"),
    "cotton":   ("seeds, fertilizer, pest management, drip irrigation", "Long-duration cotton crop inputs"),
    "maize":    ("seeds, fertilizer, irrigation", "Kharif/Rabi maize inputs"),
    "default":  ("seeds, fertilizer, irrigation, working capital", "General crop cultivation inputs"),
}

def recommend_credit_purpose(crop: str) -> Dict[str, str]:
    crop_lower = crop.lower()
    purpose, why = CROP_PURPOSE_MAP.get(crop_lower, CROP_PURPOSE_MAP["default"])
    return {
        "recommended_purpose": purpose,
        "why": why,
        "note": "Credit purpose is recommended based on crop and season. Farmer and lender should agree on final purpose.",
    }


# ─────────────────────────────────────────────
# MASTER PASSPORT GENERATION
# ─────────────────────────────────────────────

def generate_trust_passport(farmer: Farmer, db: Session) -> TrustPassport:
    """
    Generate or refresh a Trust Passport for a farmer.
    All calculations are transparent — no black-box.
    """
    farms = farmer.farms
    production_records = farmer.production_records
    sales_records = farmer.sales_records
    memberships = farmer.fpo_memberships
    verifications = farmer.verifications

    # Determine primary crop and area
    primary_crop = farmer.production_records[0].crop_type if production_records else "wheat"
    total_area = sum(f.total_area_acres for f in farms) if farms else (farmer.farm_size or 2.0)
    state = farmer.state

    # ── Score each component ──
    prod_data = score_production_stability(production_records, verifications)
    mkt_data  = score_market_stability(primary_crop, state, sales_records)
    rep_data  = calculate_repayment_capacity(primary_crop, total_area, state)
    risk_data = score_agricultural_risk(primary_crop, state, farms)
    fpo_data  = score_fpo_community(memberships, verifications)

    # ── Weighted overall score ──
    overall = (
        settings.WEIGHT_PRODUCTION_STABILITY * prod_data["score"] +
        settings.WEIGHT_MARKET_STABILITY     * mkt_data["score"]  +
        settings.WEIGHT_REPAYMENT_CAPACITY   * rep_data["score"]  +
        settings.WEIGHT_AGRICULTURAL_RISK    * risk_data["score"] +
        settings.WEIGHT_FPO_COMMUNITY        * fpo_data["score"]
    )
    overall = round(min(100, max(0, overall)), 1)

    # ── Safe credit limit ──
    credit_data = calculate_safe_credit_limit(primary_crop, total_area, state, risk_data["score"])

    # ── Purpose recommendation ──
    purpose_data = recommend_credit_purpose(primary_crop)

    # ── Build explanation dict ──
    score_breakdown = [
        {
            "component": "Production Stability",
            "score": prod_data["score"],
            "weight": settings.WEIGHT_PRODUCTION_STABILITY,
            "contribution": round(settings.WEIGHT_PRODUCTION_STABILITY * prod_data["score"], 2),
            "reason": prod_data["reason"],
            "inputs": prod_data["inputs"],
            "data_source": prod_data["data_source"],
            "verification_status": prod_data["verification_status"],
        },
        {
            "component": "Market Stability",
            "score": mkt_data["score"],
            "weight": settings.WEIGHT_MARKET_STABILITY,
            "contribution": round(settings.WEIGHT_MARKET_STABILITY * mkt_data["score"], 2),
            "reason": mkt_data["reason"],
            "inputs": mkt_data["inputs"],
            "data_source": mkt_data["data_source"],
            "verification_status": mkt_data["verification_status"],
        },
        {
            "component": "Repayment Capacity",
            "score": rep_data["score"],
            "weight": settings.WEIGHT_REPAYMENT_CAPACITY,
            "contribution": round(settings.WEIGHT_REPAYMENT_CAPACITY * rep_data["score"], 2),
            "reason": rep_data["reason"],
            "inputs": rep_data["inputs"],
            "data_source": rep_data["data_source"],
            "verification_status": rep_data["verification_status"],
        },
        {
            "component": "Agricultural Risk",
            "score": risk_data["score"],
            "weight": settings.WEIGHT_AGRICULTURAL_RISK,
            "contribution": round(settings.WEIGHT_AGRICULTURAL_RISK * risk_data["score"], 2),
            "reason": risk_data["reason"],
            "inputs": risk_data["inputs"],
            "data_source": risk_data["data_source"],
            "verification_status": risk_data["verification_status"],
        },
        {
            "component": "FPO Community",
            "score": fpo_data["score"],
            "weight": settings.WEIGHT_FPO_COMMUNITY,
            "contribution": round(settings.WEIGHT_FPO_COMMUNITY * fpo_data["score"], 2),
            "reason": fpo_data["reason"],
            "inputs": fpo_data["inputs"],
            "data_source": fpo_data["data_source"],
            "verification_status": fpo_data["verification_status"],
        },
    ]

    explanation = {
        "overall_creditworthiness": overall,
        "methodology": "Transparent weighted scorecard — 5 components, no black-box",
        "weights": {
            "production_stability": settings.WEIGHT_PRODUCTION_STABILITY,
            "market_stability":     settings.WEIGHT_MARKET_STABILITY,
            "repayment_capacity":   settings.WEIGHT_REPAYMENT_CAPACITY,
            "agricultural_risk":    settings.WEIGHT_AGRICULTURAL_RISK,
            "fpo_community":        settings.WEIGHT_FPO_COMMUNITY,
        },
        "safe_credit_limit": credit_data,
        "credit_purpose": purpose_data,
        "lender_note": "KisanSetu provides an explainable agricultural credit profile. The lender makes the final underwriting and approval decision.",
        "data_caveat": "Market and benchmark data sourced from DEMO/SYNTHETIC dataset. Not live government data.",
    }

    # ── Save / update passport ──
    existing = db.query(TrustPassport).filter(TrustPassport.farmer_id == farmer.id).first()
    if existing:
        passport = existing
    else:
        passport = TrustPassport(farmer_id=farmer.id)
        db.add(passport)

    passport.generated_at = datetime.utcnow()
    passport.methodology_version = settings.SCORING_VERSION
    passport.production_stability_score     = prod_data["score"]
    passport.market_stability_score         = mkt_data["score"]
    passport.repayment_capacity_score       = rep_data["score"]
    passport.agricultural_risk_score        = risk_data["score"]
    passport.fpo_community_score            = fpo_data["score"]
    passport.overall_creditworthiness       = overall
    passport.expected_crop_revenue          = rep_data["expected_revenue"]
    passport.estimated_cultivation_cost     = rep_data["cultivation_cost"]
    passport.expected_net_agricultural_income = rep_data["net_income"]
    passport.repayment_coverage             = rep_data.get("repayment_coverage")
    passport.safe_credit_limit              = credit_data["safe_credit_limit"]
    passport.safe_credit_limit_min          = credit_data["safe_credit_limit_min"]
    passport.safe_credit_limit_max          = credit_data["safe_credit_limit_max"]
    passport.recommended_credit_purpose     = purpose_data["recommended_purpose"]
    passport.explanation                    = explanation
    passport.score_breakdown                = score_breakdown
    passport.data_sources_used              = ["farmer_provided", "fpo_verified", "NHB_benchmark", "AGMARKNET_demo", "PMFBY_demo"]
    passport.assumptions = {
        "primary_crop": primary_crop,
        "total_area_acres": total_area,
        "state": state,
        "note": "Scores calculated from available data. More verified records improve accuracy.",
    }

    db.commit()
    db.refresh(passport)
    logger.info(f"Trust Passport generated for farmer {farmer.id}: score={overall}")
    return passport
