import pytest
from app.core.market import get_market_reference
from app.models.farmer import Farmer
from app.models.fpo_verification import FPOVerification
from app.services.credit_engine import compute_passport


def test_deterministic_credit_engine_formula():
    """Verify that Safe Credit Limit is computed deterministically."""
    farmer = Farmer(
        name="Test Farmer",
        mobile="9800000001",
        village="Krishnapur",
        district="Nashik",
        state="Maharashtra",
        acreage=3.5,
        primary_crop="paddy",
        crop_season="Kharif",
        fpo_membership="Krishak FPO",
        crop_insured=True,
        insurance_sum_assured=100000.0,
        farm_experience_years=6,
    )
    verif = FPOVerification(
        verification_status="verified",
        member_integrity_flag=True,
    )
    result = compute_passport(farmer, verif, repayment_demand=0.0)

    market = get_market_reference("paddy")
    expected_gross = round(3.5 * market["yield_per_acre"] * market["benchmark_price"], 2)

    assert result.yield_per_acre == market["yield_per_acre"]
    assert result.benchmark_price == market["benchmark_price"]
    assert result.gross_income == expected_gross
    assert result.risk_haircut == 0.15  # verified + member integrity flag
    assert result.safe_credit_limit > 0
    assert result.safe_credit_limit <= expected_gross


def test_risk_haircut_variations():
    """Verify that haircut adjusts according to FPO verification status."""
    farmer = Farmer(acreage=2.0, primary_crop="wheat", village="V", district="D", state="S")

    # Unverified
    res_none = compute_passport(farmer, None, 0.0)
    assert res_none.risk_haircut == 0.20

    # Verified without integrity flag
    verif_no_flag = FPOVerification(verification_status="verified", member_integrity_flag=False)
    res_no_flag = compute_passport(farmer, verif_no_flag, 0.0)
    assert res_no_flag.risk_haircut == 0.20

    # Verified with integrity flag
    verif_flag = FPOVerification(verification_status="verified", member_integrity_flag=True)
    res_flag = compute_passport(farmer, verif_flag, 0.0)
    assert res_flag.risk_haircut == 0.15

    # Rejected
    verif_rejected = FPOVerification(verification_status="rejected", member_integrity_flag=False)
    res_rej = compute_passport(farmer, verif_rejected, 0.0)
    assert res_rej.risk_haircut == 0.35


def test_component_scores_bounds():
    """Verify that all 7 component scores fall strictly within [0, 100]."""
    farmer = Farmer(
        name="Score Farmer",
        mobile="9800000002",
        village="Village",
        district="District",
        state="State",
        acreage=5.0,
        primary_crop="cotton",
        fpo_membership="FPO",
        crop_insured=True,
    )
    verif = FPOVerification(verification_status="verified", member_integrity_flag=True)
    result = compute_passport(farmer, verif, repayment_demand=50000.0)

    for score_key, score_val in result.component_scores.items():
        assert 0.0 <= score_val <= 100.0, f"Score {score_key}={score_val} out of bounds"
