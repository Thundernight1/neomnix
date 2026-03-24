from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Use environment variable for DB URL, default to SQLite for dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cybersurx.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    """User model for JWT authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="analyst")  # admin, analyst, viewer
    is_active = Column(Boolean, default=True)
    force_password_change = Column(Boolean, default=False)  # True for newly seeded accounts
    created_at = Column(DateTime, default=datetime.utcnow)

class ScanJob(Base):
    """
    Database model for a Scan Job.
    Replaces ephemeral JSON files with a persistent record.
    """
    __tablename__ = "scan_jobs"

    id = Column(String, primary_key=True, index=True) # UUID
    target = Column(String, index=True)
    status = Column(String) # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    initiated_by = Column(String, nullable=True)  # user email for audit
    
    # Store results as JSON for flexibility
    findings = Column(JSON, default=list) 
    compliance_report = Column(JSON, nullable=True)
    
    # Metrics
    final_intensity = Column(Integer)
    confidence_score = Column(Float)

class AuditLog(Base):
    """Audit trail for all API actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String, index=True)
    action = Column(String)  # scan_initiated, report_downloaded, login, etc.
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)
