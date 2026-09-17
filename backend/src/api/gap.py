"""
Gap Analysis API — mevcut Neomnix auth + DB pattern kullanır.
POST /api/gap/analyze     → Celery task başlatır
GET  /api/gap/results/{id} → Sonuç döner
GET  /api/gap/report/{org} → Tam rapor
"""
from __future__ import annotations
from typing import List, Optional
from typing import Literal
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session


from src.api.auth import get_current_user, require_role, get_db
from src.services.gap_analyzer import analyze_gaps
from src.worker.tasks import celery_app

router = APIRouter(prefix="/gap", tags=["gap-analysis"])


class AnalyzeRequest(BaseModel):
    org_id: str
    completed_ucl_ids: List[str] = []
    target_frameworks: Optional[List[Literal["hipaa", "mhmda"]]] = None
    include_ai_recommendations: bool = False


class AnalyzeResponse(BaseModel):
    task_id: str
    status: str = "queued"


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
def trigger_gap_analysis(
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "analyst"))
):
    """Gap analizini Celery worker üzerinde başlat."""
    if req.org_id != current_user.tenant_id:
        raise HTTPException(403, "Organization access denied")
    task_id = str(__import__("uuid").uuid4())
    from src.api.auth import log_audit
    log_audit(db, current_user.tenant_id, current_user.email, "gap_requested", task_id)
    try:
        task = run_gap_analysis_task.apply_async(kwargs=dict(
            org_id=req.org_id,
            completed_ucl_ids=req.completed_ucl_ids,
            target_frameworks=req.target_frameworks,
            include_ai=req.include_ai_recommendations,
        ), task_id=task_id)
    except Exception:
        logging.getLogger(__name__).exception("Gap dispatch failed: %s", task_id)
        raise HTTPException(503, "Analysis worker unavailable")
    return AnalyzeResponse(task_id=task.id)


@router.get("/results/{task_id}")
def get_gap_results(task_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Celery task sonucunu döner."""
    from src.db.models import AuditLog
    if not db.query(AuditLog).filter(
        AuditLog.resource_id == task_id,
        AuditLog.tenant_id == current_user.tenant_id,
        AuditLog.action == "gap_requested",
    ).first():
        raise HTTPException(404, "Task not found")
    from celery.result import AsyncResult
    result = AsyncResult(task_id, app=celery_app)
    if result.state == "PENDING":
        return {"status": "pending", "task_id": task_id}
    if result.state == "FAILURE":
        return {"status": "failed", "task_id": task_id, "error": "Analysis failed; contact support"}
    if result.state == "SUCCESS":
        return {"status": "success", "task_id": task_id, "data": result.result}
    return {"status": result.state.lower(), "task_id": task_id}


@router.get("/report/{org_id}")
def get_gap_report(
    org_id: str,
    frameworks: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Tam gap raporu — PDF export için."""
    if org_id != current_user.tenant_id:
        raise HTTPException(403, "Organization access denied")
    target_fw = frameworks.split(",") if frameworks else None
    if target_fw and not set(target_fw).issubset({"hipaa", "mhmda"}):
        raise HTTPException(422, "Unsupported framework")
    report = analyze_gaps(db, completed_ucl_ids=[], target_frameworks=target_fw)
    return report.to_dict()


# ─── Celery Task ────────────────────────────────────────────────────────────

@celery_app.task(name="gap.run_gap_analysis")
def run_gap_analysis_task(org_id, completed_ucl_ids, target_frameworks, include_ai):
    import os
    try:
        import redis
        r_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    except Exception:
        r_client = None

    from src.db.models import SessionLocal
    from src.services.remediation_ai import get_recommendation
    db = SessionLocal()
    try:
        report = analyze_gaps(db, completed_ucl_ids, target_frameworks)
        if include_ai:
            for gap in report.gaps:
                gap.recommendation = get_recommendation(
                    ucl_id=gap.ucl_id,
                    title=gap.title,
                    description=gap.description,
                    frameworks=gap.affected_frameworks,
                    citations=gap.citations,
                    redis_client=r_client,
                )
        return report.to_dict()
    finally:
        db.close()
