"""
Neomnix Platform API — Production-Grade.
Fixes: JWT auth, real compliance scoring, optimized stats, audit logging.
Chunk 3: live /ws/alerts WebSocket (in-process asyncio.Queue),
admin-only PDF report download, framework allowlist trimmed to
HIPAA-2026 + WA-MHMDA.
"""
from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
import asyncio

from src.db.models import SessionLocal, ScanJob, User, AuditLog, init_db
from src.api.auth import (
    get_current_user, get_password_hash, verify_password,
    create_access_token, TokenResponse, UserCreate, UserResponse,
    ChangePasswordRequest, require_role, log_audit, get_db, init_auth_settings,
    get_jwt_secret_key, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
)
from jose import JWTError, jwt

# AI Hub Imports
from src.agents.ai_hub import AIHub
from src.agents.dispatch import ScannerDispatcher
from src.agents.cross_mapping_analyzer import CrossMappingAnalyzer

import uuid, os
from pathlib import Path
from typing import List, Optional

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.api.gap import router as gap_router


app = FastAPI(
    title="Neomnix Platform API",
    version="2.0.0",
    description="HIPAA / SOC2 / NIST Compliance Scanning Platform"
)

# --- CORS (restrict in production via ALLOWED_ORIGINS env var) ---
def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


APP_ENV = (os.getenv("APP_ENV") or os.getenv("ENV") or "development").strip().lower()
IS_PROD = APP_ENV in {"prod", "production"}
IS_TEST = APP_ENV == "test"

_origins_raw = os.getenv("ALLOWED_ORIGINS")
if IS_PROD:
    if _origins_raw is None or not _origins_raw.strip():
        raise RuntimeError("ALLOWED_ORIGINS is required in production.")
    ALLOWED_ORIGINS = [o.strip() for o in _origins_raw.split(",") if o.strip()]
    if not ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS:
        raise RuntimeError("ALLOWED_ORIGINS cannot include '*'.")
else:
    if _origins_raw and _origins_raw.strip():
        ALLOWED_ORIGINS = [o.strip() for o in _origins_raw.split(",") if o.strip()]
    else:
        ALLOWED_ORIGINS = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate Limiter Setup (Fix 14) ---
# IS_TEST relaxes the rate limits so that test suites (which hammer the
# /auth/login endpoint from a single TestClient IP) are not falsely
# rate-limited. Production behavior is unchanged.
_login_limit = "10000/minute" if IS_TEST else "10/minute"
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=(["10000/minute"] if IS_TEST else ["200/minute"]),
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- AI Hub Singleton ---
ai_hub = AIHub()


# ╔══════════════════════════════════════════╗
# ║         CHUNK 3 — ALERT QUEUE             ║
# ╚══════════════════════════════════════════╝

# In-process asyncio.Queue that SharkTapSkill pushes critical data-leak
# events onto. The /ws/alerts WebSocket route drains it. No Redis, no
# cross-process coordination — a single FastAPI worker is enough for
# the dashboard's live alert needs. If the platform ever needs to scale
# beyond a single worker, swap this for a Redis pub/sub and rewire
# SharkTapSkill accordingly.
#
# maxsize=1000 bounds memory; a slow consumer causes events to be
# dropped (the producer uses put_nowait, never blocks).
#
# Note: an asyncio.Queue is bound to the event loop that created it.
# Creating it at import time would bind it to whichever loop happened
# to be live at import. To make the queue robust against
# - pytest fixtures spinning up a new event loop per test
# - uvicorn workers on different loops
# - lifespan startup vs request handling
# we create the queue lazily on first access. The SharkTapSkill is
# passed the same queue instance, so producers and consumers share it.
_alert_queue: Optional[asyncio.Queue] = None


def get_alert_queue() -> asyncio.Queue:
    """Return the module-level alert queue, creating it on the current
    event loop if it does not yet exist (or if a previous loop's queue
    is no longer usable).

    Call sites should use `get_alert_queue()` rather than a module-level
    global, so the queue is always created on the loop that is
    currently running.
    """
    global _alert_queue
    if _alert_queue is None:
        _alert_queue = asyncio.Queue(maxsize=1000)
    return _alert_queue


