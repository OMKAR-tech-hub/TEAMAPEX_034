"""
Test configuration — uses an in-memory SQLite database.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = "sqlite:///./test_kisansetu.db"
engine_test = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


# Import after defining engine so the models import doesn't trigger real DB
from backend.database import Base, get_db
from backend.main import app

app.dependency_overrides[get_db] = override_get_db

# Create test tables before any test runs
Base.metadata.create_all(bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure tables exist for the whole test session."""
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    engine_test.dispose()
    import os, time
    time.sleep(0.2)
    try:
        if os.path.exists("test_kisansetu.db"):
            os.remove("test_kisansetu.db")
    except PermissionError:
        pass  # Windows file lock — test DB will be cleaned on next run


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="module")
def farmer_token(client):
    client.post("/api/v1/auth/register", json={
        "email": "testfarmer@test.com",
        "password": "Test@1234",
        "role": "farmer",
        "name": "Test Farmer",
        "phone": "9000000001",
        "district": "Sehore",
        "state": "Madhya Pradesh",
    })
    r = client.post("/api/v1/auth/login", data={"username": "testfarmer@test.com", "password": "Test@1234"})
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def lender_token(client):
    client.post("/api/v1/auth/register", json={
        "email": "testlender@test.com",
        "password": "Test@1234",
        "role": "lender",
        "name": "Test Lender Bank",
        "organization_name": "Test Bank",
        "lender_type": "regional_rural_bank",
    })
    r = client.post("/api/v1/auth/login", data={"username": "testlender@test.com", "password": "Test@1234"})
    return r.json()["access_token"]
