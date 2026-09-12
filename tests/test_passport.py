"""Tests: Trust Passport scoring, safe credit limit, repayment capacity"""
import pytest
from backend.services.passport_engine import (
    score_production_stability, score_market_stability,
    calculate_repayment_capacity, score_agricultural_risk,
    score_fpo_community, calculate_safe_credit_limit,
    get_risk_haircut, recommend_credit_purpose,
)
from backend.services.market_intelligence import (
    calculate_market_stats, get_benchmark_yield, get_weather_risk,
)


class TestProductionStability:
    def test_no_records_returns_baseline(self):
        result = score_production_stability([], [])
        assert result["score"] == 20.0
        assert result["inputs"]["num_records"] == 0

    def test_score_increases_with_records(self):
        from unittest.mock import MagicMock
        rec = MagicMock()
        rec.fpo_verified = True
        rec.quantity = 80.0
        rec.area_acres = 5.0
        result = score_production_stability([rec, rec, rec], [])
        assert result["score"] > 20.0

    def test_fpo_verified_increases_score(self):
        from unittest.mock import MagicMock
        rec_verified = MagicMock(); rec_verified.fpo_verified = True; rec_verified.quantity = 80; rec_verified.area_acres = 5
        rec_unverified = MagicMock(); rec_unverified.fpo_verified = False; rec_unverified.quantity = 70; rec_unverified.area_acres = 5
        s_verified = score_production_stability([rec_verified], [])
        s_unverified = score_production_stability([rec_unverified], [])
        assert s_verified["score"] > s_unverified["score"]


class TestSafeCreditLimit:
    def test_formula_correct(self):
        """Safe limit = area × benchmark_yield × conservative_price × haircut"""
        result = calculate_safe_credit_limit("wheat", 5.0, "Madhya Pradesh", 80.0)
        assert result["safe_credit_limit"] > 0
        inp = result["inputs"]
        expected = inp["acreage"] * inp["nhb_benchmark_yield_q_per_acre"] * inp["conservative_agmarknet_price_per_quintal"] * inp["risk_haircut"]
        assert abs(result["safe_credit_limit"] - expected) < 1

    def test_higher_risk_score_means_lower_haircut(self):
        r_high = calculate_safe_credit_limit("wheat", 5.0, "Madhya Pradesh", 90.0)
        r_low  = calculate_safe_credit_limit("wheat", 5.0, "Madhya Pradesh", 30.0)
        assert r_high["safe_credit_limit"] > r_low["safe_credit_limit"]

    def test_haircut_table_coverage(self):
        for score, expected_haircut in [(95, 1.00), (80, 0.90), (65, 0.75), (50, 0.60), (20, 0.45)]:
            haircut, _ = get_risk_haircut(score)
            assert haircut == expected_haircut, f"score={score} expected={expected_haircut} got={haircut}"


class TestRepaymentCapacity:
    def test_repayment_calculation_returns_positive_income(self):
        result = calculate_repayment_capacity("wheat", 5.0, "Madhya Pradesh")
        assert result["expected_revenue"] > 0
        assert result["cultivation_cost"] > 0
        assert result["net_income"] == pytest.approx(result["expected_revenue"] - result["cultivation_cost"], rel=0.01)

    def test_repayment_coverage_calculated_when_proposed(self):
        result = calculate_repayment_capacity("wheat", 5.0, "Madhya Pradesh", proposed_repayment=50000)
        assert result["repayment_coverage"] is not None
        assert result["repayment_coverage"] == pytest.approx(result["net_income"] / 50000, rel=0.01)

    def test_score_high_when_coverage_high(self):
        high = calculate_repayment_capacity("wheat", 10.0, "Madhya Pradesh", proposed_repayment=10000)
        low  = calculate_repayment_capacity("wheat", 1.0,  "Madhya Pradesh", proposed_repayment=500000)
        assert high["score"] > low["score"]


class TestFPOCommunity:
    def test_no_membership_low_score(self):
        result = score_fpo_community([], [])
        assert result["score"] == 0.0

    def test_active_membership_adds_score(self):
        from unittest.mock import MagicMock
        m = MagicMock(); m.status.value = "active"
        result = score_fpo_community([m], [])
        assert result["score"] >= 40.0


class TestMarketIntelligence:
    def test_get_benchmark_yield_known_crop(self):
        b = get_benchmark_yield("wheat")
        assert b["benchmark_yield"] == 16.0

    def test_get_benchmark_yield_unknown_crop_returns_default(self):
        b = get_benchmark_yield("unknowncrop")
        assert b["benchmark_yield"] == 12.0

    def test_market_stats_returns_stability_score(self):
        result = calculate_market_stats("wheat")
        assert "market_stability_score" in result
        assert 0 <= result["market_stability_score"] <= 100

    def test_market_stats_no_data_returns_fallback(self):
        result = calculate_market_stats("unknowncrop999")
        assert result["data_available"] == False


class TestCreditPurpose:
    def test_wheat_gets_seeds_recommendation(self):
        result = recommend_credit_purpose("wheat")
        assert "seeds" in result["recommended_purpose"].lower()

    def test_unknown_crop_gets_default(self):
        result = recommend_credit_purpose("unknowncrop")
        assert "seeds" in result["recommended_purpose"].lower()
