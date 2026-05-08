"""
Neomnix Platform API — Production-Grade.
Fixes: JWT auth, real compliance scoring, optimized stats, audit logging.
"""
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.models import SessionLocal, engine, Base, ScanJob, User, AuditLog, init_db
from src.worker.tasks import run_neomnix_scan
from src.api.auth import (
    get_current_user, get_password_hash, verify_password,
    create_access_token, TokenResponse, UserCreate, UserResponse,
    ChangePasswordRequest, require_role, log_audit, get_db, oauth2_scheme
)

# AI Hub Imports
from src.agents.ai_hub import AIHub
from src.agents.dispatch import ScannerDispatcher
from src.agents.cross_mapping_analyzer import CrossMappingAnalyzer
from src.agents.llm_agent import LLMAgent
from src.agents.cloud_scanner import CloudScannerAgent
from src.skills.sharktap_skill import SharkTapSkill

import uuid, os, shutil, tempfile
from typing import List, Optional, Dict, Any
from datetime import timedelta
from fastapi import UploadFile, File

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


app = FastAPI(
    title="Neomnix Platform API",
    version="2.0.0",
    description="HIPAA / SOC2 / NIST Compliance Scanning Platform"
)

# --- CORS (restrict in production via ALLOWED_ORIGINS env var) ---
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate Limiter Setup (Fix 14) ---
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- AI Hub Singleton ---
ai_hub = AIHub()


# ╔══════════════════════════════════════════╗
# ║         REQUEST / RESPONSE MODELS        ║
# ╚══════════════════════════════════════════╝

class ScanRequest(BaseModel):
    target: str
    scan_type: str = "quick"  # quick, deep, full

class CommandRequest(BaseModel):
    command: str
    context: Optional[Dict[str, Any]] = {}

class ScanResponse(BaseModel):
    job_id: str
    status: str
    target: str

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
    init_db()
    # Register AI Agents
    ai_hub.register_agent("scanner", ScannerDispatcher())
    ai_hub.register_agent("cross_mapper", CrossMappingAnalyzer())
    ai_hub.register_agent("llm", LLMAgent())
    ai_hub.register_agent("cloud_scanner", CloudScannerAgent())

    # --- Seed admin user if none exists ---
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
            
            default_password = os.getenv("ADMIN_DEFAULT_PASSWORD", "Neomnix2026!")
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
            print(f"✅ Admin account provisioned: {admin_email} — password change required on first login.")
    finally:
        db.close()



# @app.post("/auth/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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
    log_audit(db, user.email, "login")

    return TokenResponse(
        access_token=token,
        role=user.role,
        email=user.email,
        force_password_change=bool(user.force_password_change)
    )

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
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit(db, current_user.email, "user_created", resource_id=str(new_user.id))
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

    log_audit(db, current_user.email, "password_changed", details={"forced_reset_cleared": True})
    return {"message": "Password updated successfully."}


# ╔══════════════════════════════════════════╗
# ║        PROTECTED SCAN ENDPOINTS          ║
# ╚══════════════════════════════════════════╝

@app.post("/command")
async def execute_ai_command(
    request: CommandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute a natural language command through the AI Hub."""
    context = request.context or {}
    context['db'] = db
    context['user'] = current_user.email

    result = await ai_hub.process_command(request.command, context)
    log_audit(db, current_user.email, "ai_command", details={"command": request.command})
    return result

@app.post("/scan", response_model=ScanResponse)
async def trigger_scan(
    request: Request,
    scan_request: ScanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "analyst"))
):
    """Initiate a compliance scan. Requires admin or analyst role."""
    job_id = str(uuid.uuid4())

    new_job = ScanJob(
        id=job_id,
        target=scan_request.target,
        status="pending",
        initiated_by=current_user.email
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Determine Intensity
    intensity = {"quick": 1, "deep": 5, "full": 10}.get(scan_request.scan_type, 1)

    # Dispatch Celery Worker
    run_neomnix_scan.delay(job_id, scan_request.target, intensity)

    log_audit(db, current_user.email, "scan_initiated", resource_id=job_id,
              details={"target": scan_request.target, "scan_type": scan_request.scan_type})

    return ScanResponse(job_id=job_id, status="pending", target=scan_request.target)

@app.get("/scans", response_model=List[ReportResponse])
async def list_scans(skip: int = 0, limit: int = 20, db: Session = Depends(get_db), current_user: User = Depends(require_role("viewer"))):
    """List recent scans with pagination."""
    jobs = db.query(ScanJob).order_by(ScanJob.id.desc()).offset(skip).limit(limit).all()
    
    results = []
    for job in jobs:
        verdict = None
        if job.compliance_report:
            verdict = job.compliance_report.get("determination")
        
        # Calculate score if findings exist
        score = None
        if job.findings:
            score = _compute_compliance_score(job)

        results.append({
            "job_id": job.id,
            "status": job.status,
            "target": job.target,
            "findings_count": len(job.findings) if job.findings else 0,
            "compliance_verdict": verdict,
            "details": job.compliance_report, # simplified
            "compliance_score": score
        })
    return results

@app.get("/scan/{job_id}", response_model=ReportResponse)
def get_scan_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get scan status and results with real compliance score."""
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan Job not found")

    verdict = None
    compliance_score = None

    if job.compliance_report:
        verdict = job.compliance_report.get("determination")
        # --- FIX 3: Real compliance score computation ---
        compliance_score = _compute_compliance_score(job)

    return ReportResponse(
        job_id=job.id,
        status=job.status,
        target=job.target,
        findings_count=len(job.findings) if job.findings else 0,
        compliance_verdict=verdict,
        compliance_score=compliance_score,
        details=job.compliance_report
    )


# ╔══════════════════════════════════════════╗
# ║     COMPLIANCE SCORE COMPUTATION         ║
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
    total_scans = db.query(func.count(ScanJob.id)).scalar() or 0
    completed_scans = db.query(func.count(ScanJob.id)).filter(ScanJob.status == "completed").scalar() or 0
    failed_scans = db.query(func.count(ScanJob.id)).filter(ScanJob.status == "failed").scalar() or 0

    # Get recent completed jobs for score calculation (limit to last 10)
    recent_completed = db.query(ScanJob).filter(
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
    recent_jobs = db.query(ScanJob).order_by(ScanJob.created_at.desc()).limit(5).all()
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
    current_user: User = Depends(get_current_user)
):
    """Serves the generated PDF report for a specific job and framework."""
    filename = f"{framework}_{job_id}.pdf"
    file_path = os.path.join("reports", "pdf", filename)

    if not os.path.exists(file_path):
        # Fallback: broader search if exact match fails
        pdf_dir = os.path.join("reports", "pdf")
        if os.path.isdir(pdf_dir):
            matched_file = next(
                (f for f in os.listdir(pdf_dir) 
                 if job_id in f and framework in f and f.endswith(".pdf")),
                None
            )
            if matched_file:
                file_path = os.path.join(pdf_dir, matched_file)
            else:
                raise HTTPException(status_code=404, detail="Executive Report not found. Ensure the scan has completed.")
        else:
            raise HTTPException(status_code=404, detail="Reports directory does not exist yet.")

    log_audit(db, current_user.email, "report_downloaded", resource_id=job_id,
              details={"framework": framework})

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )


