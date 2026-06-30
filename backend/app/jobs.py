from __future__ import annotations

import json
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from .config import (
    CONVERTED_MODELS_DIR,
    DB_PATH,
    MIGRATED_MODELS_DIR,
    ORCHESTRATION_CONVERTER,
    RAW_MODELS_DIR,
    SUPPORTED_ARCHITECTURES,
    SUPPORTED_MIGRATION_COMBINATIONS,
)
from .db import DbWorker
from .schemas import ConversionJobRequest, MigrationJobRequest
from .storage import ensure_storage_contract, load_metadata, save_metadata

HELPERS_PYTHON_DIR = Path(__file__).resolve().parents[2] / "helpers" / "python"
if str(HELPERS_PYTHON_DIR) not in sys.path:
    sys.path.append(str(HELPERS_PYTHON_DIR))

try:
    from hardware_throttle import throttle_check
except Exception:  # pragma: no cover
    def throttle_check() -> bool:
        return True


SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass
class QueueItem:
    job_id: str


@dataclass
class LlmQueueItem:
    job_id: str
    operation: str
    prompt: str
    model: str
    context: dict[str, Any]


@dataclass
class DbTask:
    operation: str
    payload: dict[str, Any]


class PoolWorker(threading.Thread):
    def __init__(self, manager: "JobManager", worker_key: str, worker_type: str, architecture: str) -> None:
        super().__init__(daemon=True)
        self.manager = manager
        self.worker_key = worker_key
        self.worker_type = worker_type
        self.architecture = architecture
        self._queue: queue.Queue[Any] = queue.Queue()
        self.current_job: str | None = None
        self.last_task: str | None = None

    @property
    def queued(self) -> int:
        return self._queue.qsize()

    def enqueue(self, item: Any) -> None:
        self._queue.put(item)

    def run(self) -> None:
        while True:
            item = self._queue.get()
            self.current_job = getattr(item, "job_id", None)
            try:
                if not throttle_check():
                    self.last_task = "throttled"
                    self.manager._append_log(self.current_job or "", "Worker throttled due to hardware limits.")
                    time.sleep(1.0)
                    self._queue.put(item)
                    continue
                self.process_item(item)
                self.last_task = f"processed:{self.current_job or 'task'}"
            finally:
                self.current_job = None
                self._queue.task_done()

    def process_item(self, item: Any) -> None:
        raise NotImplementedError


class DatabaseWorker(PoolWorker):
    def __init__(self, manager: "JobManager") -> None:
        super().__init__(manager, "database:sqlite", "database", "sqlite")

    def process_item(self, item: DbTask) -> None:
        if item.operation == "job_create":
            self.manager.db.create_job(item.payload)
        elif item.operation == "job_update":
            self.manager.db.update_job(
                item.payload["id"],
                item.payload["status"],
                item.payload.get("worker"),
                item.payload.get("result"),
                item.payload.get("error"),
            )
        elif item.operation == "log_append":
            self.manager.db.append_log(item.payload["job_id"], item.payload["line"])
        elif item.operation == "worker_event":
            self.manager.db.add_worker_event(
                item.payload["worker_name"],
                item.payload["event_type"],
                item.payload.get("payload"),
            )


class ConversionWorker(PoolWorker):
    def __init__(self, manager: "JobManager", architecture: str) -> None:
        super().__init__(manager, f"conversion:{architecture}", "conversion", architecture)

    def process_item(self, item: QueueItem) -> None:
        self.manager._process_conversion_job(item.job_id, self.architecture)


class MigrationWorker(PoolWorker):
    def __init__(self, manager: "JobManager") -> None:
        super().__init__(manager, "migration:v1", "migration", "v1")

    def process_item(self, item: QueueItem) -> None:
        self.manager._process_migration_job(item.job_id)