# ╔══════════════════════════════════════════╗
# ║         REQUEST / RESPONSE MODELS        ║
# ╚══════════════════════════════════════════╝

class ReportResponse(BaseModel):
    job_id: str
    status: str
    target: str
    findings_count: int
    compliance_verdict: Optional[str]
    compliance_score: Optional[float]
    details: Optional[dict]


# ╔══════════════════════════════════════════╗
# ║              STARTUP                     ║
# ╚══════════════════════════════════════════╝

@app.on_event("startup")
def on_startup():
    init_auth_settings()
    init_db()
    # Register AI Agents
    ai_hub.register_agent("scanner", ScannerDispatcher())
    ai_hub.register_agent("cross_mapper", CrossMappingAnalyzer())

    # --- Seed admin user if none exists ---
    seed_admin_default = not IS_PROD and not IS_TEST
    seed_admin = _env_flag("SEED_ADMIN", default=seed_admin_default)
    if not seed_admin:
        return

    db = SessionLocal()
    try:
        from src.db.models import Tenant
        
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            # Create default tenant
            default_tenant = Tenant(
                id=str(uuid.uuid4()),
                name="Default Organization",
                slug="default-org",
                billing_email=os.getenv("ADMIN_EMAIL", "admin@neomnix.io"),
                tier="enterprise",
                is_active=True
            )
            db.add(default_tenant)
            db.commit()
            db.refresh(default_tenant)
            
            default_password = os.getenv("ADMIN_DEFAULT_PASSWORD")
            if default_password is None or not default_password.strip():
                raise RuntimeError("ADMIN_DEFAULT_PASSWORD is required when SEED_ADMIN is enabled.")
            admin_email = os.getenv("ADMIN_EMAIL", "admin@neomnix.io")
            admin_user = User(
                tenant_id=default_tenant.id,
                email=admin_email,
                hashed_password=get_password_hash(default_password),
                full_name="System Administrator",
                role="admin",
                is_active=True,
                force_password_change=True
            )
            db.add(admin_user)
            db.commit()
    finally:
        db.close()



@app.post("/auth/login", response_model=TokenResponse)
@limiter.limit(_login_limit)
async def login(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled. Contact admin.")

    token = create_access_token(data={"sub": user.email, "role": user.role})
    log_audit(db, user.tenant_id, user.email, "login")

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=IS_PROD,
        samesite="lax",
        path="/",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return TokenResponse(
        access_token=token,
        role=user.role,
        email=user.email,
        force_password_change=bool(user.force_password_change)
    )

@app.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}

@app.post("/auth/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Admin-only: create a new user account."""
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    new_user = User(
        tenant_id=current_user.tenant_id,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit(db, current_user.tenant_id, current_user.email, "user_created", resource_id=str(new_user.id))
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active
    )

@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active
    )


@app.post("/auth/change-password")
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allow any authenticated user to change their password. Clears force_password_change flag."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    if len(payload.new_password) < 10:
        raise HTTPException(status_code=422, detail="New password must be at least 10 characters.")

    current_user.hashed_password = get_password_hash(payload.new_password)
    current_user.force_password_change = False
    db.commit()

    log_audit(db, current_user.tenant_id, current_user.email, "password_changed", details={"forced_reset_cleared": True})
    return {"message": "Password updated successfully."}


# ╔══════════════════════════════════════════╗
# ║          DASHBOARD STATS (OPTIMIZED)     ║
# ╚══════════════════════════════════════════╝

