from __future__ import annotations

import json
import logging
import os
import queue
import re
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import httpx

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

logger = logging.getLogger(__name__)

SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


# ---------------------------------------------------------------------------
# PoolWorker — base class for workers that process generic job queues
# ---------------------------------------------------------------------------

class PoolWorker:
    """Base class for workers backed by a threading.Queue.

    Subclasses override ``_process(job_id, payload)`` to do actual work.
    """

    worker_key: str = "pool:base"

    def __init__(self) -> None:
        self._queue: queue.Queue[QueueItem] = queue.Queue()
        self._current_job: str | None = None
        self._lock = threading.Lock()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name=self.worker_key
        )

    def start(self) -> None:
        self._thread.start()

    def submit(self, job_id: str) -> None:
        self._queue.put(QueueItem(job_id=job_id))

    def status(self) -> dict:
        return {
            "type": self.worker_key.split(":")[0],
            "worker_key": self.worker_key,
            "current_job": self._current_job,
            "queued": self._queue.qsize(),
        }

    def _loop(self) -> None:
        while True:
            item = self._queue.get()
            with self._lock:
                self._current_job = item.job_id
            try:
                self._process(item.job_id)
            except Exception:  # pragma: no cover
                logger.exception("Unhandled error in worker %s for job %s",
                                  self.worker_key, item.job_id)
            finally:
                with self._lock:
                    self._current_job = None
                self._queue.task_done()

    def _process(self, job_id: str) -> None:  # noqa: D401
        raise NotImplementedError


# ---------------------------------------------------------------------------
# DatabaseWorker — serialises writes to the DB worker (thin shim)
# ---------------------------------------------------------------------------

class DatabaseWorker(PoolWorker):
    """Serialises out-of-band DB writes that don't fit the async path."""

    worker_key = "db:writer"

    def __init__(self) -> None:
        super().__init__()
        self._write_queue: queue.Queue[tuple] = queue.Queue()
        self._thread = threading.Thread(
            target=self._write_loop, daemon=True, name="db-writer"
        )

    def enqueue_write(self, op: str, *args: Any) -> None:
        self._write_queue.put((op, args))

    def _write_loop(self) -> None:
        from .db import DB_WORKER
        while True:
            op, args = self._write_queue.get()
            try:
                fn = getattr(DB_WORKER, op, None)
                if fn:
                    fn(*args)
            except Exception:  # pragma: no cover
                logger.exception("DB write error op=%s", op)
            finally:
                self._write_queue.task_done()

    def _process(self, job_id: str) -> None:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# LlmWorker — non-blocking LLM inference via Ollama
# ---------------------------------------------------------------------------

