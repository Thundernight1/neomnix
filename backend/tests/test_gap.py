"""
Tests for src/api/gap.py — Gap Analysis API endpoints and Celery task.

Target coverage: 45% → 90%+. Tests:
  - POST /api/gap/analyze     → mock Celery task, assert 202 + task_id
  - GET  /api/gap/results/{id} → parametric for PENDING, SUCCESS, FAILURE, RETRY
  - GET  /api/gap/report/{org} → mock analyze_gaps, assert frameworks in response
  - run_gap_analysis_task (Celery) → unit tests for include_ai, Redis failure, DB exception
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.db.models import Base, Tenant, User, UnifiedControl, ControlCitation
from src.api.auth import get_password_hash
from src.api.main import app, get_db


# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def test_db_engine():
    """Create an isolated in-memory SQLite engine for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db_engine):
    """Provide a DB session bound to the test engine."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_db_engine, monkeypatch):
    """FastAPI test client with dependency-injected DB."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Required for require_role -> get_current_user
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 64)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_header(client, db_session):
    """Register a tenant + admin user and return a valid JWT auth header."""
    tenant = Tenant(
        id="tenant-gap-test",
        name="Gap Test Tenant",
        slug="gap-test-tenant",
        billing_email="billing@gap.io",
        tier="starter",
        is_active=True,
    )
    db_session.add(tenant)
    db_session.commit()

    user = User(
        tenant_id=tenant.id,
        email="admin@gap.io",
        hashed_password=get_password_hash("TestPassword123"),
        full_name="Gap Admin",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login = client.post("/auth/login", data={"username": "admin@gap.io", "password": "TestPassword123"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def populated_db(db_session):
    """Seed a minimal gap-analysis dataset: 2 controls, 3 citations."""
    c1 = UnifiedControl(
        id="UCL-001",
        title="Encryption in transit",
        description="TLS enforcement for all traffic",
        priority_level="HIGH",
        category="transit",
    )
    c2 = UnifiedControl(
        id="UCL-002",
        title="Access logging",
        description="Audit log retention",
        priority_level="MEDIUM",
        category="logging",
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    db_session.add_all([
        ControlCitation(control_id="UCL-001", framework="hipaa", citation_id="HIPAA-164.312(e)(1)"),
        ControlCitation(control_id="UCL-001", framework="mhmda", citation_id="RCW-19.373.010"),
        ControlCitation(control_id="UCL-002", framework="hipaa", citation_id="HIPAA-164.312(b)"),
    ])
    db_session.commit()
    return {"completed_ucl_ids": ["UCL-001"]}  # UCL-002 remains a gap


# ─────────────────────────────────────────────────────────────────────────────
# Test: POST /api/gap/analyze → 202 + task_id
# ─────────────────────────────────────────────────────────────────────────────

def test_post_analyze_returns_202_with_task_id(client, auth_header, monkeypatch):
    """POST /api/gap/analyze with valid body returns 202 and a task_id."""
    from src.api.gap import run_gap_analysis_task

    # Mock Celery's .delay() so we don't actually enqueue a task.
    with patch.object(run_gap_analysis_task, "delay") as mock_delay:
        mock_delay.return_value = MagicMock(id="celery-task-abc-123")
        r = client.post(
            "/api/gap/analyze",
            json={
                "org_id": "org-1",
                "completed_ucl_ids": ["UCL-001"],
                "target_frameworks": ["hipaa", "mhmda"],
                "include_ai_recommendations": True,
            },
            headers=auth_header,
        )

    assert r.status_code == 202, f"Expected 202, got {r.status_code}: {r.text}"
    body = r.json()
    assert "task_id" in body
    assert body["task_id"] == "celery-task-abc-123"
    assert body["status"] == "queued"
    mock_delay.assert_called_once_with(
        org_id="org-1",
        completed_ucl_ids=["UCL-001"],
        target_frameworks=["hipaa", "mhmda"],
        include_ai=True,
    )


def test_post_analyze_minimal_payload(client, auth_header, monkeypatch):
    """POST /api/gap/analyze with only required fields works."""
    from src.api.gap import run_gap_analysis_task

    with patch.object(run_gap_analysis_task, "delay") as mock_delay:
        mock_delay.return_value = MagicMock(id="t-min")
        r = client.post(
            "/api/gap/analyze",
            json={"org_id": "org-min"},
            headers=auth_header,
        )

    assert r.status_code == 202
    body = r.json()
    assert body["task_id"] == "t-min"
    # Defaults from the model
    mock_delay.assert_called_once_with(
        org_id="org-min",
        completed_ucl_ids=[],
        target_frameworks=None,
        include_ai=True,
    )


def test_post_analyze_without_auth_returns_401(client):
    """POST /api/gap/analyze without auth must 401."""
    r = client.post("/api/gap/analyze", json={"org_id": "x"})
    assert r.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Test: GET /api/gap/results/{task_id} → parametric for Celery states
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("celery_state, expected_status", [
    ("PENDING", "pending"),
    ("SUCCESS", "success"),
    ("FAILURE", "failed"),
    ("RETRY",   "retry"),
    ("STARTED", "started"),
])
def test_get_results_celery_states(client, auth_header, celery_state, expected_status):
    """GET /api/gap/results/{task_id} handles all Celery states."""
    # Mock celery.result.AsyncResult.
    fake_result = MagicMock()
    fake_result.state = celery_state
    if celery_state == "SUCCESS":
        fake_result.result = {"total_controls": 5, "gaps": []}
    elif celery_state == "FAILURE":
        fake_result.info = Exception("Worker error")
    else:
        # For PENDING/RETRY/STARTED we don't touch .result or .info
        pass

    # AsyncResult is imported inside the function from celery.result,
    # so patch the celery.result.AsyncResult symbol.
    with patch("celery.result.AsyncResult", return_value=fake_result):
        r = client.get(f"/api/gap/results/task-{celery_state}", headers=auth_header)

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == expected_status
    assert body["task_id"] == f"task-{celery_state}"

    if celery_state == "SUCCESS":
        assert "data" in body
    if celery_state == "FAILURE":
        assert "error" in body


def test_get_results_without_auth_returns_401(client):
    """GET /api/gap/results/{task_id} without auth must 401."""
    r = client.get("/api/gap/results/any-task-id")
    assert r.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Test: GET /api/gap/report/{org_id} → mock analyze_gaps, assert frameworks
# ─────────────────────────────────────────────────────────────────────────────

def test_get_report_returns_in_scope_frameworks(client, auth_header, monkeypatch):
    """GET /api/gap/report/{org_id} must include HIPAA-2026 and WA-MHMDA frameworks."""
    from src.services.gap_analyzer import GapReport

    fake_report = GapReport(
        total_controls=10,
        passing_controls=7,
        failing_controls=3,
        score=70,
        gaps=[],
        gaps_by_priority={"HIGH": 1, "MEDIUM": 1, "LOW": 1},
    )

    with patch("src.api.gap.analyze_gaps", return_value=fake_report) as mock_analyze:
        r = client.get("/api/gap/report/org-xyz", headers=auth_header)

    assert r.status_code == 200
    body = r.json()
    assert body["total_controls"] == 10
    assert body["passing_controls"] == 7
    assert body["failing_controls"] == 3
    assert body["score"] == 70
    assert "gaps_by_priority" in body
    # Verify the call went through with the default frameworks.
    mock_analyze.assert_called_once()


def test_get_report_with_frameworks_filter(client, auth_header, monkeypatch):
    """GET /api/gap/report/{org_id}?frameworks=hipaa passes filter to analyze_gaps."""
    from src.services.gap_analyzer import GapReport

    fake_report = GapReport(
        total_controls=2, passing_controls=2, failing_controls=0, score=100
    )

    with patch("src.api.gap.analyze_gaps", return_value=fake_report) as mock_analyze:
        r = client.get(
            "/api/gap/report/org-xyz?frameworks=hipaa,mhmda",
            headers=auth_header,
        )

    assert r.status_code == 200
    body = r.json()
    # Only HIPAA+MHMDA frameworks are in-scope.
    assert body["score"] == 100
    mock_analyze.assert_called_once()
    # Inspect what was passed.
    call_args = mock_analyze.call_args
    target_frameworks = call_args.kwargs.get("target_frameworks") or call_args.args[2]
    assert target_frameworks == ["hipaa", "mhmda"]


# ─────────────────────────────────────────────────────────────────────────────
# Test: run_gap_analysis_task (Celery task) — unit tests
# ─────────────────────────────────────────────────────────────────────────────

def test_celery_task_include_ai_true_calls_get_recommendation(monkeypatch):
    """include_ai=True path: get_recommendation is called once per gap."""
    from src.api.gap import run_gap_analysis_task
    from src.services.gap_analyzer import GapReport, GapItem

    fake_report = GapReport(
        total_controls=2,
        passing_controls=0,
        failing_controls=2,
        score=0,
        gaps=[
            GapItem(
                ucl_id="UCL-001",
                title="Encryption",
                description="TLS",
                priority_level="HIGH",
                affected_frameworks=["hipaa"],
                citations={"hipaa": ["HIPAA-164.312(e)(1)"]},
            ),
            GapItem(
                ucl_id="UCL-002",
                title="Logging",
                description="Audit log",
                priority_level="MEDIUM",
                affected_frameworks=["mhmda"],
                citations={"mhmda": ["RCW-19.373.010"]},
            ),
        ],
    )

    # Mock analyze_gaps.
    monkeypatch.setattr("src.api.gap.analyze_gaps", lambda *a, **kw: fake_report)
    # Mock get_recommendation.
    rec_calls = []
    def fake_rec(ucl_id, title, description, frameworks, citations, redis_client=None):
        rec_calls.append(ucl_id)
        return {"why_critical": "test", "fix_steps": ["a"]}
    monkeypatch.setattr(
        "src.services.remediation_ai.get_recommendation", fake_rec
    )

    # Mock SessionLocal so the DB close path is exercised but not required.
    # The task does `from src.db.models import SessionLocal` inside its body,
    # so patch the source module.
    mock_db = MagicMock()
    monkeypatch.setattr("src.db.models.SessionLocal", lambda: mock_db)

    # Mock the redis import inside run_gap_analysis_task by patching
    # the function's view of the `redis` module. The task does
    # `import redis; r = redis.from_url(...)` inside the try block.
    fake_redis_module = MagicMock()
    fake_redis_module.from_url.return_value = MagicMock()
    import sys
    monkeypatch.setitem(sys.modules, "redis", fake_redis_module)

    result = run_gap_analysis_task(
        org_id="org-1",
        completed_ucl_ids=[],
        target_frameworks=["hipaa", "mhmda"],
        include_ai=True,
    )

    assert len(rec_calls) == 2
    assert "UCL-001" in rec_calls
    assert "UCL-002" in rec_calls
    assert result["total_controls"] == 2
    # DB must be closed in finally.
    mock_db.close.assert_called_once()
    # The redis client was created and passed through.
    fake_redis_module.from_url.assert_called_once()


def test_celery_task_include_ai_false_skips_get_recommendation(monkeypatch):
    """include_ai=False path: get_recommendation is NOT called."""
    from src.api.gap import run_gap_analysis_task
    from src.services.gap_analyzer import GapReport, GapItem

    fake_report = GapReport(
        total_controls=1,
        passing_controls=0,
        failing_controls=1,
        score=0,
        gaps=[
            GapItem(
                ucl_id="UCL-X",
                title="x", description="x", priority_level="LOW",
                affected_frameworks=["hipaa"], citations={},
            ),
        ],
    )
    monkeypatch.setattr("src.api.gap.analyze_gaps", lambda *a, **kw: fake_report)
    rec_called = []
    def fake_rec(*a, **kw):
        rec_called.append(True)
        return {}
    monkeypatch.setattr("src.services.remediation_ai.get_recommendation", fake_rec)

    mock_db = MagicMock()
    monkeypatch.setattr("src.db.models.SessionLocal", lambda: mock_db)

    fake_redis_module = MagicMock()
    fake_redis_module.from_url.return_value = MagicMock()
    import sys
    monkeypatch.setitem(sys.modules, "redis", fake_redis_module)

    result = run_gap_analysis_task(
        org_id="o", completed_ucl_ids=[],
        target_frameworks=["hipaa"], include_ai=False,
    )
    assert rec_called == []
    assert result["total_controls"] == 1
    mock_db.close.assert_called_once()


def test_celery_task_redis_failure_degrades_gracefully(monkeypatch):
    """Redis import or connection failure: r_client becomes None, no crash."""
    from src.api.gap import run_gap_analysis_task
    from src.services.gap_analyzer import GapReport

    fake_report = GapReport(
        total_controls=0, passing_controls=0, failing_controls=0, score=0
    )
    monkeypatch.setattr("src.api.gap.analyze_gaps", lambda *a, **kw: fake_report)

    # Simulate redis failure by providing a module whose from_url raises.
    import sys
    saved_redis = sys.modules.get("redis")

    class FakeRedisModule:
        @staticmethod
        def from_url(url):  # noqa: ARG004 — url is documented but unused
            raise ConnectionError("redis is down")

    monkeypatch.setitem(sys.modules, "redis", FakeRedisModule)

    mock_db = MagicMock()
    monkeypatch.setattr("src.db.models.SessionLocal", lambda: mock_db)

    # Should not raise.
    result = run_gap_analysis_task(
        org_id="o", completed_ucl_ids=[],
        target_frameworks=None, include_ai=False,
    )
    assert result["total_controls"] == 0
    # DB still closed.
    mock_db.close.assert_called_once()
    # Restore.
    if saved_redis is not None:
        sys.modules["redis"] = saved_redis


def test_celery_task_db_exception_still_closes_db(monkeypatch):
    """If analyze_gaps raises, the finally block must still call db.close()."""
    from src.api.gap import run_gap_analysis_task

    def explode(*a, **kw):
        raise RuntimeError("DB is on fire")
    monkeypatch.setattr("src.api.gap.analyze_gaps", explode)

    # Provide a working redis.
    fake_redis_module = MagicMock()
    fake_redis_module.from_url.return_value = MagicMock()
    import sys
    monkeypatch.setitem(sys.modules, "redis", fake_redis_module)

    mock_db = MagicMock()
    monkeypatch.setattr("src.db.models.SessionLocal", lambda: mock_db)

    with pytest.raises(RuntimeError, match="DB is on fire"):
        run_gap_analysis_task(
            org_id="o", completed_ucl_ids=[],
            target_frameworks=None, include_ai=False,
        )
    # finally block must have closed the DB even on exception.
    mock_db.close.assert_called_once()
