"""Tenant-scoped scan submission, results and audit API."""
import ipaddress
import logging
import os
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.api.auth import get_current_user, get_db, require_role, log_audit
from src.db.models import ScanJob, AuditLog
from src.worker.tasks import run_neomnix_scan
from src.worker.tasks import run_pcap_scan
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/scans/pcap", status_code=202)
def upload_pcap(file: UploadFile, db: Session = Depends(get_db),
                user=Depends(require_role("admin", "analyst"))):
    job_id = str(uuid.uuid4())
    directory = Path("reports") / "uploads" / str(user.tenant_id)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / f"{job_id}.pcap"
    total = 0
    try:
        with path.open("xb") as output:
            os.chmod(path, 0o600)
            while chunk := file.file.read(1024 * 1024):
                if total == 0 and chunk[:4] not in {
                    b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4",
                    b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d", b"\x0a\x0d\x0d\x0a",
                }:
                    raise HTTPException(422, "A valid PCAP or PCAPNG file is required")
                total += len(chunk)
                if total > 50 * 1024 * 1024:
                    raise HTTPException(413, "Capture exceeds 50 MiB")
                output.write(chunk)
        if total < 24:
            raise HTTPException(422, "Capture is empty or truncated")
        job = ScanJob(id=job_id, tenant_id=user.tenant_id, target="Uploaded capture",
                      status="pending", initiated_by=user.email)
        db.add(job)
        db.commit()
        try:
            run_pcap_scan.delay(job_id, str(path.resolve()))
        except Exception:
            logger.exception("PCAP dispatch failed: %s", job_id)
            job.status = "failed"
            db.commit()
            raise HTTPException(503, "Capture worker unavailable")
        log_audit(db, user.tenant_id, user.email, "scan_initiated", job_id)
        return {"job_id": job_id, "status": "pending"}
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()


class ScanRequest(BaseModel):
    target: str
    scan_type: Literal["quick", "full", "compliance"] = "quick"


def validate_target(target: str) -> str:
    """Only literal IPs in operator-approved networks; no DNS/URL SSRF."""
    try:
        address = ipaddress.ip_address(target)
    except ValueError:
        raise HTTPException(422, "Provide a single authorized IP address")
    allowed = [value.strip() for value in os.getenv("SCAN_ALLOWED_CIDRS", "").split(",") if value.strip()]
    if not allowed or not any(address in ipaddress.ip_network(value) for value in allowed):
        raise HTTPException(403, "Target is outside SCAN_ALLOWED_CIDRS")
    if address.is_unspecified or address.is_multicast or address.is_link_local:
        raise HTTPException(403, "Reserved target is not permitted")
    return str(address)


@router.post("/scan", status_code=202)
def start_scan(payload: ScanRequest, db: Session = Depends(get_db),
               user=Depends(require_role("admin", "analyst"))):
    target = validate_target(payload.target)
    job = ScanJob(id=str(uuid.uuid4()), tenant_id=user.tenant_id, target=target,
                  status="pending", initiated_by=user.email)
    db.add(job)
    db.commit()
    try:
        run_neomnix_scan.delay(job.id, target, 1 if payload.scan_type == "quick" else 5)
    except Exception:
        logger.exception("Scan dispatch failed for %s", job.id)
        job.status = "failed"
        db.commit()
        raise HTTPException(503, "Scan worker unavailable; try again later")
    log_audit(db, user.tenant_id, user.email, "scan_initiated", job.id)
    return {"job_id": job.id, "status": "pending", "target": target}


@router.get("/scans")
def list_scans(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
               db: Session = Depends(get_db), user=Depends(get_current_user)):
    jobs = db.query(ScanJob).filter(ScanJob.tenant_id == user.tenant_id).order_by(
        ScanJob.created_at.desc(), ScanJob.id).offset(offset).limit(limit).all()
    return [{"id": job.id, "status": job.status, "target": job.target,
             "findings": job.findings or [], "created_at": job.created_at,
             "frameworks": ["HIPAA-2026", "WA-MHMDA"]} for job in jobs]


@router.get("/scan/{job_id}")
def scan_details(job_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    job = db.query(ScanJob).filter(ScanJob.id == job_id, ScanJob.tenant_id == user.tenant_id).first()
    if job is None:
        raise HTTPException(404, "Scan not found")
    from src.api.main import _compute_compliance_score
    report = job.compliance_report or {}
    return {"job_id": job.id, "status": job.status, "target": job.target,
            "findings_count": len(job.findings or []),
            "compliance_verdict": report.get("determination"),
            "compliance_score": _compute_compliance_score(job) if job.status == "completed" else None,
            "details": {**report, "findings": job.findings or []}}


@router.get("/audit/logs")
def audit_logs(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
               db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    rows = db.query(AuditLog).filter(AuditLog.tenant_id == user.tenant_id).order_by(
        AuditLog.timestamp.desc(), AuditLog.id.desc()).offset(offset).limit(limit).all()
    return [{"user": row.user_email, "action": row.action, "resource": row.resource_id,
             "details": row.details, "time": row.timestamp, "ip": row.ip_address} for row in rows]
