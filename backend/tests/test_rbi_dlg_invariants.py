import pytest
from app.models.farmer import Farmer
from app.models.credit_profile import CreditProfile
from app.models.loan import LoanApplication
from app.services.loan_service import create_loan, process_settlement, build_tranche_plan
from app.services.underwrite_service import annual_emi, evaluate_underwrite


def test_zero_borrower_fee_invariant(db, seed_actors):
    """Invariant I1: For every loan and underwrite, farmer-charged fee must be exactly 0.0."""
    farmer = seed_actors["farmer"]
    result = evaluate_underwrite(
        db,
        farmer,
        requested_amount=120000.0,
        tenure_months=10,
        annual_interest_rate=0.11,
        origination_fee_rate=0.0175,
        purpose_category="working_capital",
    )

    # Origination fee charged to borrower MUST be 0.0
    assert result["origination_fee"]["farmer_charged"] == 0.0
    assert result["origination_fee"]["payer"] == "lender"

    # Effective rate to farmer is strictly the contracted annual interest rate
    assert result["inputs"]["annual_interest_rate"] == 0.11


def test_settlement_zero_platform_fee_to_farmer(db, seed_actors):
    """Invariant I4: Mandi settlement proceeds deduct FPO and platform fees from value chain, never borrower debt."""
    farmer = seed_actors["farmer"]
    profile = db.query(CreditProfile).filter(CreditProfile.farmer_id == farmer.id).first()
    if not profile:
        profile = CreditProfile(
            farmer_id=farmer.id,
            safe_credit_limit=150000.0,
            risk_haircut=0.15,
            credit_tier="High",
            component_scores={},
            input_snapshot={},
        )
        db.add(profile)
        db.commit()

    loan = create_loan(
        db,
        farmer,
        profile,
        principal=100000.0,
        tenure_months=10,
        annual_interest_rate=0.11,
    )
    loan.status = "active"
    db.commit()

    sale_value = 132300.0
    settlement = process_settlement(db, loan, sale_value=sale_value, crop="paddy")

    receipt = settlement.receipt_json
    assert receipt["farmer_fees_total"] == 0.0
    assert receipt["rbi_dlg_invariant"] == "farmer_charged_zero"

    # FPO fee is 2% of mandi sale
    expected_fpo_fee = round(sale_value * 0.02, 2)
    assert settlement.fpo_facilitation_amt == expected_fpo_fee

    # Platform micro-fee is 0.15% of mandi sale
    expected_platform_fee = round(sale_value * 0.0015, 2)
    assert settlement.platform_settlement_fee == expected_platform_fee

    # Residual cash to farmer must equal sale_value - fpo_fee - platform_fee - emi_paid
    net_chain = sale_value - expected_fpo_fee - expected_platform_fee
    assert settlement.residual_to_farmer == round(net_chain - settlement.emi_paid, 2)


def test_disbursement_integrity(db, seed_actors):
    """Invariant I3: Tranche plan amounts sum exactly to gross principal (no deduction haircuts)."""
    farmer = seed_actors["farmer"]
    loan = LoanApplication(
        application_uid="LN-INVAR01",
        farmer_id=farmer.id,
        principal=120000.0,
        tenure_months=12,
        annual_interest_rate=0.11,
    )
    tranches = build_tranche_plan(loan)
    total_tranches = sum(t.amount for t in tranches)

    assert round(total_tranches, 2) == loan.principal
    # T1 = 40%, T2 = 50%, T3 = 10%
    assert tranches[0].amount == 48000.0
    assert tranches[1].amount == 60000.0
    assert tranches[2].amount == 12000.0
