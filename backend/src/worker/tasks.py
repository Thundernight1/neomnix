import os
from celery import Celery
import asyncio
from src.orchestrator import NeomnixOrchestrator
from src.db.models import SessionLocal, ScanJob, init_db
from datetime import datetime
import json

# Initialize DB on worker start
init_db()

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "neomnix_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)


# Initialize Orchestrator Singleton
orchestrator = NeomnixOrchestrator()

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
        return
    
    job.status = "running"
    db.commit()
    
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
        job.completed_at = datetime.utcnow()
        job.final_intensity = final_state['context'].intensity
        job.confidence_score = final_state['confidence']
        
        # Serialize Artifacts
        job.findings = [a.model_dump() for a in final_state['artifacts']]
        
        if final_state['verdict']:
            job.compliance_report = final_state['verdict'].model_dump()
            
        db.commit()
        print(f"--- [Worker] Job {job_id} Completed Successfully ---")
        
    except Exception as e:
        print(f"!!! [Worker] Job {job_id} Failed: {e} !!!")
        job.status = "failed"
        # Store error in findings or a separate field if we had one
        job.findings = [{"error": str(e)}]
        db.commit()
    finally:
        db.close()
