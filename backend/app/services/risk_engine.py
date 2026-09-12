"""Explainable agricultural-risk engine and repayment-capacity credit range.

Answers the missions' lending questions on a transparent, auditable basis:

  Q1 Who is trustworthy?      -> community_trust factor (FPO verification)
  Q2 How much credit?         -> credit_capacity_range() (TDSR capacity bounds)
  Q3 What should it be used for? -> purpose steering surfaced via loan funding
  Q4 Can they repay?          -> repayment_capacity vs total payable (underwrite)
  Q5 How does community help? -> FPO integrity flag de-risks the assessment
  Q6 Data ownership?          -> all analysis uses consent-gated attributes

The model is a deterministic factor scorecard (production stability, market
price, crop condition/insurance, community trust, debt repayment). Every
score maps to a human-readable reason, so the output is explainable by
construction rather than proxy-interpreted from a black box.

SIMULATED-AI NOTE: for the MVP the "AI risk engine" is expressed as this
transparent scorecard (model_version `kisansetu-risk-v1`) instead of a fitted
black-box model, which is the defensible choice when every credit decision
must be auditable and there is no local training corpus yet. The adapter
boundary (production -> market -> condition -> community -> debt) is identical
to what a trained model would expose, so swapping in a fitted model later is a
one-file change.
"""
from typing import Dict, List, Optional, Tuple

from app.core.market import (
    PRODUCTION_COST_RATIO,
    get_market_reference,
    get_market_risk,
)
from app.models.farmer import Farmer, ProductionRecord
from app.models.fpo_verification import FPOVerification
from app.services.credit_engine import compute_repayment_demand

MODEL_VERSION = "kisansetu-risk-v1"

# Factor weights (sum to 1.0). Each factor is scored 0-100 where higher = riskier.
FACTOR_WEIGHTS: Dict[str, float] = {
    "production_stability": 0.30,
    "market_price": 0.25,
    "crop_condition": 0.20,
    "community_trust": 0.15,
    "debt_repayment": 0.10,
}

# TDSR bounds as a share of monthly crop income: what a defensible lender services.
TDSR_LOW = 0.40
TDSR_HIGH = 0.55
INCOME_RECOGNITION_MONTHS = 6.0  # crop-cycle income realized across ~6 harvest months

# Risk-tier -> credit discount on top of capacity pricing.
RISK_TIER_DISCOUNT = {"low": 0.0, "medium": 0.12, "high": 0.26}
RISK_TIER_BREAKPOINTS = {"high": 55.0, "medium": 30.0}  # >high high, >medium med, else low

INSURANCE_UPLIFT = 0.05  # risk-transfer mitigant added when crop insurance exists

COMMUNITY_VOUCH_DISCOUNT = 0.06  # FPO first-loss style guarantee reduces the risk discount

# Purpose steering taxonomy (Q3: what should the credit be used for?).
# Productive purposes that convert into repayable crop income get the full
# capacity; discretionary/consumption asks are capped lower and steered.
PURPOSE_TAXONOMY: Dict[str, Dict] = {
    "input_finance": {"alignment": 1.00, "note": "Seeds, fertiliser, crop inputs — directly converts to income."},
    "production_capital": {"alignment": 0.95, "note": "Irrigation, mechanisation, land development."},
    "horticulture_expansion": {"alignment": 0.90, "note": "High-value horticulture expansion."},
    "post_harvest": {"alignment": 0.88, "note": "Storage/cold-chain post-harvest infrastructure."},
    "working_capital": {"alignment": 0.85, "note": "Seasonal working capital."},
    "equipment": {"alignment": 0.82, "note": "Equipment and implements."},
    "consumption": {"alignment": 0.70, "note": "Consumption/emergency — steered toward smaller ticket or savings."},
}
DEFAULT_PURPOSE = "working_capital"


def purpose_grade(purpose_category: str) -> Dict:
    key = (purpose_category or DEFAULT_PURPOSE).strip().lower()
    if key not in PURPOSE_TAXONOMY:
        key = DEFAULT_PURPOSE
    entry = PURPOSE_TAXONOMY[key]
    tier = (
        "productive"
        if entry["alignment"] >= 0.9
        else "neutral"
        if entry["alignment"] >= 0.8
        else "guardrail"
    )
    return {"category": key, "alignment": entry["alignment"], "tier": tier, "note": entry["note"]}


