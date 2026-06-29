from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/image", tags=["image_gen"])

# ---- Configuration -------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]
SD_CPP_BIN = Path(
    os.environ.get(
        "SD_CPP_BIN",
        str(REPO_ROOT / "converters" / "diffusers_cpp" / "build" / "bin" / "sd"),
    )
)
OUTPUT_DIR = REPO_ROOT / "frontend" / "models" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory job store for image generation jobs
_JOBS: dict[str, dict] = {}


# ---- Schemas -------------------------------------------------------------

class ImageRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    model: str           # GGUF model filename (relative to frontend/models/converted)
    width: int = 512
    height: int = 512
    steps: int = 20
    cfg_scale: float = 7.0
    seed: int = -1


# ---- Background task -----------------------------------------------------

def _run_sd_job(job_id: str, params: dict) -> None:
    _JOBS[job_id]["status"] = "running"
    out_path = OUTPUT_DIR / f"{job_id}.png"

    converted_dir = REPO_ROOT / "frontend" / "models" / "converted"
    model_path = converted_dir / params["model"]
    if not model_path.exists():
        _JOBS[job_id]["status"] = "failed"
        _JOBS[job_id]["error"] = f"Model file not found: {params['model']}"
        return

    cmd = [
        str(SD_CPP_BIN),
        "--model", str(model_path),
        "--prompt", params["prompt"],
        "--output", str(out_path),
        "--width", str(params["width"]),
        "--height", str(params["height"]),
        "--steps", str(params["steps"]),
        "--cfg-scale", str(params["cfg_scale"]),
        "--seed", str(params["seed"]),
    ]
    if params.get("negative_prompt"):
        cmd += ["--negative-prompt", params["negative_prompt"]]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            _JOBS[job_id]["status"] = "failed"
            _JOBS[job_id]["error"] = result.stderr[-2000:]
        else:
            _JOBS[job_id]["status"] = "done"
            _JOBS[job_id]["output"] = f"images/{job_id}.png"
    except subprocess.TimeoutExpired:
        _JOBS[job_id]["status"] = "failed"
        _JOBS[job_id]["error"] = "Generation timed out"
    except Exception as exc:  # pragma: no cover
        _JOBS[job_id]["status"] = "failed"
        _JOBS[job_id]["error"] = str(exc)


# ---- Endpoints -----------------------------------------------------------

@router.post("")
async def submit_image_job(request: ImageRequest, bg: BackgroundTasks) -> dict:
    """Queue a text-to-image job via stable-diffusion.cpp."""
    if not SD_CPP_BIN.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "stable-diffusion.cpp binary not found. "
                f"Build it: cd converters/diffusers_cpp && cmake -B build && cmake --build build"
            ),
        )
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {"id": job_id, "status": "queued", "output": None, "error": None}
    bg.add_task(_run_sd_job, job_id, request.model_dump())
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs")
async def list_image_jobs() -> dict:
    """List all image generation jobs."""
    return {"jobs": list(_JOBS.values())}


@router.get("/jobs/{job_id}")
async def get_image_job(job_id: str) -> dict:
    """Get the status/result of a specific image generation job."""
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _JOBS[job_id]


@router.get("/models")
async def list_diffusion_models() -> dict:
    """List GGUF diffusion model files available for image generation."""
    converted_dir = REPO_ROOT / "frontend" / "models" / "converted"
    if not converted_dir.exists():
        return {"models": []}
    models = [
        {"name": f.name, "size_bytes": f.stat().st_size}
        for f in sorted(converted_dir.iterdir())
        if f.is_file() and f.suffix == ".gguf"
    ]
    return {"models": models}
