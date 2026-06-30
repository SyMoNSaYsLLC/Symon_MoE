from __future__ import annotations

from pathlib import Path
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import (
    ALLOWED_ORIGINS,
    CONVERTED_MODELS_DIR,
    MIGRATED_MODELS_DIR,
    MODELS_ROOT,
    SCOPE_DECISIONS,
    SUPPORTED_MIGRATION_COMBINATIONS,
)
from .jobs import JOB_MANAGER
from .routers import (
    building,
    calculator,
    chat,
    code_assist,
    database,
    embedded,
    image_gen,
    iptv,
    llm_ops,
    model_runtime,
    mining,
    planning,
    tensor_lab,
    terminal,
    video_gen,
)
from .schemas import ConversionJobRequest, MigrationJobRequest
from .storage import ensure_storage_contract, scan_models

app = FastAPI(title="Symoneural Backend API", version="0.2.0")
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for _router in (
    chat.router,
    code_assist.router,
    image_gen.router,
    video_gen.router,
    calculator.router,
    iptv.router,
    tensor_lab.router,
    llm_ops.router,
    database.router,
    mining.router,
    embedded.router,
    model_runtime.router,
    terminal.router,
    planning.router,
    building.router,
):
    app.include_router(_router)


@app.on_event("startup")
def startup() -> None:
    ensure_storage_contract()


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "symoneural-backend",
        "models_root": str(MODELS_ROOT),
        "scope_decisions": SCOPE_DECISIONS,
    }


@app.get("/api/models/discover")
def discover_models() -> dict:
    return scan_models()


@app.post("/api/jobs/conversion")
def create_conversion_job(request: ConversionJobRequest) -> dict:
    try:
        return JOB_MANAGER.submit_conversion(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/jobs/migration")
def create_migration_job(request: MigrationJobRequest) -> dict:
    try:
        return JOB_MANAGER.submit_migration(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/jobs")
def list_jobs() -> dict:
    return {"jobs": JOB_MANAGER.list_jobs()}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    try:
        return JOB_MANAGER.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found") from exc


@app.get("/api/jobs/{job_id}/logs")
def get_job_logs(job_id: str) -> dict:
    try:
        logs = JOB_MANAGER.get_job_logs(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found") from exc
    return {"job_id": job_id, "logs": logs}


@app.get("/api/workers/status")
def workers_status() -> dict:
    return {"workers": JOB_MANAGER.workers_status()}


@app.get("/api/migration/supported")
def supported_migrations() -> dict:
    combos = [
        {
            "sources": list(combo),
            "target": "single GGUF",
            "description": "3 architectures to 1 GGUF (v1)",
        }
        for combo in SUPPORTED_MIGRATION_COMBINATIONS
    ]
    return {"supported": combos}


@app.get("/api/artifacts/{artifact_type}/{filename}")
def download_artifact(artifact_type: str, filename: str):
    if artifact_type == "converted":
        base_dir = CONVERTED_MODELS_DIR
    elif artifact_type == "migrated":
        base_dir = MIGRATED_MODELS_DIR
    else:
        raise HTTPException(status_code=400, detail="artifact_type must be converted or migrated")

    if not SAFE_NAME_PATTERN.fullmatch(filename) or filename in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid artifact filename")

    artifact_path = None
    for entry in base_dir.iterdir():
        if entry.is_file() and entry.name == filename:
            artifact_path = entry.resolve()
            break
    if artifact_path is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return FileResponse(path=str(artifact_path), filename=filename)


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
