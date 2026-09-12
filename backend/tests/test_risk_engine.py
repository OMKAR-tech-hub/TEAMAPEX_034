import pytest
from app.models.farmer import Farmer
from app.models.fpo_verification import FPOVerification
from app.services.risk_engine import (
    assess,
    credit_capacity_range,
    purpose_grade,
    repayment_capacity_amount,
    PURPOSE_TAXONOMY,
)


def test_purpose_steering_taxonomy():
    """Verify purpose categories match taxonomy and alignment weights."""
    input_fin = purpose_grade("input_finance")
    assert input_fin["tier"] == "productive"
    assert input_fin["alignment"] == 1.00

    consumption = purpose_grade("consumption")
    assert consumption["tier"] == "guardrail"
    assert consumption["alignment"] == 0.70

    unknown = purpose_grade("arbitrary_unknown")
    assert unknown["category"] == "working_capital"


def test_risk_scorecard_and_tdsr_bounds(db, seed_actors):
    """Verify TDSR bounds (0.40 to 0.55) and factor scorecard generation."""
    farmer = seed_actors["farmer"]
    verif = FPOVerification(verification_status="verified", member_integrity_flag=True)

    capacity = credit_capacity_range(farmer, verif, repayment_demand=0.0)
    assert capacity["range_low"] < capacity["range_high"]
    assert capacity["servicing_tdsr_low"] == 0.40
    assert capacity["servicing_tdsr_high"] == 0.55
    assert capacity["recommended_credit"] >= capacity["range_low"]
    assert capacity["recommended_credit"] <= capacity["range_high"]

    agri_risk = capacity["agri_risk"]
    assert agri_risk["risk_tier"] in ("low", "medium", "high")
    assert len(agri_risk["factor_scores"]) == 5
    for factor in ["production_stability", "market_price", "crop_condition", "community_trust", "debt_repayment"]:
        assert factor in agri_risk["factor_scores"]


def test_insurance_uplift_effect(db, seed_actors):
    """Verify crop insurance transfers risk and lowers risk discount."""
    farmer = seed_actors["farmer"]
    verif = FPOVerification(verification_status="verified", member_integrity_flag=True)

    farmer.crop_insured = False
    cap_no_ins = credit_capacity_range(farmer, verif, 0.0)

    farmer.crop_insured = True
    cap_ins = credit_capacity_range(farmer, verif, 0.0)

    assert cap_ins["insurance_uplift"] == 0.05
    assert cap_no_ins["insurance_uplift"] == 0.0
