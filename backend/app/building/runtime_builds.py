"""Runtime build job management for the building layer."""
from __future__ import annotations

import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_JOBS: dict[str, dict[str, Any]] = {}

SUPPORTED_RUNTIMES = ("gguf", "onnx", "transformers", "diffusers", "peft", "custom")


class RuntimeBuildManager:
    """Queue and track runtime model build jobs."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = repo_root or Path(__file__).resolve().parents[4]

    def submit(
        self,
        runtime: str,
        model_name: str,
        source_path: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if runtime not in SUPPORTED_RUNTIMES:
            raise ValueError(f"runtime must be one of {sorted(SUPPORTED_RUNTIMES)}")
        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        job: dict[str, Any] = {
            "id": job_id,
            "runtime": runtime,
            "model_name": model_name,
            "source_path": source_path,
            "options": options or {},
            "status": "queued",
            "logs": [],
            "artifacts": [],
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        _JOBS[job_id] = job
        return job

    def run_conversion_script(self, job_id: str, script_path: str, args: list[str]) -> dict[str, Any] | None:
        job = _JOBS.get(job_id)
        if job is None:
            return None
        job["status"] = "running"
        job["updated_at"] = datetime.now(UTC).isoformat()
        try:
            cmd = ["python", script_path] + args
            proc = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(self._root),
            )
            job["logs"].append(proc.stdout)
            if proc.returncode == 0:
                job["status"] = "completed"
            else:
                job["status"] = "failed"
                job["error"] = proc.stderr
        except Exception as exc:  # pragma: no cover
            job["status"] = "error"
            job["error"] = str(exc)
        job["updated_at"] = datetime.now(UTC).isoformat()
        return job

    def get(self, job_id: str) -> dict[str, Any] | None:
        return _JOBS.get(job_id)

    def list(self, runtime: str | None = None) -> list[dict[str, Any]]:
        jobs = list(_JOBS.values())
        if runtime is not None:
            jobs = [j for j in jobs if j["runtime"] == runtime]
        return jobs
