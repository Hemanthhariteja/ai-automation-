import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import datetime

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_business_id, get_current_user
from app.auth.security import ALGORITHM, create_access_token, hash_password
from app.config import get_settings
from app.database.base import Base
from app.models.user import User

settings = get_settings()


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_token_missing_sub_claim_rejected(db_session):
    token = jwt.encode(
        {"exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)},
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials=_creds(token), db=db_session)
    assert exc_info.value.status_code == 401


def test_token_for_nonexistent_user_rejected(db_session):
    token = create_access_token(subject="999999")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials=_creds(token), db=db_session)
    assert exc_info.value.status_code == 401


def test_token_for_inactive_user_rejected(db_session):
    user = User(email="disabled@example.io", hashed_password=hash_password("whatever123"), full_name="Disabled", is_active=False)
    db_session.add(user)
    db_session.commit()

    token = create_access_token(subject=str(user.id))
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials=_creds(token), db=db_session)
    assert exc_info.value.status_code == 401


def test_get_current_business_id_rejects_user_with_no_business():
    user = User(id=1, email="nobusiness@example.io", hashed_password="x", full_name="No Biz", business_id=None)
    with pytest.raises(HTTPException) as exc_info:
        get_current_business_id(current_user=user)
    assert exc_info.value.status_code == 400
