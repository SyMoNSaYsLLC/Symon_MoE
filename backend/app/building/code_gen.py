"""Code generation orchestration for the building layer."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

_JOBS: dict[str, dict[str, Any]] = {}

SUPPORTED_TARGETS = ("fastapi_router", "pydantic_schema", "worker_class", "test_module", "custom")


class CodeGenOrchestrator:
    """Orchestrate LLM-backed code generation jobs."""

    def submit(
        self,
        target: str,
        template: str,
        variables: dict[str, str],
        output_path: str | None = None,
    ) -> dict[str, Any]:
        if target not in SUPPORTED_TARGETS:
            raise ValueError(f"target must be one of {sorted(SUPPORTED_TARGETS)}")
        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        job: dict[str, Any] = {
            "id": job_id,
            "target": target,
            "template": template,
            "variables": variables,
            "output_path": output_path,
            "status": "queued",
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        _JOBS[job_id] = job
        return job

    def complete(self, job_id: str, result: str) -> dict[str, Any] | None:
        job = _JOBS.get(job_id)
        if job is None:
            return None
        job["result"] = result
        job["status"] = "completed"
        job["updated_at"] = datetime.now(UTC).isoformat()
        return job

    def fail(self, job_id: str, error: str) -> dict[str, Any] | None:
        job = _JOBS.get(job_id)
        if job is None:
            return None
        job["error"] = error
        job["status"] = "failed"
        job["updated_at"] = datetime.now(UTC).isoformat()
        return job

    def get(self, job_id: str) -> dict[str, Any] | None:
        return _JOBS.get(job_id)

    def list(self) -> list[dict[str, Any]]:
        return list(_JOBS.values())
