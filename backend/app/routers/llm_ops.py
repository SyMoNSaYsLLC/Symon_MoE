from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..jobs import JOB_MANAGER

router = APIRouter(prefix="/api/llm", tags=["llm_ops"])


class LlmCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: str = "llama3"


class LlmUpdateRequest(BaseModel):
    artifact_id: str = Field(..., min_length=1)
    diff: str = Field(..., min_length=1)
    model: str = "llama3"


@router.post("/create")
def llm_create(request: LlmCreateRequest) -> dict:
    job = JOB_MANAGER.submit_llm_job(
        operation="create",
        prompt=request.prompt,
        model=request.model,
        context={},
    )
    return {"job_id": job["id"], "status": job["status"]}


@router.post("/update")
def llm_update(request: LlmUpdateRequest) -> dict:
    prompt = (
        f"Update artifact '{request.artifact_id}' with the following diff intent:\n"
        f"{request.diff}\n"
        "Return only the updated artifact content."
    )
    job = JOB_MANAGER.submit_llm_job(
        operation="update",
        prompt=prompt,
        model=request.model,
        context={"artifact_id": request.artifact_id, "diff": request.diff},
    )
    return {"job_id": job["id"], "status": job["status"]}


@router.get("/queue")
def llm_queue_status() -> dict:
    workers = JOB_MANAGER.workers_status()
    llm = workers.get("llm:ollama", {})
    return {
        "queue_depth": llm.get("queued", 0),
        "worker": llm,
    }
