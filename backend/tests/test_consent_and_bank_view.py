import pytest
from app.models.consent_log import ConsentLog
from app.models.loan import LoanApplication
from app.services.bank_view import _mask_value


def test_attribute_masking_function():
    """Verify deterministic attribute masking."""
    assert _mask_value("mobile", "9876543210") == "xxxxxx3210"
    assert _mask_value("name", "Ramesh Patel") == "R. P."
    assert _mask_value("district", "Nashik") == "••••••"


def test_consent_grant_and_masked_bank_view(client, db, seed_actors):
    """Verify bank sees only consented attributes and masked fields are masked."""
    farmer = seed_actors["farmer"]
    bank_user = seed_actors["bank_user"]
    farmer_headers = seed_actors["farmer_headers"]
    bank_headers = seed_actors["bank_headers"]

    # 1. Farmer grants consent to bank
    grant_res = client.post(
        "/api/v1/consents",
        json={
            "bank_user_id": bank_user.id,
            "attributes": ["name", "mobile", "village"],
            "masked_attributes": ["mobile"],
        },
        headers=farmer_headers,
    )
    assert grant_res.status_code == 201
    consent_id = grant_res.json()["id"]

    # 2. Bank views farmer profile
    view_res = client.get(f"/api/v1/bank/farmers/{farmer.farmer_id}/view", headers=bank_headers)
    assert view_res.status_code == 200
    data = view_res.json()

    fields_by_attr = {f["attribute"]: f for f in data["fields"]}
    assert "name" in fields_by_attr
    assert "village" in fields_by_attr
    assert "mobile" in fields_by_attr
    assert fields_by_attr["mobile"]["masked"] is True
    assert fields_by_attr["mobile"]["value"] == "xxxxxx0001"  # last 4 of 9999900001

    # Unconsented attributes must not appear
    assert "acreage" not in fields_by_attr

    # 3. Farmer revokes consent
    del_res = client.delete(f"/api/v1/consents/{consent_id}", headers=farmer_headers)
    assert del_res.status_code == 204

    # 4. Bank immediate 403 Forbidden check
    revoked_view_res = client.get(f"/api/v1/bank/farmers/{farmer.farmer_id}/view", headers=bank_headers)
    assert revoked_view_res.status_code == 403


def test_origination_pipeline_and_psl_export(client, db, seed_actors):
    """Verify bank origination pipeline and PSL CSV report download."""
    farmer = seed_actors["farmer"]
    bank_user = seed_actors["bank_user"]
    farmer_headers = seed_actors["farmer_headers"]
    bank_headers = seed_actors["bank_headers"]

    # Grant consent
    client.post(
        "/api/v1/consents/grant",
        json={
            "bank_user_id": bank_user.id,
            "attributes": ["name", "mobile", "village", "passport"],
            "masked_attributes": ["mobile"],
        },
        headers=farmer_headers,
    )

    # Add active loan with PSL tag
    loan = LoanApplication(
        application_uid="LN-PSLTEST",
        farmer_id=farmer.id,
        principal=100000.0,
        tenure_months=12,
        annual_interest_rate=0.11,
        status="active",
        psl_category="Small & Marginal Farmer - Agri <= 2L",
        psl_eligible=True,
    )
    db.add(loan)
    db.commit()

    # Test pipeline endpoint (both /bank/pipeline and /lender/pipeline)
    pipe_res = client.get("/api/v1/bank/pipeline", headers=bank_headers)
    assert pipe_res.status_code == 200
    pipe_data = pipe_res.json()["data"]
    assert pipe_data["count"] >= 1
    assert pipe_data["items"][0]["farmer_ref"] == farmer.farmer_id

    lender_res = client.get("/api/v1/lender/pipeline", headers=bank_headers)
    assert lender_res.status_code == 200

    # Test PSL CSV export
    export_res = client.get("/api/v1/bank/export/psl", headers=bank_headers)
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["content-type"]
    csv_content = export_res.text
    assert "LN-PSLTEST" in csv_content
    assert "Small & Marginal Farmer" in csv_content
