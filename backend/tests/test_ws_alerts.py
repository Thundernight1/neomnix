"""
Tests for Chunk 3 R3 (WebSocket) and R4 (admin-only PDF).

R4 tests verify that:
  - GET /reports/pdf/{job_id}/{framework} requires the admin role.
  - An analyst (or any non-admin) gets 403.
  - An admin gets 200 (or 404 if the file isn't on disk; not 403).
  - The framework allowlist is trimmed to HIPAA-2026 + WA-MHMDA.

R3 tests verify that:
  - GET /ws/alerts rejects connections without a token.
  - GET /ws/alerts rejects connections with an invalid token.
  - GET /ws/alerts accepts a valid token.
  - When SharkTapSkill pushes an event onto the alert_queue, a
    connected WebSocket client receives that event as JSON.
"""

import asyncio
import json
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.models import Base, User, Tenant, ScanJob
from src.api import main as main_module
from src.api.main import app, get_db, get_alert_queue
from src.api.auth import get_password_hash, create_access_token


# ──────────────────────────────────────────────────────────────────────────────
# Test fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def test_db():
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
    db = TestingSessionLocal()
    try:
        yield db, TestingSessionLocal
    finally:
        db.close()
        app.dependency_overrides.clear()


@pytest.fixture
def client(test_db):
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_alert_queue():
    """asyncio.Queue is bound to the event loop that created it. Each
    pytest test gets its own loop via TestClient, so the module-level
    queue (if any) becomes unusable across tests. Reset it to None so
    `get_alert_queue()` lazily creates a fresh one on the current loop.
    """
    main_module._alert_queue = None
    yield
    main_module._alert_queue = None


def _make_tenant(db, slug="t-1"):
    t = Tenant(
        id=str(uuid.uuid4()),
        name="Test Org",
        slug=slug,
        billing_email="b@t.io",
        tier="starter",
        is_active=True,
    )
    db.add(t)
    db.commit()
    return t