def _production_stability(farmer: Farmer) -> Tuple[float, str]:
    records: List[ProductionRecord] = farmer.production_records or []
    if not records:
        return 62.0, "No production history on record — yield evidence gap raises uncertainty."
    yields = [r.quantity / max(farmer.acreage, 0.01) for r in records]
    mean = sum(yields) / len(yields)
    var = sum((y - mean) ** 2 for y in yields) / len(yields)
    cv = (var ** 0.5 / mean) * 100.0 if mean > 0 else 100.0
    if cv <= 10:
        base = 20.0
    elif cv <= 25:
        base = 32.0
    elif cv <= 50:
        base = 50.0
    else:
        base = 72.0
    verified_frac = sum(1 for r in records if r.verified) / len(records)
    if verified_frac >= 0.75:
        base -= 8.0
    elif verified_frac == 0:
        base += 5.0
    msg = (
        f"{len(records)} recorded season(s); yield CV {cv:.0f}%, "
        f"{int(verified_frac * 100)}% verified."
    )
    return round(min(95.0, max(10.0, base)), 1), msg


def _market_price(farmer: Farmer) -> Tuple[float, str]:
    mr = get_market_risk(farmer.primary_crop or "other")
    base = float(mr["volatility"])
    if mr["msp_gap_ratio"] is not None:
        if mr["msp_gap_ratio"] >= 1.0:
            base -= 15.0
            note = "trades above the MSP floor (support holding)"
        else:
            base += 18.0
            note = f"trades below MSP floor (gap ratio {mr['msp_gap_ratio']})"
    else:
        base += 10.0
        note = "no MSP floor — full market risk"
    msg = (
        f"'{mr['crop']}' market volatility band is {mr['volatility']}/100; {note} "
        f"(modal ₹{mr['modal_price']:,.0f}/q)."
    )
    return round(min(95.0, max(5.0, base)), 1), msg


def _crop_condition(farmer: Farmer) -> Tuple[float, str]:
    records: List[ProductionRecord] = farmer.production_records or []
    base = 35.0
    notes = []
    if records:
        distressed = sum(1 for r in records if r.weather_distress_observed)
        base += 40.0 * (distressed / len(records))
        if distressed:
            notes.append(f"{distressed}/{len(records)} seasons flagged weather distress")
    else:
        base += 10.0
        notes.append("no field-condition telemetry on record")

    gross = farmer.acreage * get_market_reference(farmer.primary_crop or "other")["yield_per_acre"] \
        * get_market_reference(farmer.primary_crop or "other")["modal_price"]
    if farmer.crop_insured:
        base -= 25.0
        notes.append("crop insured")
        if farmer.insurance_sum_assured and farmer.insurance_sum_assured >= 0.5 * gross:
            base -= 10.0
            notes.append("insurance sum covers ≥50% of expected gross value")
    else:
        base += 12.0
        notes.append("no crop insurance — downside risk unmitigated")

    msg = "; ".join(notes) if notes else "no coverage signals"
    return round(min(95.0, max(5.0, base)), 1), msg


def _community_trust(verification: Optional[FPOVerification], farmer: Farmer) -> Tuple[float, str]:
    if verification is None:
        base = 60.0
        msg = "No FPO community verification yet — trust rests only on self-reported data."
    elif verification.verification_status == "verified":
        base = 18.0 if verification.member_integrity_flag else 40.0
        msg = (
            "FPO community verification passed with member integrity flag."
            if verification.member_integrity_flag
            else "FPO verification passed (integrity flag not yet confirmed)."
        )
    elif verification.verification_status == "rejected":
        base = 90.0
        msg = "FPO community flagged integrity concerns — high community distrust."
    else:
        base = 50.0
        msg = "FPO verification is pending community review."
    if farmer.farm_experience_years:
        base -= min(8.0, farmer.farm_experience_years)
        msg += f" {farmer.farm_experience_years} yrs farming experience noted."
    return round(min(95.0, max(5.0, base)), 1), msg


