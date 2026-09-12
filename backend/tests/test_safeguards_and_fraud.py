import pytest
from app.models.farmer import Farmer
from app.models.credit_profile import CreditProfile
from app.models.loan import DisbursementTranche, LoanApplication
from app.models.user import Role, User
from app.services.loan_service import approve_loan, create_loan, declare_risk_event, release_tranche


def test_loss_event_blocks_pending_tranches(db, seed_actors):
    """Verify that a severe climate shock (e.g. drought) blocks scheduled tranches and triggers moratorium."""
    farmer = seed_actors["farmer"]
    bank_user = seed_actors["bank_user"]

    profile = CreditProfile(
        farmer_id=farmer.id,
        safe_credit_limit=100000.0,
        risk_haircut=0.15,
        credit_tier="High",
        component_scores={},
        input_snapshot={},
    )
    db.add(profile)
    db.commit()

    loan = create_loan(db, farmer, profile, principal=100000.0, tenure_months=12, annual_interest_rate=0.11)
    loan = approve_loan(db, loan, by=bank_user)

    # Release T1
    t1 = loan.tranches[0]
    released_t1 = release_tranche(db, loan, t1)
    assert released_t1.status == "released"

    # Declare mid-season severe drought
    declare_risk_event(db, loan, event_type="drought", severity="severe", loss_ratio=0.60)

    # Invariant: EMI is paused (moratorium)
    assert loan.emi_paused is True

    # Invariant: Remaining scheduled tranches are blocked
    t2 = loan.tranches[1]
    assert t2.status == "blocked"

    # Attempting to release a blocked tranche must raise ValueError / conflict
    with pytest.raises(ValueError) as exc:
        release_tranche(db, loan, t2)
    assert "blocked" in str(exc.value).lower()


def test_self_vouching_rejected(client, db, seed_actors):
    """Anti-collusion: FPO user cannot self-vouch their own linked farmer profile (422)."""
    farmer = seed_actors["farmer"]
    fpo_headers = seed_actors["fpo_headers"]
    fpo_user = seed_actors["fpo_user"]

    # Link fpo_user to farmer
    fpo_user.farmer_id = farmer.id
    db.commit()

    res = client.post(
        "/api/v1/risk/vouches",
        json={"farmer_id": farmer.id, "guarantee_style": "first_loss"},
        headers=fpo_headers,
    )
    assert res.status_code == 422
    assert "conflict of interest" in res.json()["detail"].lower()


def test_reciprocal_vouch_scheme_detected(client, db, seed_actors):
    """Anti-collusion: Mutual circular vouching between two members is detected and frozen (409)."""
    # Create Farmer 2 and FPO user 2
    farmer2 = Farmer(
        farmer_id="FAR-PEER02",
        name="Suresh Peer",
        mobile="9999900002",
        village="Krishnapur",
        district="Nashik",
        state="Maharashtra",
        acreage=2.5,
        primary_crop="paddy",
        fpo_membership="Krishak Test FPO",
    )
    db.add(farmer2)
    db.flush()

    from app.models.fpo_vouch import FpoVouch
    # A vouched B previously
    prior_vouch = FpoVouch(
        farmer_id=seed_actors["farmer"].id,
        fpo_user_id=farmer2.id,
        guarantee_style="first_loss",
        status="active",
    )
    db.add(prior_vouch)
    db.commit()

    # Now B (seed_actors["fpo_user"] linked to farmer) attempts to vouch A (farmer2)
    fpo_user = seed_actors["fpo_user"]
    fpo_user.farmer_id = seed_actors["farmer"].id
    db.commit()

    res = client.post(
        "/api/v1/risk/vouches",
        json={"farmer_id": farmer2.id, "guarantee_style": "first_loss"},
        headers=seed_actors["fpo_headers"],
    )
    assert res.status_code == 409
    assert "reciprocal" in res.json()["detail"].lower()


def test_vouch_never_changes_safe_credit_limit(client, db, seed_actors):
    """Social vouching moves attestation/reputation, never the Safe Credit Limit directly."""
    farmer = seed_actors["farmer"]
    fpo_headers = seed_actors["fpo_headers"]

    res = client.post(
        "/api/v1/fpo/vouch",
        json={"farmer_id": farmer.id, "guarantee_style": "first_loss"},
        headers=fpo_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["safe_credit_limit_unchanged"] is True
    assert "weight" in data
    assert "attestation_score_delta" in data
