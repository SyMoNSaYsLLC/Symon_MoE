from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..jobs import JOB_MANAGER

router = APIRouter(prefix="/api/db", tags=["database"])


@router.get("/jobs")
def list_db_jobs() -> dict:
    return {"jobs": JOB_MANAGER.list_jobs()}


@router.get("/logs/{job_id}")
def list_db_job_logs(job_id: str) -> dict:
    try:
        logs = JOB_MANAGER.get_job_logs(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found") from exc
    return {"job_id": job_id, "logs": logs}


@router.get("/events")
def list_worker_events(limit: int = 200) -> dict:
    return {"events": JOB_MANAGER.db.list_worker_events(limit=limit)}