def _debt_repayment(farmer: Farmer, repayment_demand: float, net_income: float) -> Tuple[float, str]:
    if repayment_demand <= 0:
        return 10.0, "No outstanding repayment demand — clean debt position."
    ratio = repayment_demand / net_income if net_income > 0 else 2.0
    if ratio <= 0.2:
        base = 25.0
    elif ratio <= 0.5:
        base = 45.0
    elif ratio <= 0.8:
        base = 70.0
    else:
        base = 90.0
    msg = (
        f"Existing repayment demand of ₹{repayment_demand:,.0f} equals "
        f"{ratio * 100:.0f}% of expected net crop income."
    )
    return round(base, 1), msg


def agricultural_risk(
    farmer: Farmer,
    verification: Optional[FPOVerification],
    repayment_demand: float,
) -> Dict:
    market = get_market_reference(farmer.primary_crop or "other")
    net_income = round(
        farmer.acreage * market["yield_per_acre"] * market["modal_price"] * (1.0 - PRODUCTION_COST_RATIO),
        2,
    )

    scores: Dict[str, float] = {}
    reasons: Dict[str, str] = {}
    scores["production_stability"], reasons["production_stability"] = _production_stability(farmer)
    scores["market_price"], reasons["market_price"] = _market_price(farmer)
    scores["crop_condition"], reasons["crop_condition"] = _crop_condition(farmer)
    scores["community_trust"], reasons["community_trust"] = _community_trust(verification, farmer)
    scores["debt_repayment"], reasons["debt_repayment"] = _debt_repayment(farmer, repayment_demand, net_income)

    risk_score = round(
        sum(scores[k] * FACTOR_WEIGHTS[k] for k in FACTOR_WEIGHTS),
        1,
    )
    tier = (
        "high"
        if risk_score > RISK_TIER_BREAKPOINTS["high"]
        else "medium"
        if risk_score > RISK_TIER_BREAKPOINTS["medium"]
        else "low"
    )

    ranked = sorted(
        ((scores[k] * FACTOR_WEIGHTS[k], k) for k in FACTOR_WEIGHTS),
        reverse=True,
    )
    top_reasons = [
        {
            "factor": k,
            "impact_pct": round(100.0 * FACTOR_WEIGHTS[k]),
            "score": scores[k],
            "reason": reasons[k],
        }
        for _, k in ranked[:3]
    ]

    return {
        "risk_tier": tier,
        "risk_score": risk_score,
        "factor_scores": scores,
        "factor_weights": FACTOR_WEIGHTS,
        "factor_reasons": reasons,
        "top_reasons": top_reasons,
        "net_income_expected": net_income,
        "model_version": MODEL_VERSION,
    }


def credit_capacity_range(
    farmer: Farmer,
    verification: Optional[FPOVerification],
    repayment_demand: float,
    tenure_months: int = 12,
    annual_interest_rate: float = 0.135,
    community_vouch: bool = False,
) -> Dict:
    market = get_market_reference(farmer.primary_crop or "other")
    net_income = round(
        farmer.acreage * market["yield_per_acre"] * market["modal_price"] * (1.0 - PRODUCTION_COST_RATIO),
        2,
    )
    risk = agricultural_risk(farmer, verification, repayment_demand)

    # Monthly repayment capacity from expected net crop income.
    monthly_capacity = net_income / INCOME_RECOGNITION_MONTHS
    monthly_demand = repayment_demand / 12.0
    servicing_low = max(0.0, monthly_capacity * TDSR_LOW - monthly_demand)
    servicing_high = max(servicing_low, monthly_capacity * TDSR_HIGH - monthly_demand)

    # Invert the EMI annuity to get the principal each servicing budget supports.
    r = annual_interest_rate / 12.0
    n = tenure_months
    emi_factor = (r * (1 + r) ** n) / ((1 + r) ** n - 1.0) if r > 0 else 1.0 / n
    p_low = servicing_low / emi_factor
    p_high = servicing_high / emi_factor

    discount = max(0.0, RISK_TIER_DISCOUNT[risk["risk_tier"]] - (COMMUNITY_VOUCH_DISCOUNT if community_vouch else 0.0))
    uplift = INSURANCE_UPLIFT if farmer.crop_insured else 0.0
    factor = (1.0 - discount) * (1.0 + uplift)

    low = round_to(p_low * factor, 1000, mode="floor")
    high = round_to(p_high * factor, 1000, mode="ceil")
    if high < low:
        high = low
    recommended = round_to((low + high) / 2.0, 1000, mode="round")
    recommended = min(max(recommended, low), high)

    coverage = None
    if repayment_demand and repayment_demand > 0:
        coverage = round(net_income / repayment_demand, 2)

    return {
        "range_low": low,
        "range_high": high,
        "recommended_credit": recommended,
        "servicing_tdsr_low": TDSR_LOW,
        "servicing_tdsr_high": TDSR_HIGH,
        "income_recognition_months": INCOME_RECOGNITION_MONTHS,
        "monthly_capacity": round(monthly_capacity, 2),
        "monthly_repayment_demand": round(monthly_demand, 2),
        "net_income_expected": net_income,
        "annual_interest_rate": annual_interest_rate,
        "tenure_months": tenure_months,
        "risk_discount": discount,
        "insurance_uplift": uplift,
        "community_vouch": community_vouch,
        "repayment_coverage": coverage,
        "agri_risk": risk,
    }