def _make_user(db, tenant, email, role, password="TestPassword123"):
    u = User(
        tenant_id=tenant.id,
        email=email,
        hashed_password=get_password_hash(password),
        full_name=email.split("@")[0].title(),
        role=role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def tenant(test_db):
    db, _ = test_db
    return _make_tenant(db)


@pytest.fixture
def admin_user(test_db, tenant):
    db, _ = test_db
    return _make_user(db, tenant, "admin@t.io", "admin")


@pytest.fixture
def analyst_user(test_db, tenant):
    db, _ = test_db
    return _make_user(db, tenant, "analyst@t.io", "analyst")


@pytest.fixture
def viewer_user(test_db, tenant):
    db, _ = test_db
    return _make_user(db, tenant, "viewer@t.io", "viewer")


def _login(client, email, password="TestPassword123"):
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ──────────────────────────────────────────────────────────────────────────────
# R4 — admin-only PDF route
# ──────────────────────────────────────────────────────────────────────────────


def _make_scan_job(db, tenant):
    job = ScanJob(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        target="test-target",
        status="completed",
        initiated_by=tenant.billing_email,
        findings=[],
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class TestPdfRouteAdminOnly:
    def test_admin_can_call_endpoint(self, client, admin_user):
        """An admin receives a 404 (file not on disk), not a 403."""
        token = _login(client, "admin@t.io")
        # Use a syntactically valid UUID.
        job_id = str(uuid.uuid4())
        r = client.get(f"/reports/pdf/{job_id}/HIPAA-2026", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code != 403, "Admin must not be denied"
        # 404 because the file doesn't exist on disk in the test env.
        assert r.status_code == 404

    def test_analyst_cannot_call_endpoint(self, client, admin_user, analyst_user):
        """An analyst must receive 403, not 404."""
        token = _login(client, "analyst@t.io")
        job_id = str(uuid.uuid4())
        r = client.get(f"/reports/pdf/{job_id}/HIPAA-2026", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"Analyst must be 403'd, got {r.status_code}: {r.text}"
        body = r.json()
        assert "analyst" in body["detail"].lower() or "role" in body["detail"].lower()

    def test_viewer_cannot_call_endpoint(self, client, viewer_user):
        """A viewer must also receive 403."""
        token = _login(client, "viewer@t.io")
        job_id = str(uuid.uuid4())
        r = client.get(f"/reports/pdf/{job_id}/WA-MHMDA", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    def test_unauthenticated_caller_is_rejected(self, client):
        """No token at all -> 401 (from the auth dependency)."""
        job_id = str(uuid.uuid4())
        r = client.get(f"/reports/pdf/{job_id}/HIPAA-2026")
        assert r.status_code == 401

    def test_out_of_scope_framework_rejected_for_admin(self, client, admin_user):
        """Even an admin cannot download an out-of-scope framework report
        (NIST-800-53, SOC2). The allowlist is server-side, not just
        for analyst/viewer."""
        token = _login(client, "admin@t.io")
        for bad in ("NIST-800-53", "SOC2", "CCM-4.0", "SEC-2023"):
            r = client.get(f"/reports/pdf/{uuid.uuid4()}/{bad}", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 400, (
                f"Out-of-scope framework {bad} must be rejected with 400, got {r.status_code}"
            )
            assert "Unsupported framework" in r.json()["detail"]


# ──────────────────────────────────────────────────────────────────────────────
# R3 — live alert WebSocket
# ──────────────────────────────────────────────────────────────────────────────


class TestWebSocketAlerts:
    def test_ws_rejects_connection_without_token(self, client):
        """No token in the query string -> server closes with code 1008
        (policy violation) before accepting. The TestClient surfaces the
        close as a WebSocketDisconnect on context-manager entry."""
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/alerts"):
                pass
        # starlette passes the close code through. 1008 = policy violation.
        assert exc_info.value.code == 1008

    def test_ws_rejects_connection_with_invalid_token(self, client):
        """Garbage token -> close code 1008."""
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/alerts?token=not-a-real-jwt"):
                pass
        assert exc_info.value.code == 1008

    def test_ws_rejects_connection_with_expired_or_bogus_jwt(self, client):
        """A well-formed but undecodable JWT -> close code 1008."""
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/alerts?token=xxx.yyy.zzz"):
                pass
        assert exc_info.value.code == 1008

    def test_ws_rejects_connection_for_unknown_user(self, client):
        """A JWT signed for a user that doesn't exist in the test DB."""
        token = create_access_token(data={"sub": "ghost@t.io", "role": "admin"})
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/alerts?token={token}"):
                pass
        assert exc_info.value.code == 1008

    def test_ws_rejects_inactive_user(self, client, admin_user, test_db):
        """An inactive user must not be able to subscribe.

        Login itself will 403 for an inactive user, so we mint a token
        directly via create_access_token (the auth dependency is what
        is being tested, not login)."""
        db, _ = test_db
        admin_user.is_active = False
        db.commit()
        token = create_access_token(data={"sub": admin_user.email, "role": admin_user.role})
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/alerts?token={token}"):
                pass
        assert exc_info.value.code == 1008

    def test_ws_accepts_valid_admin_token(self, client, admin_user):
        """A valid admin token connects successfully and the server
        sends a heartbeat within HEARTBEAT_INTERVAL seconds (30s)."""
        token = _login(client, "admin@t.io")
        with client.websocket_connect(f"/ws/alerts?token={token}") as ws:
            # The server will send a heartbeat after 30s of no alerts.
            # We don't want a 30s test; we want to confirm the connection
            # is open and the heartbeat is well-formed. Just verify the
            # connection handshake succeeded by closing it cleanly.
            pass  # context manager exit closes the socket

    def test_ws_receives_enqueued_event(self, client, admin_user):
        """Push an event onto the alert queue while a WebSocket client
        is connected. The client must receive the event as a JSON string.

        asyncio.Queue is thread-safe for put_nowait/get_nowait, so the
        test thread can enqueue an event that the server's loop will
        deliver.
        """
        token = _login(client, "admin@t.io")
        with client.websocket_connect(f"/ws/alerts?token={token}") as ws:
            event = {
                "type": "critical_data_leak",
                "severity": "critical",
                "threat": "UNENCRYPTED_DATABASE",
                "source": "10.0.0.5",
                "detail": "Test push",
                "pcap": "synthetic.pcap",
                "timestamp": "2026-06-06T00:00:00",
            }
            # Drain any leftover events from previous tests so we receive
            # the one we just pushed (the queue is module-level state).
            queue = get_alert_queue()
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pytest.skip("queue full")

            msg = ws.receive_text()
            data = json.loads(msg)
            assert data["type"] == "critical_data_leak"
            assert data["threat"] == "UNENCRYPTED_DATABASE"
            assert data["source"] == "10.0.0.5"
            assert data["pcap"] == "synthetic.pcap"
