"""Tests: consent enforcement, lender cannot access without consent"""


def test_lender_cannot_see_passport_without_consent(client, lender_token, farmer_token):
    """Lender must not access farmer passport without active consent."""
    # Get farmer_id
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {farmer_token}"})
    farmer_profile_id = me.json()["profile_id"]

    # Lender tries to access without consent
    r = client.get(
        f"/api/v1/lender/farmers/{farmer_profile_id}/passport",
        headers={"Authorization": f"Bearer {lender_token}"}
    )
    assert r.status_code == 403
    assert "consent" in r.json()["detail"].lower()


def test_farmer_can_view_own_passport(client, farmer_token):
    """Farmer can always view their own passport."""
    r = client.get("/api/v1/passport/me", headers={"Authorization": f"Bearer {farmer_token}"})
    # 200 OK or auto-generates it
    assert r.status_code == 200
    data = r.json()
    assert "overall_creditworthiness" in data


def test_what_if_does_not_mutate_farmer(client, farmer_token):
    """What-if simulation must not change real data."""
    # Get passport before
    before = client.get("/api/v1/passport/me", headers={"Authorization": f"Bearer {farmer_token}"}).json()

    # Run what-if with very different values
    client.post("/api/v1/passport/what-if", json={
        "hypothetical_crop": "cotton",
        "hypothetical_area_acres": 50,
        "hypothetical_price_per_quintal": 9999,
    }, headers={"Authorization": f"Bearer {farmer_token}"})

    # Get passport after — must be same
    after = client.get("/api/v1/passport/me", headers={"Authorization": f"Bearer {farmer_token}"}).json()
    assert before["overall_creditworthiness"] == after["overall_creditworthiness"]
    assert before["safe_credit_limit"] == after["safe_credit_limit"]


def test_what_if_returns_note_about_no_mutation(client, farmer_token):
    r = client.post("/api/v1/passport/what-if", json={
        "hypothetical_area_acres": 3,
    }, headers={"Authorization": f"Bearer {farmer_token}"})
    assert r.status_code == 200
    assert "NOT been modified" in r.json()["note"]


def test_farmer_cannot_approve_own_application(client, farmer_token):
    """Farmer must not be able to set status=approved on their own application."""
    # Create application first
    client.post("/api/v1/credit/", json={
        "amount_requested": 50000,
        "purpose": "Test purchase",
    }, headers={"Authorization": f"Bearer {farmer_token}"})

    apps = client.get("/api/v1/credit/", headers={"Authorization": f"Bearer {farmer_token}"}).json()
    if not apps:
        return  # No apps to test

    app_id = apps[0]["id"]
    r = client.put(f"/api/v1/credit/{app_id}", json={"status": "approved"},
                   headers={"Authorization": f"Bearer {farmer_token}"})
    assert r.status_code == 403