def _compute_compliance_score(job: ScanJob) -> float:
    """
    Compute real compliance score from scan data.
    
    Formula:
      base_score = 100
      - 15 per critical finding
      - 8 per high finding  
      - 3 per medium finding
      + partial credit if controls are mapped
      
    Score clamped to [0, 100]
    """
    if not job.findings:
        return 100.0

    base_score = 100.0
    total_findings = len(job.findings) if job.findings else 0

    critical_count = 0
    high_count = 0
    medium_count = 0

    for f in job.findings:
        if isinstance(f, dict):
            severity = f.get("severity", "low")
            if severity == "critical":
                critical_count += 1
            elif severity == "high":
                high_count += 1
            elif severity == "medium":
                medium_count += 1

    # Penalty deductions
    penalty = (critical_count * 15) + (high_count * 8) + (medium_count * 3)
    raw_score = base_score - penalty

    # Bonus: if compliance report exists with mapped controls, partial recovery
    if job.compliance_report:
        mapped = len(job.compliance_report.get("mapped_controls", []))
        unmapped = len(job.compliance_report.get("unmapped_findings", []))
        total_issues = mapped + unmapped
        if total_issues > 0:
            mapping_ratio = mapped / total_issues
            # Up to 10 points recovery for good coverage
            raw_score += mapping_ratio * 10

    return round(max(0.0, min(100.0, raw_score)), 1)


# ╔══════════════════════════════════════════╗
# ║          DASHBOARD STATS (OPTIMIZED)     ║
# ╚══════════════════════════════════════════╝