# ╔══════════════════════════════════════════╗
# ║    SHARKTAP PCAP ANALYSIS ENDPOINT       ║
# ╚══════════════════════════════════════════╝

@app.post("/scan/pcap")
async def analyze_pcap_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "analyst"))
):
    """
    Upload a PCAP file captured by SharkTap for compliance analysis.
    Returns threat findings mapped to HIPAA/SOC2/NIST/CCM/SEC controls
    and generates a PDF report.
    """
    # Validate file type
    if not file.filename.endswith((".pcap", ".pcapng", ".cap")):
        raise HTTPException(
            status_code=422,
            detail="File must be a PCAP file (.pcap, .pcapng, or .cap)"
        )

    # Save upload to temp file
    suffix = os.path.splitext(file.filename)[1]
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="sharktap_") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        file_size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
        if file_size_mb > 500:
            raise HTTPException(status_code=413, detail="PCAP file too large (max 500 MB)")

        # Create scan job
        job_id = str(uuid.uuid4())
        new_job = ScanJob(
            id=job_id,
            target=f"pcap://{file.filename}",
            status="running",
            initiated_by=current_user.email
        )
        db.add(new_job)
        db.commit()

        log_audit(db, current_user.email, "scan_initiated", resource_id=job_id,
                  details={"source": "sharktap", "filename": file.filename,
                           "size_mb": round(file_size_mb, 2)})

        # Run SharkTap analysis
        skill = SharkTapSkill()
        results = skill.analyze_pcap(tmp_path)

        artifacts = results.get("artifacts", [])
        threats   = results.get("threats", [])

        # Feed artifacts through ComplianceAgent for cross-mapping + PDF
        from src.agents.compliance import ComplianceAgent
        from src.models.contracts import ScanContext, NeomnixState

        compliance_agent = ComplianceAgent()
        confidence = 0.95 if any(t.get("severity") == "HIGH" for t in threats) else 0.7

        verdict = compliance_agent.evaluate(artifacts, confidence, job_id=job_id)

        # Persist results
        new_job.status             = "completed"
        new_job.findings           = [a.model_dump() for a in artifacts]
        new_job.compliance_report  = verdict.model_dump()
        db.commit()

        return {
            "job_id":            job_id,
            "status":            "completed",
            "source":            "sharktap_pcap",
            "filename":          file.filename,
            "threats_detected":  len(threats),
            "artifacts_count":   len(artifacts),
            "compliance_verdict": verdict.determination,
            "mapped_controls":   verdict.mapped_controls,
            "unmapped_findings": verdict.unmapped_findings,
            "analysis_summary": {
                "total_packets":  results["summary"].get("total_packets"),
                "dns_queries":    len(results["dns_queries"]),
                "http_hosts":     len(results["http_hosts"]),
                "top_threats":    [
                    {"type": t["type"], "severity": t["severity"]}
                    for t in threats
                ],
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        if 'new_job' in dir() and new_job.id:
            new_job.status   = "failed"
            new_job.findings = [{"error": str(e)}]
            db.commit()
        raise HTTPException(status_code=500, detail=f"PCAP analysis failed: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ╔══════════════════════════════════════════╗
# ║           HEALTH & AUDIT                 ║
# ╚══════════════════════════════════════════╝

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}

@app.get("/audit/logs")
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Admin-only: view audit trail."""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [{
        "user": log.user_email,
        "action": log.action,
        "resource": log.resource_id,
        "details": log.details,
        "time": log.timestamp.isoformat() if log.timestamp else None,
        "ip": log.ip_address
    } for log in logs]
