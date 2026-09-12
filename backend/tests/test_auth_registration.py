def test_registered_farmer_can_log_in_again(client):
    """Registration must persist credentials for a later, independent login."""
    registration = client.post(
        "/api/v1/auth/register/farmer",
        json={
            "name": "Login Regression Farmer",
            "mobile": "9000000001",
            "password": "secure123",
            "village": "Test Village",
            "district": "Test District",
            "state": "Test State",
            "acreage": 2.5,
            "primary_crop": "paddy",
            "crop_season": "Kharif",
            "fpo_membership": None,
        },
    )

    assert registration.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "9000000001", "password": "secure123"},
    )

    assert login.status_code == 200
    assert login.json()["role"] == "farmer"
    assert login.json()["user"]["username"] == "9000000001"