class LlmWorker(PoolWorker):
    """Pulls LLM job requests from a queue, calls Ollama, stores results in DB."""

    worker_key = "llm:inference"

    def __init__(self, jobs_ref: dict, lock: threading.Lock) -> None:
        super().__init__()
        self._jobs = jobs_ref
        self._jobs_lock = lock

    def _process(self, job_id: str) -> None:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
        if job is None:
            return

        request = job.get("request", {})
        model = request.get("model", "llama3")
        prompt = request.get("prompt", "")
        options: dict = {}
        if request.get("temperature") is not None:
            options["temperature"] = request["temperature"]

        self._update_job(job_id, status="running")
        self._append_log(job_id, f"LlmWorker: calling model={model}")

        try:
            payload: dict = {"model": model, "prompt": prompt, "stream": False}
            if options:
                payload["options"] = options
            resp = httpx.post(
                f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=300.0
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama returned {resp.status_code}: {resp.text[:200]}")
            response_text = resp.json().get("response", "")
            self._update_job(job_id, status="completed",
                             result={"response": response_text})
            self._append_log(job_id, "LlmWorker: completed")
        except Exception as exc:
            self._update_job(job_id, status="failed", error=str(exc))
            self._append_log(job_id, f"LlmWorker error: {exc}")

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if job:
                job.update(updates)
                job["updated_at"] = datetime.now(UTC)

    def _append_log(self, job_id: str, line: str) -> None:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if job:
                job.setdefault("logs", []).append(line)
                job["updated_at"] = datetime.now(UTC)


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

        # New workers
        self._llm_worker = LlmWorker(self._jobs, self._lock)
        self._db_writer = DatabaseWorker()

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

        # Start new pool-based workers
        self._llm_worker.start()
        self._db_writer.start()

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _validate_safe_name(self, value: str, field_name: str, expected_suffix: str | None = None) -> str:
        if not SAFE_NAME_PATTERN.fullmatch(value):
            raise ValueError(
                f"{field_name} contains unsupported characters. Use only letters, numbers, ., _, -."
            )
        if value in {".", ".."}:
            raise ValueError(f"{field_name} cannot be '.' or '..'.")
        if expected_suffix and not value.endswith(expected_suffix):
            raise ValueError(f"{field_name} must end with {expected_suffix}.")
        return value

    def _find_named_directory(self, base_dir: Path, directory_name: str) -> Path | None:
        for entry in base_dir.iterdir():
            if entry.is_dir() and entry.name == directory_name:
                return entry.resolve()
        return None

    def _find_named_file(self, base_dir: Path, file_name: str) -> Path | None:
        for entry in base_dir.iterdir():
            if entry.is_file() and entry.name == file_name:
                return entry.resolve()
        return None

    def submit_conversion(self, request: ConversionJobRequest) -> dict[str, Any]:
        if request.architecture not in self._conversion_queues:
            raise ValueError(f"Unsupported architecture '{request.architecture}'.")

        model_name = self._validate_safe_name(request.model_name, "model_name")
        model_dir = self._find_named_directory(RAW_MODELS_DIR, model_name)
        if model_dir is None:
            raise ValueError(
                f"Raw model folder '{model_name}' was not found under {RAW_MODELS_DIR}."
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
                safe_source_file = self._validate_safe_name(source_file, "source_file", ".safetensors")
                source_path = self._find_named_file(model_dir, safe_source_file)
                if source_path is None:
                    raise ValueError(
                        f"source_file '{safe_source_file}' does not exist in {model_dir}."
                    )
        else:
            if not (model_dir / "config.json").exists():
                raise ValueError(
                    "LLM conversion requires config.json in the selected model folder."
                )

        output_name = request.output_name
        if output_name is not None:
            self._validate_safe_name(output_name, "output_name", ".gguf")

        job_id = str(uuid.uuid4())
        now = self._now()
        job = {
            "id": job_id,
            "job_type": "conversion",
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "worker": f"conversion:{request.architecture}",
            "request": {
                **request.model_dump(),
                "model_name": model_name,
                "model_dir": str(model_dir),
            },
            "logs": [f"Queued conversion job for {model_name}."],
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

        target_name = self._validate_safe_name(request.target_name, "target_name", ".gguf")
        safe_sources = []
        for source in request.sources:
            safe_sources.append(
                {
                    "architecture": source.architecture,
                    "artifact_name": self._validate_safe_name(
                        source.artifact_name,
                        f"artifact_name ({source.architecture})",
                        ".gguf",
                    ),
                }
            )

        artifact_names = [source["artifact_name"] for source in safe_sources]
        source_artifact_paths = []
        missing = []
        for name in artifact_names:
            artifact_path = self._find_named_file(CONVERTED_MODELS_DIR, name)
            if artifact_path is None:
                missing.append(name)
            else:
                source_artifact_paths.append(str(artifact_path))
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
            "request": {
                "sources": safe_sources,
                "source_artifact_paths": source_artifact_paths,
                "target_name": target_name,
            },
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
        requested_output = request.get("output_name")
        if requested_output:
            requested_output = self._validate_safe_name(requested_output, "output_name", ".gguf")
        output_name = requested_output or f"{job_id}-{model_name}-{architecture}.gguf"
        output_path = CONVERTED_MODELS_DIR / output_name
        model_dir = Path(request["model_dir"]).resolve()

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
                cmd.extend(
                    [
                        "--src",
                        self._validate_safe_name(
                            request["source_file"], "source_file", ".safetensors"
                        ),
                    ]
                )
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

        requested_target = request.get("target_name")
        if requested_target:
            requested_target = self._validate_safe_name(requested_target, "target_name", ".gguf")
        target_name = requested_target or f"migration-{job_id}.gguf"
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
