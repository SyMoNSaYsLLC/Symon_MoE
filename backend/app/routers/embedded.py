from __future__ import annotations

from pathlib import Path
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..config import EMBEDDED_BUILD_ROOT
from ..embedded.bitbake_worker import BitbakeWorker
from ..embedded.firmware_packager import build_manifest
from ..embedded.layer_manager import LayerManager

router = APIRouter(prefix="/api/embedded", tags=["embedded"])

BITBAKE_WORKER = BitbakeWorker()
LAYER_MANAGER = LayerManager()
ARTIFACT_DIR = EMBEDDED_BUILD_ROOT / "deploy" / "images"
SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class BuildRequest(BaseModel):
    machine: str = Field(..., min_length=1)
    recipe: str = Field(..., min_length=1)


class AddLayerRequest(BaseModel):
    layer_url: str = Field(..., min_length=1)


@router.post("/build")
def queue_build(request: BuildRequest) -> dict:
    job_id = BITBAKE_WORKER.queue_build(request.machine, request.recipe)
    return {"job_id": job_id, "status": "queued"}


@router.get("/build/{job_id}")
def build_status(job_id: str) -> dict:
    item = BITBAKE_WORKER.get(job_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Build job not found")
    return item


@router.get("/layers")
def list_layers() -> dict:
    return {"layers": LAYER_MANAGER.list()}


@router.post("/layers")
def add_layer(request: AddLayerRequest) -> dict:
    return LAYER_MANAGER.add(request.layer_url)


@router.get("/artifacts")
def list_artifacts() -> dict:
    return {"artifacts": build_manifest(ARTIFACT_DIR)}


@router.get("/artifacts/{name}")
def download_artifact(name: str):
    if not SAFE_NAME_PATTERN.fullmatch(name) or name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid artifact name")

    artifact_path = None
    for entry in ARTIFACT_DIR.iterdir() if ARTIFACT_DIR.exists() else []:
        if entry.is_file() and entry.name == name:
            artifact_path = entry.resolve()
            break
    if artifact_path is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path=str(artifact_path), filename=name)
