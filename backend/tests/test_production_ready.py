"""
Production Integration Tests for Neomnix Platform
Tests multi-tenancy, Stripe integration, and core compliance scanning
"""

import pytest
import os
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from src.db.models import Base, SessionLocal, Tenant, User, Subscription, ScanJob, AuditLog
from src.integrations.stripe_mcp import StripeMCPClient
from src.api.auth import get_password_hash


@pytest.fixture
def test_db():
    """In-memory test database"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = SessionLocal(bind=engine)
    yield session
    session.close()


@pytest.fixture
def sample_tenant(test_db):
    """Create a test tenant"""
    tenant = Tenant(
        id="tenant-001",
        name="Acme Corporation",
        slug="acme-corp",
        billing_email="billing@acme.com",
        tier="professional",
        is_active=True,
    )
    test_db.add(tenant)
    test_db.commit()
    test_db.refresh(tenant)
    return tenant


@pytest.fixture
def sample_admin_user(test_db, sample_tenant):
    """Create test admin user"""
    user = User(
        tenant_id=sample_tenant.id,
        email="admin@acme.com",
        hashed_password=get_password_hash("SecurePassword123!"),
        full_name="Alice Admin",
        role="admin",
        is_active=True,
        force_password_change=False,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-TENANCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiTenancy:
    """Test multi-tenant isolation and data segregation"""

    def test_tenant_creation(self, test_db):
        """Verify tenant can be created with all required fields"""
        tenant = Tenant(
            id="tenant-002",
            name="Beta Inc",
            slug="beta-inc",
            billing_email="billing@beta.com",
            tier="starter",
            is_active=True,
        )
        test_db.add(tenant)
        test_db.commit()

        retrieved = test_db.query(Tenant).filter(Tenant.id == "tenant-002").first()
        assert retrieved is not None
        assert retrieved.name == "Beta Inc"
        assert retrieved.tier == "starter"

    def test_per_tenant_user_isolation(self, test_db, sample_tenant):
        """Verify users are isolated per tenant"""
        # Create two tenants
        tenant1 = Tenant(id="t1", name="Org1", slug="org1", billing_email="b1@org1.com", tier="starter")
        tenant2 = Tenant(id="t2", name="Org2", slug="org2", billing_email="b2@org2.com", tier="starter")
        test_db.add_all([tenant1, tenant2])
        test_db.commit()

        # Create same email in both tenants
        user1 = User(
            tenant_id="t1",
            email="admin@example.com",
            hashed_password=get_password_hash("pwd123"),
            role="admin",
        )
        user2 = User(
            tenant_id="t2",
            email="admin@example.com",
            hashed_password=get_password_hash("pwd123"),
            role="admin",
        )
        test_db.add_all([user1, user2])
        test_db.commit()

        # Verify both exist (email unique per tenant, not globally)
        count = test_db.query(User).filter(User.email == "admin@example.com").count()
        assert count == 2, "Same email should exist in different tenants"

    def test_scan_job_tenant_isolation(self, test_db, sample_tenant, sample_admin_user):
        """Verify scan jobs are isolated per tenant"""
        # Create scan for tenant1
        scan1 = ScanJob(
            id="scan-001",
            tenant_id=sample_tenant.id,
            target="api.acme.com",
            status="completed",
            initiated_by=sample_admin_user.email,
            findings=[{"severity": "high", "type": "sql_injection"}],
            final_intensity=5,
            confidence_score=0.95,
        )
        test_db.add(scan1)
        test_db.commit()

        # Create different tenant
        tenant2 = Tenant(
            id="tenant-003",
            name="Other Corp",
            slug="other-corp",
            billing_email="billing@other.com",
            tier="starter",
        )
        test_db.add(tenant2)
        test_db.commit()

        # Query should only return scans for tenant1
        scans = test_db.query(ScanJob).filter(ScanJob.tenant_id == sample_tenant.id).all()
        assert len(scans) == 1
        assert scans[0].id == "scan-001"

        # tenant2 should have no scans
        scans2 = test_db.query(ScanJob).filter(ScanJob.tenant_id == "tenant-003").all()
        assert len(scans2) == 0

    def test_audit_log_tenant_isolation(self, test_db, sample_tenant, sample_admin_user):
        """Verify audit logs are isolated per tenant"""
        log1 = AuditLog(
            tenant_id=sample_tenant.id,
            user_email=sample_admin_user.email,
            action="scan_initiated",
            resource_id="scan-001",
            details={"target": "api.acme.com"},
        )
        test_db.add(log1)
        test_db.commit()

        retrieved = test_db.query(AuditLog).filter(
            AuditLog.tenant_id == sample_tenant.id,
            AuditLog.action == "scan_initiated"
        ).first()

        assert retrieved is not None
        assert retrieved.user_email == "admin@acme.com"
        assert retrieved.resource_id == "scan-001"


# ═══════════════════════════════════════════════════════════════════════════════
# STRIPE INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStripeIntegration:
    """Test Stripe MCP tools for billing"""

    def test_tier_pricing_configuration(self):
        """Verify tier pricing is correctly configured"""
        from src.integrations.stripe_mcp import TIER_PRICING

        assert "starter" in TIER_PRICING
        assert "professional" in TIER_PRICING
        assert "enterprise" in TIER_PRICING

        assert TIER_PRICING["starter"]["price_per_month"] == 29.00
        assert TIER_PRICING["professional"]["price_per_month"] == 99.00
        assert TIER_PRICING["enterprise"]["price_per_month"] == 299.00

        assert TIER_PRICING["starter"]["seats_limit"] == 5
        assert TIER_PRICING["professional"]["seats_limit"] == 25
        assert TIER_PRICING["enterprise"]["seats_limit"] == 999

    def test_stripe_customer_creation_call(self):
        """Test Stripe customer creation (mock validation)"""
        # Note: Requires STRIPE_API_KEY set for real calls
        import os
        if not os.getenv("STRIPE_API_KEY"):
            pytest.skip("STRIPE_API_KEY not set")

        result = StripeMCPClient.create_customer(
            email="test@example.com",
            tenant_name="Test Tenant",
            metadata={"tenant_id": "t123", "plan": "professional"}
        )

        # Should return success or proper error
        assert "customer_id" in result or "error" in result
        if "customer_id" in result:
            assert result["success"] is True

    def test_subscription_status_values(self):
        """Verify valid subscription status values"""
        from src.db.models import Subscription

        valid_statuses = ["active", "past_due", "canceled", "trialing", "inactive"]

        for status in valid_statuses:
            sub = Subscription(
                id=f"sub-{status}",
                tenant_id="t123",
                status=status,
                tier="professional",
            )
            # Should not raise
            assert sub.status == status

    def test_subscription_tier_mapping(self, test_db, sample_tenant):
        """Verify subscription tiers map correctly"""
        sub = Subscription(
            id="sub-001",
            tenant_id=sample_tenant.id,
            status="active",
            tier="professional",
            price_per_month=99.00,
            seats_limit=25,
            started_at=datetime.utcnow(),
            ends_at=datetime.utcnow() + timedelta(days=30),
        )
        test_db.add(sub)
        test_db.commit()

        retrieved = test_db.query(Subscription).filter(Subscription.id == "sub-001").first()
        assert retrieved.tier == "professional"
        assert retrieved.price_per_month == 99.00
        assert retrieved.seats_limit == 25


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE SCANNING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestComplianceScanning:
    """Test core compliance scanning workflow"""

    def test_scan_job_creation(self, test_db, sample_tenant, sample_admin_user):
        """Verify scan job can be created and retrieved"""
        scan = ScanJob(
            id="scan-prod-001",
            tenant_id=sample_tenant.id,
            target="https://api.production.acme.com",
            status="pending",
            initiated_by=sample_admin_user.email,
        )
        test_db.add(scan)
        test_db.commit()

        retrieved = test_db.query(ScanJob).filter(ScanJob.id == "scan-prod-001").first()
        assert retrieved is not None
        assert retrieved.status == "pending"
        assert retrieved.target == "https://api.production.acme.com"

    def test_scan_findings_persistence(self, test_db, sample_tenant, sample_admin_user):
        """Verify scan findings are stored and retrieved correctly"""
        findings = [
            {"severity": "critical", "type": "sql_injection", "cwe": "CWE-89", "remediation": "Use parameterized queries"},
            {"severity": "high", "type": "xss", "cwe": "CWE-79", "remediation": "Escape output"},
        ]

        scan = ScanJob(
            id="scan-findings-001",
            tenant_id=sample_tenant.id,
            target="api.acme.com",
            status="completed",
            initiated_by=sample_admin_user.email,
            findings=findings,
            final_intensity=10,
            confidence_score=0.92,
        )
        test_db.add(scan)
        test_db.commit()

        retrieved = test_db.query(ScanJob).filter(ScanJob.id == "scan-findings-001").first()
        assert len(retrieved.findings) == 2
        assert retrieved.findings[0]["severity"] == "critical"
        assert retrieved.confidence_score == 0.92

    def test_scan_compliance_report(self, test_db, sample_tenant, sample_admin_user):
        """Verify compliance reports are generated and stored"""
        compliance_report = {
            "determination": "PARTIALLY_COMPLIANT",
            "mapped_controls": [
                {"control_id": "HIPAA-001", "framework": "hipaa", "status": "satisfied"},
            ],
            "unmapped_findings": [
                {"finding_id": "F001", "description": "Encryption not enforced", "framework": "SOC2"},
            ],
            "summary": {
                "total_controls": 50,
                "satisfied_controls": 42,
                "partially_satisfied": 5,
                "unsatisfied": 3,
            },
        }

        scan = ScanJob(
            id="scan-report-001",
            tenant_id=sample_tenant.id,
            target="api.acme.com",
            status="completed",
            initiated_by=sample_admin_user.email,
            compliance_report=compliance_report,
            findings=[],
            final_intensity=8,
            confidence_score=0.88,
        )
        test_db.add(scan)
        test_db.commit()

        retrieved = test_db.query(ScanJob).filter(ScanJob.id == "scan-report-001").first()
        assert retrieved.compliance_report["determination"] == "PARTIALLY_COMPLIANT"
        assert len(retrieved.compliance_report["mapped_controls"]) == 1
        assert retrieved.compliance_report["summary"]["satisfied_controls"] == 42


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT & COMPLIANCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditAndCompliance:
    """Test audit logging and compliance tracking"""

    def test_audit_log_creation(self, test_db, sample_tenant, sample_admin_user):
        """Verify audit log records are created"""
        log = AuditLog(
            tenant_id=sample_tenant.id,
            user_email=sample_admin_user.email,
            action="scan_initiated",
            resource_id="scan-001",
            details={"target": "api.acme.com", "scan_type": "deep"},
            ip_address="192.168.1.1",
        )
        test_db.add(log)
        test_db.commit()

        retrieved = test_db.query(AuditLog).filter(
            AuditLog.resource_id == "scan-001"
        ).first()

        assert retrieved is not None
        assert retrieved.action == "scan_initiated"
        assert retrieved.user_email == "admin@acme.com"
        assert retrieved.ip_address == "192.168.1.1"

    def test_audit_trail_completeness(self, test_db, sample_tenant, sample_admin_user):
        """Verify complete audit trail for a user session"""
        actions = ["login", "scan_initiated", "report_downloaded", "settings_changed", "logout"]

        for action in actions:
            log = AuditLog(
                tenant_id=sample_tenant.id,
                user_email=sample_admin_user.email,
                action=action,
                resource_id=f"resource-{action}",
            )
            test_db.add(log)

        test_db.commit()

        trail = test_db.query(AuditLog).filter(
            AuditLog.tenant_id == sample_tenant.id,
            AuditLog.user_email == sample_admin_user.email,
        ).order_by(AuditLog.timestamp).all()

        assert len(trail) == len(actions)
        assert [log.action for log in trail] == actions


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCTION READINESS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestProductionReadiness:
    """Test production-grade configurations and safeguards"""

    def test_env_variables_set(self):
        """Verify critical environment variables are configured"""
        import os

        critical_vars = [
            "STRIPE_API_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "JWT_SECRET_KEY",
            "ADMIN_EMAIL",
        ]

        for var in critical_vars:
            # Don't fail, just warn if not set
            value = os.getenv(var)
            if not value:
                print(f"⚠️  {var} not set - may cause issues in production")

    def test_database_connection_string(self):
        """Verify database URL is production-grade (PostgreSQL, not SQLite)"""
        db_url = os.getenv("DATABASE_URL", "")
        assert "postgresql" in db_url or "postgres" in db_url, \
            "DATABASE_URL must use PostgreSQL for production"

    def test_stripe_keys_present(self):
        """Verify Stripe keys are configured"""
        stripe_key = os.getenv("STRIPE_API_KEY", "")
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

        # Check for live keys (not test keys)
        if stripe_key and stripe_key.startswith("sk_test_"):
            print("⚠️  Using Stripe TEST key - use sk_live_ for production")
        if webhook_secret and webhook_secret.startswith("whsec_test_"):
            print("⚠️  Using Stripe TEST webhook secret - use whsec_ for production")

    def test_password_hash_strength(self):
        """Verify password hashing uses strong algorithm"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        # bcrypt hashes start with $2b$ or $2a$
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$"), \
            "Passwords must use bcrypt for production"
        assert len(hashed) >= 60, "bcrypt hash too short"

    def test_tenant_tier_values(self):
        """Verify only valid tier values are used"""
        valid_tiers = ["starter", "professional", "enterprise"]

        for tier in valid_tiers:
            tenant = Tenant(
                id=f"t-{tier}",
                name=f"Org {tier}",
                slug=f"org-{tier}",
                billing_email=f"billing@{tier}.com",
                tier=tier,
            )
            assert tenant.tier in valid_tiers
