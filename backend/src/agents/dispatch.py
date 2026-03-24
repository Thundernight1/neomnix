from sqlalchemy.orm import Session
from src.db.models import ScanJob
from src.worker.tasks import run_cybersurx_scan
import uuid

class ScannerDispatcher:
    """
    Dispatcher for technical security scans.
    Wraps Celery task execution to be compatible with AIHub.
    """
    async def execute(self, target: str, context: dict = None) -> dict:
        # DB Session is required to create the job record
        db: Session = context.get('db') if context else None
        
        if not db:
            return {
                "error": "Database session required for scanning", 
                "status": "failed",
                "details": "Internal Error: DB context missing in dispatch"
            }
            
        job_id = str(uuid.uuid4())
        
        try:
            # Create DB record
            db_job = ScanJob(id=job_id, target=target, status="pending")
            db.add(db_job)
            db.commit()
            db.refresh(db_job)
            
            # Trigger async task
            intensity = context.get('intensity', 1) if context else 1
            run_cybersurx_scan.delay(job_id, target, intensity)
            
            return {
                "status": "initiated",
                "job_id": job_id,
                "target": target,
                "message": f"Scan started for {target}"
            }
        except Exception as e:
            db.rollback()
            return {"error": str(e), "status": "failed"}
