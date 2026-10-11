import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.utils.rate_limit import _hits as _rate_limit_hits


@pytest.fixture()
def client():
    # StaticPool: FastAPI runs sync endpoints in a worker thread, so a plain
    # in-memory SQLite engine would hand each thread its own empty database.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)  # no context manager: skip lifespan, avoid touching the real DB file
    test_client.test_session_factory = TestSession  # lets tests inspect DB state directly

    # The rate limiter is module-level, in-memory state — correct in
    # production, but TestClient always reports the same fake IP, so without
    # resetting this, unrelated tests would collectively exhaust each
    # other's rate limits. Isolate each test the same way the DB already is.
    _rate_limit_hits.clear()

    yield test_client
    app.dependency_overrides.clear()


def register_and_get_token(client, email="owner@techfixsolutions.io", business_name="TechFix Solutions"):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "supersecret123",
            "full_name": "Techfix Owner",
            "business_name": business_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
