import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import Farmer, Role, User

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seed_actors(db):
    """Seed standard test actors: Farmer, FPO, Bank."""
    farmer = Farmer(
        farmer_id="FAR-TEST01",
        name="Ramesh Test",
        mobile="9999900001",
        village="Krishnapur",
        district="Nashik",
        state="Maharashtra",
        acreage=3.5,
        primary_crop="paddy",
        crop_season="Kharif",
        fpo_membership="Krishak Test FPO",
        crop_insured=True,
        insurance_sum_assured=100000.0,
        farm_experience_years=7,
    )
    db.add(farmer)
    db.flush()

    farmer_user = User(
        username="9999900001",
        password_hash=hash_password("pass123"),
        role=Role.FARMER.value,
        name=farmer.name,
        farmer_id=farmer.id,
    )
    fpo_user = User(
        username="fpo_test",
        password_hash=hash_password("pass123"),
        role=Role.FPO.value,
        name="Krishak Test FPO",
        wallet_balance=1000.0,
    )
    bank_user = User(
        username="bank_test",
        password_hash=hash_password("pass123"),
        role=Role.BANK.value,
        name="Gramin Test Bank",
    )
    db.add_all([farmer_user, fpo_user, bank_user])
    db.commit()

    db.refresh(farmer)
    db.refresh(farmer_user)
    db.refresh(fpo_user)
    db.refresh(bank_user)

    farmer_token = create_access_token(farmer_user.id, farmer_user.role)
    fpo_token = create_access_token(fpo_user.id, fpo_user.role)
    bank_token = create_access_token(bank_user.id, bank_user.role)

    return {
        "farmer": farmer,
        "farmer_user": farmer_user,
        "fpo_user": fpo_user,
        "bank_user": bank_user,
        "farmer_headers": {"Authorization": f"Bearer {farmer_token}"},
        "fpo_headers": {"Authorization": f"Bearer {fpo_token}"},
        "bank_headers": {"Authorization": f"Bearer {bank_token}"},
    }
