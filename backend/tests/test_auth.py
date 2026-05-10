"""
Unit tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.models import Base, User, Tenant, SessionLocal
from src.api.main import app, get_db
from src.api.auth import get_password_hash, verify_password


@pytest.fixture
def test_db():
    """Create test database."""
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
    return TestingSessionLocal()


@pytest.fixture
def client(test_db):
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def admin_user(test_db):
    """Create test admin user."""
    tenant = Tenant(
        id="tenant-test",
        name="Test Tenant",
        slug="test-tenant",
        billing_email="billing@test.io",
        tier="starter",
        is_active=True,
    )
    test_db.add(tenant)
    test_db.commit()

    user = User(
        tenant_id=tenant.id,
        email="admin@test.io",
        hashed_password=get_password_hash("TestPassword123"),
        full_name="Test Admin",
        role="admin",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


class TestLogin:
    def test_login_success(self, client, admin_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            data={"username": "admin@test.io", "password": "TestPassword123"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["role"] == "admin"
    
    def test_login_invalid_password(self, client, admin_user):
        """Test login with wrong password."""
        response = client.post(
            "/auth/login",
            data={"username": "admin@test.io", "password": "WrongPassword"}
        )
        assert response.status_code == 401
        assert "Incorrect" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent email."""
        response = client.post(
            "/auth/login",
            data={"username": "notfound@test.io", "password": "password"}
        )
        assert response.status_code == 401


class TestGetMe:
    def test_get_me_authenticated(self, client, admin_user):
        """Test getting current user info."""
        login_response = client.post(
            "/auth/login",
            data={"username": "admin@test.io", "password": "TestPassword123"}
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == "admin@test.io"
        assert response.json()["role"] == "admin"
    
    def test_get_me_unauthenticated(self, client):
        """Test getting current user without auth."""
        response = client.get("/auth/me")
        assert response.status_code == 401


class TestHealthCheck:
    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
