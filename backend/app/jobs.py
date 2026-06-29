from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from .config import (
    CONVERTED_MODELS_DIR,
    MIGRATED_MODELS_DIR,
    ORCHESTRATION_CONVERTER,
    RAW_MODELS_DIR,
    SUPPORTED_ARCHITECTURES,
    SUPPORTED_MIGRATION_COMBINATIONS,
)
from .schemas import ConversionJobRequest, MigrationJobRequest
from .storage import ensure_storage_contract, load_metadata, save_metadata


@dataclass
class QueueItem:
    job_id: str


class JobManager:
    def __init__(self) -> None:
        ensure_storage_contract()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

        self._conversion_queues: dict[str, queue.Queue[QueueItem]] = {
            architecture: queue.Queue() for architecture in SUPPORTED_ARCHITECTURES
        }
        self._migration_queue: queue.Queue[QueueItem] = queue.Queue()
        self._workers: dict[str, dict[str, Any]] = {}
        self._start_workers()

    def _start_workers(self) -> None:
        for architecture, q in self._conversion_queues.items():
            self._workers[f"conversion:{architecture}"] = {
                "type": "conversion",
                "architecture": architecture,
                "current_job": None,
                "queue": q,
            }
            t = threading.Thread(
                target=self._conversion_worker_loop,
                args=(architecture, q),
                daemon=True,
            )
            t.start()

        self._workers["migration:v1"] = {
            "type": "migration",
            "architecture": "v1",
            "current_job": None,
            "queue": self._migration_queue,
        }
        t = threading.Thread(target=self._migration_worker_loop, daemon=True)
        t.start()

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def submit_conversion(self, request: ConversionJobRequest) -> dict[str, Any]:
        if request.architecture not in self._conversion_queues:
            raise ValueError(f"Unsupported architecture '{request.architecture}'.")

        model_dir = RAW_MODELS_DIR / request.model_name
        if not model_dir.exists() or not model_dir.is_dir():
            raise ValueError(
                f"Raw model folder '{request.model_name}' was not found under {RAW_MODELS_DIR}."
            )

        if request.architecture == "diffusion":
            source_file = request.source_file
            if source_file is None:
                matches = list(model_dir.glob("*.safetensors"))
                if not matches:
                    raise ValueError(
                        "Diffusion conversion requires a .safetensors file in the model folder "
                        "or an explicit source_file value."
                    )
            else:
                source_path = model_dir / source_file
                if not source_path.exists():
                    raise ValueError(
                        f"source_file '{source_file}' does not exist in {model_dir}."
                    )
        else:
            if not (model_dir / "config.json").exists():
                raise ValueError(
                    "LLM conversion requires config.json in the selected model folder."
                )

        job_id = str(uuid.uuid4())
        now = self._now()
        job = {
            "id": job_id,
            "job_type": "conversion",
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "worker": f"conversion:{request.architecture}",
            "request": request.model_dump(),
            "logs": [f"Queued conversion job for {request.model_name}."],
            "result": None,
            "error": None,
        }
        with self._lock:
            self._jobs[job_id] = job
            self._conversion_queues[request.architecture].put(QueueItem(job_id=job_id))
        return job

    def submit_migration(self, request: MigrationJobRequest) -> dict[str, Any]:
        combo = tuple(sorted(source.architecture for source in request.sources))
        supported = {tuple(sorted(c)) for c in SUPPORTED_MIGRATION_COMBINATIONS}

        if combo not in supported:
            supported_text = [" + ".join(c) for c in SUPPORTED_MIGRATION_COMBINATIONS]
            raise ValueError(
                "Unsupported migration path. Requested architectures: "
                f"{', '.join(combo)}. Supported 3->1 combinations: {supported_text}."
            )

        artifact_names = [source.artifact_name for source in request.sources]
        missing = [name for name in artifact_names if not (CONVERTED_MODELS_DIR / name).exists()]
        if missing:
            raise ValueError(
                "Migration requires converted source artifacts in models/converted. "
                f"Missing files: {missing}."
            )

        job_id = str(uuid.uuid4())
        now = self._now()
        job = {
            "id": job_id,
            "job_type": "migration",
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "worker": "migration:v1",
            "request": request.model_dump(),
            "logs": ["Queued 3-architecture GGUF migration job."],
            "result": None,
            "error": None,
        }
        with self._lock:
            self._jobs[job_id] = job
            self._migration_queue.put(QueueItem(job_id=job_id))
        return job

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.update(updates)
            job["updated_at"] = self._now()

    def _append_log(self, job_id: str, line: str) -> None:
        with self._lock:
            self._jobs[job_id]["logs"].append(line)
            self._jobs[job_id]["updated_at"] = self._now()

    def _conversion_worker_loop(self, architecture: str, q: queue.Queue[QueueItem]) -> None:
        worker_key = f"conversion:{architecture}"
        while True:
            item = q.get()
            self._workers[worker_key]["current_job"] = item.job_id
            self._process_conversion_job(item.job_id, architecture)
            self._workers[worker_key]["current_job"] = None
            q.task_done()

    def _migration_worker_loop(self) -> None:
        worker_key = "migration:v1"
        while True:
            item = self._migration_queue.get()
            self._workers[worker_key]["current_job"] = item.job_id
            self._process_migration_job(item.job_id)
            self._workers[worker_key]["current_job"] = None
            self._migration_queue.task_done()

    def _process_conversion_job(self, job_id: str, architecture: str) -> None:
        job = self.get_job(job_id)
        request = job["request"]
        self._update_job(job_id, status="running")

        model_name = request["model_name"]
        output_name = request.get("output_name") or f"{model_name}-{architecture}.gguf"
        output_path = CONVERTED_MODELS_DIR / output_name
        model_dir = RAW_MODELS_DIR / model_name

        cmd = [
            sys.executable,
            str(ORCHESTRATION_CONVERTER),
            str(model_dir),
            "--outfile",
            str(output_path),
        ]

        if architecture == "diffusion":
            cmd.extend(["--engine", "diffusion"])
            if request.get("source_file"):
                cmd.extend(["--src", request["source_file"]])
        else:
            cmd.extend(["--engine", "llm", "--outtype", request.get("outtype", "q8_0")])

        self._append_log(job_id, f"Executing: {' '.join(cmd)}")

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(ORCHESTRATION_CONVERTER.parent.parent),
                check=False,
            )
            if completed.stdout:
                for line in completed.stdout.strip().splitlines():
                    self._append_log(job_id, line)
            if completed.stderr:
                for line in completed.stderr.strip().splitlines():
                    self._append_log(job_id, f"stderr: {line}")

            if completed.returncode != 0:
                self._update_job(
                    job_id,
                    status="failed",
                    error=(
                        f"Conversion failed with exit code {completed.returncode}. "
                        "Check logs for details."
                    ),
                )
                return

            metadata = load_metadata()
            metadata.setdefault("artifacts", {})[output_name] = {
                "type": "converted",
                "job_id": job_id,
                "architecture": architecture,
                "source_model": model_name,
                "path": str(output_path),
            }
            save_metadata(metadata)

            self._update_job(
                job_id,
                status="completed",
                result={
                    "artifact_type": "converted",
                    "artifact_name": output_name,
                    "artifact_path": str(output_path),
                },
            )
            self._append_log(job_id, f"Conversion completed: {output_name}")
        except Exception as exc:  # pragma: no cover - defensive path
            self._update_job(job_id, status="failed", error=f"Unexpected conversion error: {exc}")

    def _process_migration_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        request = job["request"]
        self._update_job(job_id, status="running")

        target_name = request.get("target_name") or "symoneural-migrated.gguf"
        target_path = MIGRATED_MODELS_DIR / target_name

        try:
            manifest = {
                "job_id": job_id,
                "generated_at": self._now().isoformat(),
                "sources": request["sources"],
                "strategy": "v1:three-architectures-to-one-gguf",
            }
            target_path.write_text(
                "GGUF_MIGRATION_PLACEHOLDER\n" + json.dumps(manifest, indent=2),
                encoding="utf-8",
            )

            metadata = load_metadata()
            metadata.setdefault("artifacts", {})[target_name] = {
                "type": "migrated",
                "job_id": job_id,
                "path": str(target_path),
                "sources": request["sources"],
            }
            save_metadata(metadata)

            self._append_log(job_id, f"Migration output created at {target_path}")
            self._update_job(
                job_id,
                status="completed",
                result={
                    "artifact_type": "migrated",
                    "artifact_name": target_name,
                    "artifact_path": str(target_path),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive path
            self._update_job(job_id, status="failed", error=f"Unexpected migration error: {exc}")

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return dict(job)

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(job) for job in self._jobs.values()]

    def workers_status(self) -> dict[str, Any]:
        status = {}
        for key, data in self._workers.items():
            status[key] = {
                "type": data["type"],
                "architecture": data["architecture"],
                "current_job": data["current_job"],
                "queued": data["queue"].qsize(),
            }
        return status


JOB_MANAGER = JobManager()
