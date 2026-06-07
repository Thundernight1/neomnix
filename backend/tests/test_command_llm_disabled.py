import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app, ai_hub, get_db
from src.api.auth import get_password_hash
from src.db.models import Base, Tenant, User


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def auth_header(client):
    db = next(app.dependency_overrides[get_db]())

    tenant = Tenant(
        id="tenant-test",
        name="Test Tenant",
        slug="test-tenant",
        billing_email="billing@test.io",
        tier="starter",
        is_active=True,
    )
    db.add(tenant)
    db.commit()

    user = User(
        tenant_id=tenant.id,
        email="admin@test.io",
        hashed_password=get_password_hash("TestPassword123"),
        full_name="Test Admin",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()

    login = client.post("/auth/login", data={"username": "admin@test.io", "password": "TestPassword123"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_command_unknown_intent_dispatches_to_default_agent(monkeypatch, client, auth_header):
    """Post-DCE: there is no LLM agent. Commands that don't match any
    intent_map keyword dispatch to the default agent (scanner). This
    replaces the pre-DCE test that expected a 503 when no LLM API
    key was configured — that test was asserting behaviour for a
    code path that no longer exists.

    The scanner is registered in main.py's startup, so a plain
    "hello" command (no scan/analyze keywords) falls through to
    the scanner's default-execute path and returns 200.
    """
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    r = client.post("/command", json={"command": "hello", "context": {}}, headers=auth_header)
    # The scanner agent's default target is "localhost"; a 200 with
    # some JSON body is the expected new behaviour.
    assert r.status_code == 200


def test_command_non_llm_intent_still_works_without_api_key(monkeypatch, client, auth_header):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)

    class DummyScanner:
        async def execute(self, target: str, context=None):
            return {"status": "ok", "target": target}

    ai_hub.agents["scanner"] = DummyScanner()

    r = client.post("/command", json={"command": "scan", "context": {"target": "example.com"}}, headers=auth_header)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
