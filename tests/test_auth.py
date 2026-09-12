"""Tests: auth registration, login, JWT"""


def test_register_farmer(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "newfarm@test.com", "password": "Test@1234",
        "role": "farmer", "name": "New Farmer", "phone": "9000000099",
    })
    assert r.status_code == 201
    assert r.json()["role"] == "farmer"


def test_register_duplicate_email(client):
    data = {"email": "dup@test.com", "password": "Test@1234", "role": "farmer", "name": "Dup"}
    client.post("/api/v1/auth/register", json=data)
    r = client.post("/api/v1/auth/register", json=data)
    assert r.status_code == 400


def test_login_success(client):
    client.post("/api/v1/auth/register", json={
        "email": "logintest@test.com", "password": "Test@1234",
        "role": "farmer", "name": "Login Test",
    })
    r = client.post("/api/v1/auth/login", data={"username": "logintest@test.com", "password": "Test@1234"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password(client):
    r = client.post("/api/v1/auth/login", data={"username": "logintest@test.com", "password": "wrong"})
    assert r.status_code == 401


def test_cannot_register_as_admin(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "admin2@test.com", "password": "Test@1234",
        "role": "admin", "name": "Hacker",
    })
    assert r.status_code == 403


def test_me_endpoint(client, farmer_token):
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {farmer_token}"})
    assert r.status_code == 200
    assert r.json()["role"] == "farmer"


def test_me_no_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
