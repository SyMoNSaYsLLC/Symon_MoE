from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.db import DbWorker


_DB: DbWorker | None = None


def init_db(path: str | Path) -> DbWorker:
    global _DB
    _DB = DbWorker(Path(path))
    _DB.start()
    return _DB


def get_db() -> DbWorker:
    if _DB is None:
        raise RuntimeError("DB not initialized. Call init_db first.")
    return _DB


def create_job(job: dict[str, Any]) -> None:
    get_db().create_job(job)


def update_job(job_id: str, status: str, result: dict | None = None, error: str | None = None) -> None:
    get_db().update_job(job_id=job_id, status=status, result=result, error=error)


def append_log(job_id: str, line: str) -> None:
    get_db().append_log(job_id, line)
