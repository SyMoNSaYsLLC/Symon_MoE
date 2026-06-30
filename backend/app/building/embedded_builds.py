"""Embedded image build job management for the building layer."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

_JOBS: dict[str, dict[str, Any]] = {}

SUPPORTED_MACHINES = ("raspberrypi4", "raspberrypi5", "jetson-nano", "beaglebone", "custom")
SUPPORTED_DISTROS = ("poky", "openembedded", "custom")


class EmbeddedBuildManager:
    """Queue and track embedded image build jobs (separate from runtime execution)."""

    def submit(
        self,
        machine: str,
        recipe: str,
        distro: str = "poky",
        layers: list[str] | None = None,
        extra_vars: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        job: dict[str, Any] = {
            "id": job_id,
            "machine": machine,
            "recipe": recipe,
            "distro": distro,
            "layers": layers or [],
            "extra_vars": extra_vars or {},
            "status": "queued",
            "logs": [],
            "artifacts": [],
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        _JOBS[job_id] = job
        return job

    def update_status(
        self, job_id: str, status: str, log_line: str | None = None
    ) -> dict[str, Any] | None:
        job = _JOBS.get(job_id)
        if job is None:
            return None
        job["status"] = status
        if log_line:
            job["logs"].append(log_line)
        job["updated_at"] = datetime.now(UTC).isoformat()
        return job

    def add_artifact(self, job_id: str, artifact_path: str) -> dict[str, Any] | None:
        job = _JOBS.get(job_id)
        if job is None:
            return None
        job["artifacts"].append(artifact_path)
        job["updated_at"] = datetime.now(UTC).isoformat()
        return job

    def get(self, job_id: str) -> dict[str, Any] | None:
        return _JOBS.get(job_id)

    def list(self, machine: str | None = None) -> list[dict[str, Any]]:
        jobs = list(_JOBS.values())
        if machine is not None:
            jobs = [j for j in jobs if j["machine"] == machine]
        return jobs
