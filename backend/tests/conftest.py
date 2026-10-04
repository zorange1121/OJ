import os
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import routers.submissions as submissions_router
import services.judge as judge
from database import get_db
from main import app
from model import Base, User
from services.auth import create_user


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session, tmp_path, monkeypatch):
    from services.login_limit import _attempts
    _attempts.clear()
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(judge, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    monkeypatch.setattr(judge, "DATA_DIR", tmp_path / "submissions")
    monkeypatch.setattr(submissions_router.queue_service, "publish_submission", lambda submission_id: judge.run_judge(submission_id))

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def make_user(db_session: Session):
    def _make_user(username: str, password: str = "testpass", is_admin: bool = False) -> User:
        return create_user(db_session, username, password, is_admin)

    return _make_user


@pytest.fixture()
def auth_headers(client: TestClient, make_user):
    def _auth_headers(username: str = "alice", password: str = "testpass", is_admin: bool = False) -> dict:
        make_user(username, password, is_admin)
        resp = client.post("/api/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers
