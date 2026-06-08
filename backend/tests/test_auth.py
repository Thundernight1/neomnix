"""
Tests for src/api/auth.py — JWT Authentication Module.

Target coverage: 87% → 97%+. Tests:
  - get_jwt_secret_key: missing env var → RuntimeError
  - get_jwt_secret_key: key shorter than 32 chars → RuntimeError
  - get_db: assert db.close() called in finally block
  - get_current_user: invalid JWT signature → 401
  - get_current_user: expired token → 401
  - get_current_user: missing "sub" claim → 401
  - get_current_user: user not found in DB → 401
  - get_current_user: user.is_active=False → 401
  - require_role: correct role → returns user
  - require_role: wrong role → 403 with role name in detail
"""
import os
import sys
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.db.models import Base, Tenant, User
from src.api.auth import (
    ALGORITHM,
    get_jwt_secret_key,
    JWT_SECRET_KEY_MIN_LENGTH,
    get_password_hash,
    create_access_token,
    get_current_user,
    require_role,
    get_db,
)
from src.api.main import app


# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def test_db_engine():
    """Isolated in-memory SQLite engine."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db_session(test_db_engine):
    """SQLAlchemy session bound to the test engine."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_user(test_db_session):
    """Insert a known tenant + active user."""
    tenant = Tenant(
        id="tenant-auth",
        name="Auth Test Tenant",
        slug="auth-test-tenant",
        billing_email="billing@auth.io",
        tier="starter",
        is_active=True,
    )
    test_db_session.add(tenant)
    test_db_session.commit()

    user = User(
        tenant_id=tenant.id,
        email="auth@test.io",
        hashed_password=get_password_hash("TestPassword123"),
        full_name="Auth Tester",
        role="analyst",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()
    return user


@pytest.fixture
def secret_key(monkeypatch):
    """Set a valid 32+ char JWT secret."""
    key = "x" * 64
    monkeypatch.setenv("JWT_SECRET_KEY", key)
    return key


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_jwt_secret_key
# ─────────────────────────────────────────────────────────────────────────────

def test_get_jwt_secret_key_raises_when_missing(monkeypatch):
    """get_jwt_secret_key raises RuntimeError when env var is unset."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable is required"):
        get_jwt_secret_key()


def test_get_jwt_secret_key_raises_when_empty_string(monkeypatch):
    """get_jwt_secret_key raises RuntimeError when env var is empty/whitespace."""
    monkeypatch.setenv("JWT_SECRET_KEY", "   ")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable is required"):
        get_jwt_secret_key()


def test_get_jwt_secret_key_raises_when_too_short(monkeypatch):
    """get_jwt_secret_key raises RuntimeError when key is shorter than 32 chars."""
    monkeypatch.setenv("JWT_SECRET_KEY", "short")
    with pytest.raises(RuntimeError, match=f"at least {JWT_SECRET_KEY_MIN_LENGTH}"):
        get_jwt_secret_key()


def test_get_jwt_secret_key_returns_value_when_valid(monkeypatch):
    """get_jwt_secret_key returns the value when it's at least 32 chars."""
    valid = "a" * 32
    monkeypatch.setenv("JWT_SECRET_KEY", valid)
    assert get_jwt_secret_key() == valid


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_db
# ─────────────────────────────────────────────────────────────────────────────

def test_get_db_closes_db_in_finally(monkeypatch):
    """get_db() must call db.close() in its finally block."""
    from src.api import auth as auth_module

    mock_db = MagicMock()
    monkeypatch.setattr(auth_module, "SessionLocal", lambda: mock_db)

    # get_db is a generator — drive it through the lifecycle.
    gen = auth_module.get_db()
    db = next(gen)
    # The yielded db is the mock.
    assert db is mock_db
    # Trigger the cleanup (finally).
    with pytest.raises(StopIteration):
        next(gen)
    # db.close() must have been called exactly once.
    mock_db.close.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Test: get_current_user — failure modes
# ─────────────────────────────────────────────────────────────────────────────

def test_get_current_user_invalid_signature_raises_401(secret_key, test_db_engine):
    """get_current_user raises 401 when JWT signature is invalid."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        # Encode with a DIFFERENT secret.
        bad_token = jwt.encode(
            {"sub": "auth@test.io"},
            "different_secret" + "y" * 20,  # different from monkeypatched
            algorithm=ALGORITHM,
        )

        with pytest.raises(HTTPException) as exc_info:
            # Wrap in a coroutine to drive the async function.
            import asyncio
            mock_request = MagicMock()
            mock_request.cookies.get.return_value = bad_token
            asyncio.run(get_current_user(request=mock_request, db=MagicMock()))

        assert exc_info.value.status_code == 401
        assert "Invalid authentication credentials" in exc_info.value.detail
    finally:
        app.dependency_overrides.clear()


def test_get_current_user_expired_token_raises_401(secret_key, test_db_engine):
    """get_current_user raises 401 when the token has expired."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        # Encode with a past expiry.
        expired = jwt.encode(
            {"sub": "auth@test.io", "exp": datetime.utcnow() - timedelta(hours=1)},
            secret_key,
            algorithm=ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            mock_request = MagicMock()
            mock_request.cookies.get.return_value = expired
            asyncio.run(get_current_user(request=mock_request, db=MagicMock()))
        assert exc_info.value.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_get_current_user_missing_sub_claim_raises_401(secret_key, test_db_engine):
    """get_current_user raises 401 when the token has no 'sub' claim."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        # No 'sub' claim.
        token_no_sub = jwt.encode(
            {"role": "admin"},  # no sub
            secret_key,
            algorithm=ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            mock_request = MagicMock()
            mock_request.cookies.get.return_value = token_no_sub
            asyncio.run(get_current_user(request=mock_request, db=MagicMock()))
        assert exc_info.value.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_get_current_user_not_in_db_raises_401(secret_key, test_db_engine):
    """get_current_user raises 401 when the 'sub' user doesn't exist in the DB."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        # Encode with an email that doesn't exist.
        token = jwt.encode(
            {"sub": "ghost@nowhere.io"},
            secret_key,
            algorithm=ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            mock_request = MagicMock()
            mock_request.cookies.get.return_value = token
            asyncio.run(get_current_user(request=mock_request, db=SessionLocal()))
        assert exc_info.value.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_get_current_user_inactive_user_raises_401(secret_key, test_db_engine, sample_user):
    """get_current_user raises 401 when user.is_active=False."""
    # Deactivate the user.
    sample_user.is_active = False
    test_db_engine.connect().execute(
        # SQLAlchemy 1.x style: just commit via the session
        __import__("sqlalchemy").text(
            f"UPDATE users SET is_active=0 WHERE id={sample_user.id}"
        )
    )
    # Use the session to commit
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    sess = SessionLocal()
    sess.query(User).filter(User.id == sample_user.id).update({"is_active": False})
    sess.commit()
    sess.close()

    def override_get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        token = jwt.encode(
            {"sub": sample_user.email},
            secret_key,
            algorithm=ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            mock_request = MagicMock()
            mock_request.cookies.get.return_value = token
            asyncio.run(get_current_user(request=mock_request, db=SessionLocal()))
        assert exc_info.value.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_get_current_user_success(secret_key, test_db_engine, sample_user):
    """get_current_user returns the user on a valid token + active user."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

    def override_get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        token = jwt.encode(
            {"sub": sample_user.email},
            secret_key,
            algorithm=ALGORITHM,
        )
        import asyncio
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = token
        user = asyncio.run(get_current_user(request=mock_request, db=SessionLocal()))
        assert user is not None
        assert user.email == sample_user.email
        assert user.role == "analyst"
    finally:
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Test: require_role
# ─────────────────────────────────────────────────────────────────────────────

def test_require_role_correct_role_returns_user(sample_user):
    """require_role returns the user when their role is in the allowed set."""
    checker = require_role("admin", "analyst")
    # The dependency factory returns an async function. Invoke it directly.
    import asyncio
    result = asyncio.run(checker(current_user=sample_user))
    assert result is sample_user


def test_require_role_wrong_role_raises_403(sample_user):
    """require_role raises 403 with role name in detail when role is wrong."""
    # sample_user has role "analyst". Only "admin" allowed.
    checker = require_role("admin")
    with pytest.raises(HTTPException) as exc_info:
        import asyncio
        asyncio.run(checker(current_user=sample_user))
    assert exc_info.value.status_code == 403
    assert "analyst" in exc_info.value.detail
    assert "admin" in exc_info.value.detail


def test_require_role_viewer_blocked_from_admin(sample_user):
    """require_role('admin') blocks a viewer/analyst user."""
    sample_user.role = "viewer"
    checker = require_role("admin")
    with pytest.raises(HTTPException) as exc_info:
        import asyncio
        asyncio.run(checker(current_user=sample_user))
    assert exc_info.value.status_code == 403
    assert "viewer" in exc_info.value.detail


# ─────────────────────────────────────────────────────────────────────────────
# Test: verify_password, create_access_token, init_auth_settings, log_audit
# ─────────────────────────────────────────────────────────────────────────────

def test_verify_password_returns_true_for_correct_password():
    """verify_password returns True when the password matches the hash."""
    from src.api.auth import verify_password
    hashed = get_password_hash("CorrectPassword")
    assert verify_password("CorrectPassword", hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_create_access_token_default_expiry(secret_key):
    """create_access_token encodes data with default expiry."""
    token = create_access_token({"sub": "x@test.io", "role": "admin"})
    payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
    assert payload["sub"] == "x@test.io"
    assert payload["role"] == "admin"
    assert "exp" in payload
    # Default is 480 minutes (8h) per ACCESS_TOKEN_EXPIRE_MINUTES.
    exp = datetime.utcfromtimestamp(payload["exp"])
    now = datetime.utcnow()
    delta = (exp - now).total_seconds()
    # Allow some tolerance.
    assert 470 * 60 < delta <= 480 * 60


def test_create_access_token_custom_expiry(secret_key):
    """create_access_token honours a custom expires_delta."""
    delta = timedelta(minutes=5)
    token = create_access_token({"sub": "y"}, expires_delta=delta)
    payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
    exp = datetime.utcfromtimestamp(payload["exp"])
    now = datetime.utcnow()
    real_delta = (exp - now).total_seconds()
    # 5 minutes ± 30 seconds tolerance.
    assert 4.5 * 60 < real_delta <= 5.5 * 60


def test_init_auth_settings_calls_get_jwt_secret_key(monkeypatch, secret_key):
    """init_auth_settings delegates to get_jwt_secret_key."""
    from src.api.auth import init_auth_settings
    # If the env var is missing, init_auth_settings should raise.
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable is required"):
        init_auth_settings()


def test_log_audit_writes_entry(test_db_engine, test_db_session, sample_user):
    """log_audit inserts an AuditLog row and commits."""
    from src.api.auth import log_audit
    log_audit(
        test_db_session,
        tenant_id=sample_user.tenant_id,
        user_email=sample_user.email,
        action="test_action",
        resource_id="res-1",
        details={"k": "v"},
        ip="127.0.0.1",
    )
    # Query and verify.
    from src.db.models import AuditLog
    entry = test_db_session.query(AuditLog).filter(AuditLog.action == "test_action").first()
    assert entry is not None
    assert entry.tenant_id == sample_user.tenant_id
    assert entry.user_email == sample_user.email
    assert entry.resource_id == "res-1"
    assert entry.details == {"k": "v"}
    assert entry.ip_address == "127.0.0.1"
