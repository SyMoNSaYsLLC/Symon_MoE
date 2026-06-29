from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/video", tags=["video_gen"])

REPO_ROOT = Path(__file__).resolve().parents[4]
OUTPUT_DIR = REPO_ROOT / "frontend" / "models" / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory job store
_JOBS: dict[str, dict] = {}


class VideoRequest(BaseModel):
    prompt: str
    frame_count: int = 16
    fps: int = 8
    width: int = 512
    height: int = 320


def _run_video_job(job_id: str, params: dict) -> None:
    """
    Placeholder video generation runner.

    Routes to orchestration/video_pipeline.py which wraps CogVideoX or
    ModelScope text-to-video inference.
    """
    _JOBS[job_id]["status"] = "running"
    out_path = OUTPUT_DIR / f"{job_id}.mp4"
    pipeline_script = REPO_ROOT / "orchestration" / "video_pipeline.py"

    if not pipeline_script.exists():
        _JOBS[job_id]["status"] = "failed"
        _JOBS[job_id]["error"] = "orchestration/video_pipeline.py not found"
        return

    import sys
    cmd = [
        sys.executable,
        str(pipeline_script),
        "--prompt", params["prompt"],
        "--output", str(out_path),
        "--frames", str(params["frame_count"]),
        "--fps", str(params["fps"]),
        "--width", str(params["width"]),
        "--height", str(params["height"]),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            _JOBS[job_id]["status"] = "failed"
            _JOBS[job_id]["error"] = result.stderr[-2000:]
        else:
            _JOBS[job_id]["status"] = "done"
            _JOBS[job_id]["output"] = f"videos/{job_id}.mp4"
    except subprocess.TimeoutExpired:
        _JOBS[job_id]["status"] = "failed"
        _JOBS[job_id]["error"] = "Video generation timed out"
    except Exception as exc:  # pragma: no cover
        _JOBS[job_id]["status"] = "failed"
        _JOBS[job_id]["error"] = str(exc)


@router.post("")
async def submit_video_job(request: VideoRequest, bg: BackgroundTasks) -> dict:
    """Queue a text-to-video job (routes to orchestration/video_pipeline.py)."""
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {"id": job_id, "status": "queued", "output": None, "error": None}
    bg.add_task(_run_video_job, job_id, request.model_dump())
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs")
async def list_video_jobs() -> dict:
    """List all video generation jobs."""
    return {"jobs": list(_JOBS.values())}


@router.get("/jobs/{job_id}")
async def get_video_job(job_id: str) -> dict:
    """Get the status/result of a specific video generation job."""
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _JOBS[job_id]
