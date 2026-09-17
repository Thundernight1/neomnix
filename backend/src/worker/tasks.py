import os
from celery import Celery
import asyncio
from src.orchestrator import NeomnixOrchestrator
from src.db.models import SessionLocal, ScanJob, init_db
from datetime import datetime
import json
from typing import Any, Dict, List, Optional

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "neomnix_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)
celery_app.conf.update(
    imports=("src.api.gap",),
    task_serializer="json", result_serializer="json", accept_content=["json"],
    task_soft_time_limit=1800, task_time_limit=1860,
    result_expires=3600, broker_connection_retry_on_startup=True,
)


# Initialize Orchestrator Singleton
orchestrator = NeomnixOrchestrator()

def serialize_artifacts(artifacts) -> List[Dict[str, Any]]:
    return [a.model_dump(mode="json") for a in artifacts]

def serialize_verdict(verdict) -> Dict[str, Any]:
    return verdict.model_dump(mode="json")


@celery_app.task
def run_pcap_scan(job_id: str, path: str):
    from pathlib import Path
    from src.skills.sharktap_skill import SharkTapSkill
    from src.agents.compliance import ComplianceAgent
    from src.services.alerts import publish_critical_alert
    import logging
    db = SessionLocal()
    try:
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if not job:
            raise ValueError("Unknown capture job")
        expected = (Path("reports") / "uploads" / job.tenant_id / f"{job.id}.pcap").resolve()
        if Path(path).resolve() != expected:
            raise ValueError("Capture path outside job scope")
        validated_path = expected
        job.status = "running"
        db.commit()
        result = SharkTapSkill().analyze_pcap(path)
        if result.get("error"):
            raise RuntimeError("Capture analysis failed")
        artifacts = result["artifacts"]
        verdict = ComplianceAgent().evaluate(artifacts, 1.0, job_id=job.id)
        job.findings = serialize_artifacts(artifacts)
        job.compliance_report = serialize_verdict(verdict)
        job.status = "completed"
        db.commit()
        if any(artifact.severity == "critical" for artifact in artifacts):
            try:
                publish_critical_alert(job.tenant_id, job.id)
            except Exception:
                logging.getLogger(__name__).exception("Alert publish failed for job %s", job.id)
    except Exception:
        db.rollback()
        if "job" in locals() and job:
            job.status = "failed"
            db.commit()
        raise
    finally:
        db.close()
        if "validated_path" in locals():
            validated_path.unlink(missing_ok=True)

@celery_app.task(bind=True)
def run_neomnix_scan(self, job_id: str, target: str, intensity: int = 1):
    """
    Celery Task to run the Neomnix Orchestrator asynchronously.
    Updates the database with progress and results.
    """
    print(f"--- [Worker] Starting Scan Job {job_id} for target {target} ---")
    
    # DB Session
    db = SessionLocal()
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if not job:
        print(f"!!! [Worker] Job {job_id} not found in DB !!!")
        db.close()
        return
    
    job.status = "running"
    db.commit()
    
    loop = None
    try:
        # Run the Orchestrator (Async call from Sync Task)
        # We need a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # We need to capture the result from the orchestrator.
        # Currently orchestrator.run() prints to stdout. 
        # We should modify orchestrator to return the state.
        # For now, let's wrap the logic here or refactor orchestrator slightly.
        # To avoid massive refactor right now, let's import the graph and run it directly here
        # similar to how orchestrator.run() does it.
        
        from src.models.contracts import ScanContext, NeomnixState
        
        initial_state = NeomnixState(
            artifacts=[],
            context=ScanContext(intensity=intensity, target=target, job_id=job_id),
            verdict=None,
            confidence=0.0,
            loop_triggered=False
        )
        
        final_state = loop.run_until_complete(orchestrator.app.ainvoke(initial_state))
        
        # Update Job with Results
        job.status = "completed"
        job.confidence_score = final_state['confidence']
        
        # Serialize Artifacts
        job.findings = serialize_artifacts(final_state['artifacts'])
        
        if final_state['verdict']:
            job.compliance_report = serialize_verdict(final_state['verdict'])
            
        db.commit()
        print(f"--- [Worker] Job {job_id} Completed Successfully ---")
        
    except Exception as e:
        print(f"!!! [Worker] Job {job_id} Failed: {e} !!!")
        db.rollback()
        job.status = "failed"
        # Store error in findings or a separate field if we had one
        job.findings = []
        db.commit()
        raise
    finally:
        if loop is not None:
            loop.close()
            asyncio.set_event_loop(None)
        db.close()