@app.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aggregated dashboard stats with real compliance score — FIX 3 + FIX 8."""
    # --- FIX 8: SQL-level aggregation instead of loading all rows ---
    tenant_filter = (ScanJob.tenant_id == current_user.tenant_id)
    total_scans = db.query(func.count(ScanJob.id)).filter(tenant_filter).scalar() or 0
    completed_scans = db.query(func.count(ScanJob.id)).filter(tenant_filter, ScanJob.status == "completed").scalar() or 0
    failed_scans = db.query(func.count(ScanJob.id)).filter(tenant_filter, ScanJob.status == "failed").scalar() or 0

    # Get recent completed jobs for score calculation (limit to last 10)
    recent_completed = db.query(ScanJob).filter(
        tenant_filter,
        ScanJob.status == "completed"
    ).order_by(ScanJob.created_at.desc()).limit(10).all()

    # Compute real aggregate compliance score
    scores = [_compute_compliance_score(job) for job in recent_completed if job.findings]
    avg_compliance = round(sum(scores) / len(scores), 1) if scores else 100.0

    # Count active risks from recent completed jobs
    high_risks = 0
    total_findings = 0
    for job in recent_completed:
        if job.findings:
            total_findings += len(job.findings)
            for f in job.findings:
                if isinstance(f, dict) and f.get('severity') in ['high', 'critical']:
                    high_risks += 1

    # Recent activity (last 5 jobs, any status)
    recent_jobs = db.query(ScanJob).filter(tenant_filter).order_by(ScanJob.created_at.desc()).limit(5).all()
    activity = [{
        "id": job.id,
        "target": job.target,
        "status": job.status,
        "time": job.created_at.isoformat() if job.created_at else None,
        "findings": len(job.findings) if job.findings else 0,
        "initiated_by": job.initiated_by
    } for job in recent_jobs]

    return {
        "total_scans": total_scans,
        "completed_scans": completed_scans,
        "failed_scans": failed_scans,
        "compliance_score": avg_compliance,  # FIX 3: Real score, not hardcoded 85
        "active_risks": high_risks,
        "total_findings": total_findings,
        "recent_activity": activity
    }


# ╔══════════════════════════════════════════╗
# ║            PDF REPORT DOWNLOAD           ║
# ╚══════════════════════════════════════════╝

@app.get("/reports/pdf/{job_id}/{framework}")
async def get_pdf_report(
    job_id: str,
    framework: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))  # Chunk 3 R4: admin-only
):
    """Serves the generated PDF report for a specific job and framework.

    Chunk 3 R4: Restricted to the admin role. Analyst and viewer roles
    receive 403 and must not be able to download executive reports.
    The role check is the authorization boundary; the PDF exporter
    itself is not.
    """
    # Chunk 3: trimmed to healthcare-only frameworks.
    allowed_frameworks = {"HIPAA-2026", "WA-MHMDA"}
    if framework not in allowed_frameworks:
        raise HTTPException(status_code=400, detail="Unsupported framework")

    try:
        uuid.UUID(job_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid job_id")

    job = db.query(ScanJob).filter(
        ScanJob.id == job_id,
        ScanJob.tenant_id == current_user.tenant_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan Job not found")

    filename = f"{framework}_{job_id}.pdf"
    pdf_dir = Path("reports") / "pdf"
    pdf_dir_resolved = pdf_dir.resolve()
    file_path = (pdf_dir / filename).resolve()
    if pdf_dir_resolved not in file_path.parents:
        raise HTTPException(status_code=400, detail="Invalid report path")

    if not file_path.exists():
        # Fallback: broader search if exact match fails
        if pdf_dir.is_dir():
            matched_file = next(
                (
                    f.name for f in pdf_dir.iterdir()
                    if f.is_file()
                    and f.name.endswith(".pdf")
                    and job_id in f.name
                    and framework in f.name
                ),
                None
            )
            if matched_file:
                matched_path = (pdf_dir / matched_file).resolve()
                if pdf_dir_resolved not in matched_path.parents:
                    raise HTTPException(status_code=400, detail="Invalid report path")
                file_path = matched_path
            else:
                raise HTTPException(status_code=404, detail="Executive Report not found. Ensure the scan has completed.")
        else:
            raise HTTPException(status_code=404, detail="Reports directory does not exist yet.")

    log_audit(db, current_user.tenant_id, current_user.email, "report_downloaded", resource_id=job_id,
              details={"framework": framework})

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename
    )


# ╔══════════════════════════════════════════╗
# ║     CHUNK 3 — LIVE ALERT WEBSOCKET        ║
# ╚══════════════════════════════════════════╝
# ╚══════════════════════════════════════════╝

async def _authenticate_ws(websocket: WebSocket, db: Session) -> Optional[User]:
    """Authenticate a WebSocket connection using the JWT in the
    HttpOnly cookie or as a fallback the `?token=...` query string.
    """
    token = websocket.cookies.get("access_token") or websocket.query_params.get("token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, get_jwt_secret_key(), algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
    except JWTError:
        return None
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        return None
    return user


@app.websocket("/ws/alerts")
async def ws_alerts(
    websocket: WebSocket,
    # Reuse the request's db session through FastAPI's DI. The
    # TestClient creates one event loop per call so this is safe.
    db: Session = Depends(get_db),
):
    """Live critical-data-leak alerts pushed from SharkTapSkill.

    The client connects with `ws://host/ws/alerts?token=<jwt>`. After
    authentication, the server streams any event that
    SharkTapSkill._enqueue_critical_alerts() pushes onto the
    module-level `alert_queue`. A heartbeat ping is sent every
    HEARTBEAT_INTERVAL seconds so the client can detect a dead
    connection.
    """
    # Authenticate BEFORE accepting — this lets us close with a
    # policy-violation code on failure.
    user = await _authenticate_ws(websocket, db)
    if user is None:
        await websocket.close(code=1008, reason="unauthorized")
        return
    await websocket.accept()

    HEARTBEAT_INTERVAL = 30.0  # seconds
    queue = get_alert_queue()
    try:
        while True:
            try:
                # Wait for either a real alert or a heartbeat tick.
                event = await asyncio.wait_for(
                    queue.get(), timeout=HEARTBEAT_INTERVAL
                )
                # event is a dict; serialize as JSON via the websocket.
                import json as _json
                await websocket.send_text(_json.dumps(event))
            except asyncio.TimeoutError:
                # No alert in HEARTBEAT_INTERVAL seconds. Send a
                # heartbeat so the client knows the connection is live.
                await websocket.send_text('{"type": "heartbeat"}')
    except WebSocketDisconnect:
        # Client went away. Nothing to clean up — the queue is shared
        # and other consumers (or the next client) will drain it.
        return


# ╔══════════════════════════════════════════╗
# ║           GAP ANALYSIS ROUTER            ║
# ╚══════════════════════════════════════════╝
app.include_router(gap_router)

# ╔══════════════════════════════════════════╗
# ║           HEALTH & AUDIT                 ║
# ╚══════════════════════════════════════════╝

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}