def round_to(value: float, step: int, mode: str = "round") -> int:
    if value <= 0:
        return 0
    if mode == "floor":
        return int(value // step * step)
    if mode == "ceil":
        return int(-(-value // step) * step)
    return int(round(value / step) * step)


def repayment_capacity_amount(
    farmer: Farmer,
    verification: Optional[FPOVerification],
    repayment_demand: float,
    requested_amount: float,
    tenure_months: int,
    annual_interest_rate: float,
    community_vouch: bool = False,
    purpose_category: str = None,
) -> Dict:
    """Underwrite-style decision based on the capacity range (Q2/Q3/Q4 wiring)."""
    capacity = credit_capacity_range(
        farmer,
        verification,
        repayment_demand,
        tenure_months,
        annual_interest_rate,
        community_vouch,
    )
    purpose = purpose_grade(purpose_category)
    high = round(capacity["range_high"] * purpose["alignment"], 0)
    low = capacity["range_low"]
    if purpose["tier"] == "guardrail" and purpose["category"] == "consumption":
        high = min(high, 30000.0)

    if requested_amount <= high:
        decision = "approved"
        reason = (
            f"Requested ₹{requested_amount:,.0f} is serviced within the defensible range "
            f"₹{low:,.0f}–₹{capacity['range_high']:,.0f} for '{(purpose['category'])}'. "
            f"{purpose['note']}"
        )
    elif requested_amount <= capacity["range_high"] * 1.15:
        decision = "adjust"
        reason = (
            f"Request exceeds the purpose-aligned ceiling ₹{high:,.0f}. Borrowing "
            f"within ₹{low:,.0f}–₹{capacity['range_high']:,.0f} keeps repayments covered."
        )
    else:
        decision = "declined"
        reason = (
            f"Request far exceeds repayment capacity (ceiling ₹{capacity['range_high']:,.0f} "
            f"of ₹{capacity['net_income_expected']:,.0f} expected net income)."
        )
    return decision, reason, capacity, purpose


def assess(db, farmer: Farmer) -> Dict:
    """Orchestrate a full assessment and persist an auditable snapshot."""
    from app.models.farmer import CreditApplication
    from app.models.fpo_vouch import FpoVouch
    from app.models.risk_assessment import RiskAssessment

    verification = (
        db.query(FPOVerification)
        .filter(FPOVerification.farmer_id == farmer.id)
        .order_by(FPOVerification.id.desc())
        .first()
    )
    demand = compute_repayment_demand(
        db.query(CreditApplication)
        .filter(CreditApplication.farmer_id == farmer.id)
        .all()
    )
    community_vouch = (
        db.query(FpoVouch)
        .filter(FpoVouch.farmer_id == farmer.id, FpoVouch.status == "active")
        .first()
        is not None
    )
    capacity = credit_capacity_range(farmer, verification, demand, community_vouch=community_vouch)
    risk = capacity["agri_risk"]
    risk["community_vouch"] = community_vouch

    snapshot = RiskAssessment(
        farmer_id=farmer.id,
        risk_tier=risk["risk_tier"],
        risk_score=risk["risk_score"],
        factor_scores=risk["factor_scores"],
        factor_weights=risk["factor_weights"],
        top_reasons=risk["top_reasons"],
        recommended_range_low=capacity["range_low"],
        recommended_range_high=capacity["range_high"],
        recommended_credit=capacity["recommended_credit"],
        servicing_tdsr_low=capacity["servicing_tdsr_low"],
        servicing_tdsr_high=capacity["servicing_tdsr_high"],
        net_income_expected=capacity["net_income_expected"],
        repayment_capacity=capacity["monthly_capacity"],
        insurance_uplift=capacity["insurance_uplift"],
        model_version=MODEL_VERSION,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {
        "assessment_id": snapshot.id,
        "farmer_id": farmer.farmer_id,
        "assessed_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        **capacity,
    }


def mission_answers(db, farmer: Farmer, assessment: Dict) -> List[Dict]:
    """The six lending questions answered from the farmer's live assessment.

    Every answer carries the evidence it was derived from (explainability +
    auditability requirement of the expected outcomes).
    """
    risk = assessment["agri_risk"]
    verification = (
        db.query(FPOVerification)
        .filter(FPOVerification.farmer_id == farmer.id)
        .order_by(FPOVerification.id.desc())
        .first()
    )
    coverage = assessment.get("repayment_coverage")
    demand = (assessment.get("monthly_repayment_demand") or 0.0) * 12.0

    answers = [
        {
            "question": "Q1 · Who is a trustworthy borrower?",
            "answer": f"Community-verified medium confidence: FPO verification is "
            f"'{getattr(verification, 'verification_status', 'missing')}' "
            f"(integrity flag {getattr(verification, 'member_integrity_flag', False)}). "
            f"Trust factor score {risk['factor_scores']['community_trust']}/100 (lower = safer).",
            "evidence": risk["factor_reasons"]["community_trust"],
        },
        {
            "question": "Q2 · How much credit can safely be extended?",
            "answer": (
                f"₹{assessment['range_low']:,.0f}–₹{assessment['range_high']:,.0f} for a "
                f"{assessment['tenure_months']}-month crop loan at "
                f"{assessment['annual_interest_rate'] * 100:.1f}% p.a.; recommended "
                f"₹{assessment['recommended_credit']:,.0f}. Bounded by a "
                f"{assessment['servicing_tdsr_low'] * 100:.0f}–{assessment['servicing_tdsr_high'] * 100:.0f}% "
                f"debt-service ratio on expected net crop income."
            ),
            "evidence": f"net income ₹{assessment['net_income_expected']:,.0f}; "
                        f"risk discount {assessment['risk_discount'] * 100:.0f}%",
        },
        {
            "question": "Q3 · What should the credit be used for?",
            "answer": (
                "Productive uses (inputs, production capital, horticulture) qualify for the full "
                "capacity. Ask for a purpose when raising the loan and the system steers "
                "consumption/emergency asks toward smaller tickets or savings."
            ),
            "evidence": "purpose taxonomy alignment 0.70–1.00 applied at underwrite",
        },
        {
            "question": "Q4 · Can the farmer repay from expected crop/market income?",
            "answer": (
                f"Expected net crop income ₹{assessment['net_income_expected']:,.0f} over the cycle; "
                f"monthly capacity ₹{assessment['monthly_capacity']:,.0f}. "
                + (
                    f"Existing repayment demand ₹{demand:,.0f} gives coverage {coverage}x."
                    if coverage is not None
                    else "No existing repayment demand."
                )
            ),
            "evidence": "repayment capacity vs monthly demand checked at the underwrite stage",
        },
        {
            "question": "Q5 · How can the community reduce lending risk?",
            "answer": (
                f"The FPO verifies members and can issue a vouch (first-loss-style guarantee). "
                f"Community vouch active: {risk.get('community_vouch', False)} — when active it "
                f"reduces the risk discount by {COMMUNITY_VOUCH_DISCOUNT * 100:.0f} points, lifting "
                f"the safe range and cutting the borrower's credit cost."
            ),
            "evidence": "member verification + integrity flag + active vouches",
        },
        {
            "question": "Q6 · Better credit without surrendering data ownership?",
            "answer": (
                "The farmer keeps ownership: the lender only sees consent-gated, masked attributes "
                "(visible via the consent panel), and every credit figure is derived from the "
                "farmer's own passport + community data — not sold to lenders. Revocation applies "
                "immediately."
            ),
            "evidence": "consent grants + attribute masking + revocable grants",
        },
    ]
    return answers