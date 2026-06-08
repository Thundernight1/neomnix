"""
PyTest configuration and fixtures for Neomnix GRC
"""

import pytest
import asyncio
from typing import Generator
import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SEED_ADMIN", "false")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-please-change-32chars+")


@pytest.fixture(autouse=True)
def bypass_rate_limits_globally():
    """Disable rate limiting globally for all tests."""
    from src.api.main import limiter
    limiter.enabled = False

@pytest.fixture(autouse=True)
def reset_ttf_state():
    """Clear PDF exporter TTF state before each test so they don't pollute each other."""
    from src.utils.pdf_exporter import _TTF_STATE
    _TTF_STATE["attempted"] = False
    _TTF_STATE["loaded"] = False
    _TTF_STATE["family"] = "Helvetica"
    _TTF_STATE["regular"] = None
    _TTF_STATE["bold"] = None
    _TTF_STATE["italic"] = None
    _TTF_STATE["bold_italic"] = None
    yield


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast, no external deps)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (requires services)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
    config.addinivalue_line(
        "markers", "requires_zap: mark test as requiring OWASP ZAP"
    )
    config.addinivalue_line(
        "markers", "requires_llm: mark test as requiring LLM API"
    )


@pytest.fixture
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db_url() -> str:
    """Test database URL"""
    return "sqlite:///./test.db"


@pytest.fixture
def redis_url() -> str:
    """Redis connection URL for tests"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis_url


@pytest.fixture
def jwt_secret() -> str:
    """JWT secret for test tokens"""
    return os.environ["JWT_SECRET_KEY"]


@pytest.fixture
def test_admin_email() -> str:
    """Test admin email"""
    return "test@neomnix.io"
