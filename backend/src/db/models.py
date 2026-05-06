from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, Float, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Use environment variable for DB URL, default to SQLite for dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cybersurx.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-TENANCY MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class Tenant(Base):
    """Multi-tenant organization model."""
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, index=True)  # UUID
    name = Column(String, unique=True, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)  # URL-friendly identifier
    description = Column(Text, nullable=True)
    logo_url = Column(String, nullable=True)
    billing_email = Column(String, nullable=False)
    tier = Column(String, default="starter")  # starter, professional, enterprise
    stripe_customer_id = Column(String, nullable=True, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="tenant")
    scan_jobs = relationship("ScanJob", back_populates="tenant")
    audit_logs = relationship("AuditLog", back_populates="tenant")
    subscriptions = relationship("Subscription", back_populates="tenant")


class Subscription(Base):
    """Billing subscription model for tenants."""
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, index=True)  # UUID
    tenant_id = Column(String, ForeignKey("tenants.id"), index=True, nullable=False)
    stripe_subscription_id = Column(String, nullable=True, unique=True)
    stripe_product_id = Column(String, nullable=True)
    status = Column(String, default="inactive")  # active, past_due, canceled, trialing
    tier = Column(String, default="starter")
    price_per_month = Column(Float, nullable=True)
    seats_limit = Column(Integer, default=5)
    started_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="subscriptions")


class User(Base):
    """User model for JWT authentication with tenant association."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), index=True, nullable=False)
    email = Column(String, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="analyst")  # admin, analyst, viewer
    is_active = Column(Boolean, default=True)
    force_password_change = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")


class ScanJob(Base):
    """Database model for a Scan Job with multi-tenancy."""
    __tablename__ = "scan_jobs"

    id = Column(String, primary_key=True, index=True)  # UUID
    tenant_id = Column(String, ForeignKey("tenants.id"), index=True, nullable=False)
    target = Column(String, index=True)
    status = Column(String)  # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    initiated_by = Column(String, nullable=True)  # user email for audit

    # Store results as JSON for flexibility
    findings = Column(JSON, default=list)
    compliance_report = Column(JSON, nullable=True)

    # Metrics
    final_intensity = Column(Integer)
    confidence_score = Column(Float)

    tenant = relationship("Tenant", back_populates="scan_jobs")


class AuditLog(Base):
    """Audit trail for all API actions with multi-tenancy."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), index=True, nullable=False)
    user_email = Column(String, index=True)
    action = Column(String)  # scan_initiated, report_downloaded, login, etc.
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)

    tenant = relationship("Tenant", back_populates="audit_logs")


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE & CONTROL MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedControl(Base):
    """Unified control framework model."""
    __tablename__ = "unified_controls"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority_level = Column(String, default="medium")  # high, medium, low
    overlap_score = Column(Integer, default=0)
    required_evidence = Column(JSON, default=list)
    category = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ControlCitation(Base):
    """Citation linking controls to compliance frameworks."""
    __tablename__ = "control_citations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    control_id = Column(String, ForeignKey("unified_controls.id"), index=True)
    framework = Column(String, index=True)  # hipaa, soc2, nist, mhmda
    citation = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ControlMapping(Base):
    """Mapping between multiple control frameworks."""
    __tablename__ = "control_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_framework = Column(String, index=True)
    source_control_id = Column(String, ForeignKey("unified_controls.id"))
    target_framework = Column(String, index=True)
    target_control_id = Column(String, ForeignKey("unified_controls.id"))
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
