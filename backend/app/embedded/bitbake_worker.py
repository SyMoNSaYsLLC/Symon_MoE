from __future__ import annotations

import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from ..jobs import JOB_MANAGER


class BitbakeWorker:
    STAGES = ["init", "fetch", "compile", "rootfs", "image"]

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def queue_build(self, machine: str, recipe: str) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "machine": machine,
                "recipe": recipe,
                "status": "queued",
                "stage": "init",
                "logs": [f"Queued build for {machine}:{recipe}"],
                "created_at": datetime.now(UTC).isoformat(),
            }
        t = threading.Thread(target=self._run, args=(job_id,), daemon=True)
        t.start()
        return job_id

    def _run(self, job_id: str) -> None:
        with self._lock:
            self._jobs[job_id]["status"] = "running"
        for stage in self.STAGES:
            with self._lock:
                self._jobs[job_id]["stage"] = stage
                self._jobs[job_id]["logs"].append(f"Stage {stage} started")
            JOB_MANAGER.db.add_embed_build(job_id, stage, "running", {"job_id": job_id})
            time.sleep(1)
        with self._lock:
            self._jobs[job_id]["status"] = "completed"
            self._jobs[job_id]["logs"].append("Build completed")
        JOB_MANAGER.db.add_embed_build(job_id, "image", "completed", {"job_id": job_id})

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._jobs.get(job_id)
            return dict(item) if item else None

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(v) for v in self._jobs.values()]