class LlmWorker(PoolWorker):
    def __init__(self, manager: "JobManager") -> None:
        super().__init__(manager, "llm:ollama", "llm", "ollama")

    def process_item(self, item: LlmQueueItem) -> None:
        self.manager._update_job(item.job_id, status="running", worker=self.worker_key)
        self.manager._append_log(item.job_id, f"Dispatching {item.operation} prompt to Ollama model '{item.model}'.")

        payload = {
            "model": item.model,
            "prompt": item.prompt,
            "stream": False,
        }
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(f"{self.manager.ollama_base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                response_text = data.get("response", "")
                self.manager._append_log(item.job_id, "LLM request completed.")
                self.manager._update_job(
                    item.job_id,
                    status="completed",
                    worker=self.worker_key,
                    result={
                        "operation": item.operation,
                        "model": item.model,
                        "response": response_text,
                        "context": item.context,
                    },
                )
        except Exception as exc:
            self.manager._append_log(item.job_id, f"LLM request failed: {exc}")
            self.manager._update_job(
                item.job_id,
                status="failed",
                worker=self.worker_key,
                error=f"LLM request failed: {exc}",
            )


class JobManager:
    def __init__(self) -> None:
        ensure_storage_contract()
        self.db = DbWorker(DB_PATH)
        self.db.start()
        self.ollama_base_url = "http://localhost:11434"

        self._workers: dict[str, PoolWorker] = {}
        self._database_worker = DatabaseWorker(self)
        self._workers[self._database_worker.worker_key] = self._database_worker

        self._conversion_workers: dict[str, ConversionWorker] = {}
        for architecture in SUPPORTED_ARCHITECTURES:
            worker = ConversionWorker(self, architecture)
            self._conversion_workers[architecture] = worker
            self._workers[worker.worker_key] = worker

        self._migration_worker = MigrationWorker(self)
        self._workers[self._migration_worker.worker_key] = self._migration_worker

        self._llm_worker = LlmWorker(self)
        self._workers[self._llm_worker.worker_key] = self._llm_worker

        for worker in self._workers.values():
            worker.start()

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

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

    def _db_enqueue(self, operation: str, payload: dict[str, Any], wait: bool = False) -> None:
        self._database_worker.enqueue(DbTask(operation=operation, payload=payload))
        if wait:
            self._database_worker._queue.join()

    def _create_job(
        self,
        job_id: str,
        job_type: str,
        worker: str,
        request_payload: dict[str, Any],
        initial_log: str,
    ) -> dict[str, Any]:
        now = self._now()
        job = {
            "id": job_id,
            "job_type": job_type,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "worker": worker,
            "request": request_payload,
            "result": None,
            "error": None,
        }
        self._db_enqueue("job_create", job, wait=True)
        self._db_enqueue("log_append", {"job_id": job_id, "line": initial_log}, wait=True)
        self._db_enqueue(
            "worker_event",
            {
                "worker_name": worker,
                "event_type": "job_queued",
                "payload": {"job_id": job_id, "job_type": job_type},
            },
        )
        return {**job, "logs": [initial_log]}

    def _update_job(
        self,
        job_id: str,
        status: str,
        worker: str | None = None,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        self._db_enqueue(
            "job_update",
            {
                "id": job_id,
                "status": status,
                "worker": worker,
                "result": result,
                "error": error,
            },
            wait=True,
        )
        if worker:
            self._db_enqueue(
                "worker_event",
                {
                    "worker_name": worker,
                    "event_type": f"job_{status}",
                    "payload": {"job_id": job_id, "status": status},
                },
            )

    def _append_log(self, job_id: str, line: str) -> None:
        if not job_id:
            return
        self._db_enqueue("log_append", {"job_id": job_id, "line": line}, wait=False)

    def submit_conversion(self, request: ConversionJobRequest) -> dict[str, Any]:
        if request.architecture not in self._conversion_workers:
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
        job = self._create_job(
            job_id=job_id,
            job_type="conversion",
            worker=f"conversion:{request.architecture}",
            request_payload={
                **request.model_dump(),
                "model_name": model_name,
                "model_dir": str(model_dir),
            },
            initial_log=f"Queued conversion job for {model_name}.",
        )
        self._conversion_workers[request.architecture].enqueue(QueueItem(job_id=job_id))
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
        job = self._create_job(
            job_id=job_id,
            job_type="migration",
            worker="migration:v1",
            request_payload={
                "sources": safe_sources,
                "source_artifact_paths": source_artifact_paths,
                "target_name": target_name,
            },
            initial_log="Queued 3-architecture GGUF migration job.",
        )
        self._migration_worker.enqueue(QueueItem(job_id=job_id))
        return job

    def submit_llm_job(
        self,
        operation: str,
        prompt: str,
        model: str = "llama3",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        payload = {
            "operation": operation,
            "prompt": prompt,
            "model": model,
            "context": context or {},
        }
        job = self._create_job(
            job_id=job_id,
            job_type="llm",
            worker="llm:ollama",
            request_payload=payload,
            initial_log=f"Queued LLM {operation} job.",
        )
        self._llm_worker.enqueue(
            LlmQueueItem(
                job_id=job_id,
                operation=operation,
                prompt=prompt,
                model=model,
                context=context or {},
            )
        )
        return job

    def _process_conversion_job(self, job_id: str, architecture: str) -> None:
        job = self.get_job(job_id)
        request = job["request"]
        worker_key = f"conversion:{architecture}"
        self._update_job(job_id, status="running", worker=worker_key)

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
                    worker=worker_key,
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
                worker=worker_key,
                result={
                    "artifact_type": "converted",
                    "artifact_name": output_name,
                    "artifact_path": str(output_path),
                },
            )
            self._append_log(job_id, f"Conversion completed: {output_name}")
        except Exception as exc:  # pragma: no cover
            self._update_job(job_id, status="failed", worker=worker_key, error=f"Unexpected conversion error: {exc}")

    def _process_migration_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        request = job["request"]
        worker_key = "migration:v1"
        self._update_job(job_id, status="running", worker=worker_key)

        requested_target = request.get("target_name")
        if requested_target:
            requested_target = self._validate_safe_name(requested_target, "target_name", ".gguf")
        target_name = requested_target or f"migration-{job_id}.gguf"
        target_path = MIGRATED_MODELS_DIR / target_name

        try:
            manifest = {
                "job_id": job_id,
                "generated_at": self._now(),
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
                worker=worker_key,
                result={
                    "artifact_type": "migrated",
                    "artifact_name": target_name,
                    "artifact_path": str(target_path),
                },
            )
        except Exception as exc:  # pragma: no cover
            self._update_job(job_id, status="failed", worker=worker_key, error=f"Unexpected migration error: {exc}")

    def get_job(self, job_id: str) -> dict[str, Any]:
        job = self.db.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    def list_jobs(self) -> list[dict[str, Any]]:
        return self.db.list_jobs()

    def get_job_logs(self, job_id: str) -> list[str]:
        if self.db.get_job(job_id) is None:
            raise KeyError(job_id)
        return self.db.get_job_logs(job_id)

    def workers_status(self) -> dict[str, Any]:
        status = {}
        for key, worker in self._workers.items():
            status[key] = {
                "type": worker.worker_type,
                "architecture": worker.architecture,
                "current_job": worker.current_job,
                "queued": worker.queued,
                "last_task": worker.last_task,
            }
        return status


JOB_MANAGER = JobManager()
