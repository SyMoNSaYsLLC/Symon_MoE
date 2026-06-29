"""
db.py — SQLite persistence layer for Symoneural.

Provides an async-friendly DbWorker that serialises all writes through a
single aiosqlite connection and exposes synchronous CRUD helpers that push
work onto the async loop from regular (non-async) threads.

Tables
------
  jobs            — all job records (conversion, migration, llm, mining, embed)
  job_logs        — append-only log lines per job
  worker_events   — timestamped worker lifecycle events
  mining_stats    — per-device mining snapshots
  embed_builds    — Yocto/PetaLinux build metadata
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

try:
    import aiosqlite
    _HAS_AIOSQLITE = True
except ImportError:  # pragma: no cover
    _HAS_AIOSQLITE = False

from .config import DB_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    job_type    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'queued',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    worker      TEXT,
    request     TEXT NOT NULL DEFAULT '{}',
    result      TEXT,
    error       TEXT
);

CREATE TABLE IF NOT EXISTS job_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL,
    ts          TEXT NOT NULL,
    line        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_job_logs_job_id ON job_logs(job_id);

CREATE TABLE IF NOT EXISTS worker_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_key  TEXT NOT NULL,
    event       TEXT NOT NULL,
    detail      TEXT,
    ts          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mining_stats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT NOT NULL,
    ts          TEXT NOT NULL,
    hashrate    REAL,
    temperature REAL,
    accepted    INTEGER,
    rejected    INTEGER,
    pool        TEXT,
    raw         TEXT
);

CREATE TABLE IF NOT EXISTS embed_builds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL,
    machine     TEXT,
    image       TEXT,
    status      TEXT NOT NULL DEFAULT 'queued',
    ts          TEXT NOT NULL,
    artifacts   TEXT
);
"""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# DbWorker — runs its own asyncio event loop in a dedicated thread
# ---------------------------------------------------------------------------

class DbWorker:
    """Thread-safe SQLite helper.

    Starts a background asyncio event loop that owns the aiosqlite connection.
    All public methods are synchronous and safe to call from any thread.
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._loop: asyncio.AbstractEventLoop | None = None
        self._conn: aiosqlite.Connection | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="db-worker")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if not _HAS_AIOSQLITE:
            logger.warning("aiosqlite not installed — DB persistence disabled.")
            return
        self._thread.start()
        self._ready.wait(timeout=10)

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._init())
        self._ready.set()
        self._loop.run_forever()

    async def _init(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self._db_path))
        await self._conn.executescript(_DDL)
        await self._conn.commit()
        logger.info("DB initialised at %s", self._db_path)

    def _submit(self, coro) -> Any:
        """Schedule a coroutine on the DB loop and wait for result."""
        if self._loop is None or not _HAS_AIOSQLITE:
            return None
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=30)

    # ------------------------------------------------------------------
    # Job CRUD
    # ------------------------------------------------------------------

    def create_job(self, job_id: str, job_type: str, worker: str | None,
                   request: dict) -> None:
        self._submit(self._create_job(job_id, job_type, worker, request))

    async def _create_job(self, job_id: str, job_type: str, worker: str | None,
                          request: dict) -> None:
        if self._conn is None:
            return
        now = _now_iso()
        await self._conn.execute(
            "INSERT OR REPLACE INTO jobs"
            " (id, job_type, status, created_at, updated_at, worker, request)"
            " VALUES (?, ?, 'queued', ?, ?, ?, ?)",
            (job_id, job_type, now, now, worker, json.dumps(request)),
        )
        await self._conn.commit()

    def update_job(self, job_id: str, status: str | None = None,
                   result: dict | None = None, error: str | None = None) -> None:
        self._submit(self._update_job(job_id, status, result, error))

    async def _update_job(self, job_id: str, status: str | None,
                          result: dict | None, error: str | None) -> None:
        if self._conn is None:
            return
        now = _now_iso()
        fields: list[str] = ["updated_at = ?"]
        params: list[Any] = [now]
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if result is not None:
            fields.append("result = ?")
            params.append(json.dumps(result))
        if error is not None:
            fields.append("error = ?")
            params.append(error)
        params.append(job_id)
        await self._conn.execute(
            f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", params
        )
        await self._conn.commit()

    def append_log(self, job_id: str, line: str) -> None:
        self._submit(self._append_log(job_id, line))

    async def _append_log(self, job_id: str, line: str) -> None:
        if self._conn is None:
            return
        await self._conn.execute(
            "INSERT INTO job_logs (job_id, ts, line) VALUES (?, ?, ?)",
            (job_id, _now_iso(), line),
        )
        await self._conn.commit()

    def get_job(self, job_id: str) -> dict | None:
        return self._submit(self._get_job(job_id))

    async def _get_job(self, job_id: str) -> dict | None:
        if self._conn is None:
            return None
        async with self._conn.execute(
            "SELECT id, job_type, status, created_at, updated_at, worker, request, result, error"
            " FROM jobs WHERE id = ?",
            (job_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return {
            "id": row[0], "job_type": row[1], "status": row[2],
            "created_at": row[3], "updated_at": row[4], "worker": row[5],
            "request": json.loads(row[6] or "{}"),
            "result": json.loads(row[7]) if row[7] else None,
            "error": row[8],
        }

    def list_jobs(self, job_type: str | None = None, status: str | None = None,
                  limit: int = 200) -> list[dict]:
        return self._submit(self._list_jobs(job_type, status, limit)) or []

    async def _list_jobs(self, job_type: str | None, status: str | None,
                         limit: int) -> list[dict]:
        if self._conn is None:
            return []
        clauses: list[str] = []
        params: list[Any] = []
        if job_type:
            clauses.append("job_type = ?")
            params.append(job_type)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        async with self._conn.execute(
            f"SELECT id, job_type, status, created_at, updated_at, worker, request, result, error"
            f" FROM jobs {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ) as cur:
            rows = await cur.fetchall()
        return [
            {
                "id": r[0], "job_type": r[1], "status": r[2],
                "created_at": r[3], "updated_at": r[4], "worker": r[5],
                "request": json.loads(r[6] or "{}"),
                "result": json.loads(r[7]) if r[7] else None,
                "error": r[8],
            }
            for r in rows
        ]

    def get_logs(self, job_id: str, limit: int = 500) -> list[dict]:
        return self._submit(self._get_logs(job_id, limit)) or []

    async def _get_logs(self, job_id: str, limit: int) -> list[dict]:
        if self._conn is None:
            return []
        async with self._conn.execute(
            "SELECT ts, line FROM job_logs WHERE job_id = ?"
            " ORDER BY id DESC LIMIT ?",
            (job_id, limit),
        ) as cur:
            rows = await cur.fetchall()
        return [{"ts": r[0], "line": r[1]} for r in reversed(rows)]

    # ------------------------------------------------------------------
    # Worker events
    # ------------------------------------------------------------------

    def record_worker_event(self, worker_key: str, event: str,
                            detail: str | None = None) -> None:
        self._submit(self._record_worker_event(worker_key, event, detail))

    async def _record_worker_event(self, worker_key: str, event: str,
                                   detail: str | None) -> None:
        if self._conn is None:
            return
        await self._conn.execute(
            "INSERT INTO worker_events (worker_key, event, detail, ts)"
            " VALUES (?, ?, ?, ?)",
            (worker_key, event, detail, _now_iso()),
        )
        await self._conn.commit()

    # ------------------------------------------------------------------
    # Mining stats
    # ------------------------------------------------------------------

    def record_mining_stat(self, device_id: str, hashrate: float | None = None,
                           temperature: float | None = None, accepted: int | None = None,
                           rejected: int | None = None, pool: str | None = None,
                           raw: dict | None = None) -> None:
        self._submit(self._record_mining_stat(
            device_id, hashrate, temperature, accepted, rejected, pool, raw
        ))

    async def _record_mining_stat(self, device_id: str, hashrate: float | None,
                                   temperature: float | None, accepted: int | None,
                                   rejected: int | None, pool: str | None,
                                   raw: dict | None) -> None:
        if self._conn is None:
            return
        await self._conn.execute(
            "INSERT INTO mining_stats"
            " (device_id, ts, hashrate, temperature, accepted, rejected, pool, raw)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (device_id, _now_iso(), hashrate, temperature, accepted, rejected, pool,
             json.dumps(raw) if raw else None),
        )
        await self._conn.commit()

    def latest_mining_stats(self, limit: int = 50) -> list[dict]:
        return self._submit(self._latest_mining_stats(limit)) or []

    async def _latest_mining_stats(self, limit: int) -> list[dict]:
        if self._conn is None:
            return []
        async with self._conn.execute(
            "SELECT device_id, ts, hashrate, temperature, accepted, rejected, pool"
            " FROM mining_stats ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
        return [
            {"device_id": r[0], "ts": r[1], "hashrate": r[2], "temperature": r[3],
             "accepted": r[4], "rejected": r[5], "pool": r[6]}
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Embed builds
    # ------------------------------------------------------------------

    def record_embed_build(self, job_id: str, machine: str, image: str) -> None:
        self._submit(self._record_embed_build(job_id, machine, image))

    async def _record_embed_build(self, job_id: str, machine: str, image: str) -> None:
        if self._conn is None:
            return
        await self._conn.execute(
            "INSERT INTO embed_builds (job_id, machine, image, status, ts)"
            " VALUES (?, ?, ?, 'queued', ?)",
            (job_id, machine, image, _now_iso()),
        )
        await self._conn.commit()

    def update_embed_build(self, job_id: str, status: str,
                           artifacts: list[str] | None = None) -> None:
        self._submit(self._update_embed_build(job_id, status, artifacts))

    async def _update_embed_build(self, job_id: str, status: str,
                                   artifacts: list[str] | None) -> None:
        if self._conn is None:
            return
        await self._conn.execute(
            "UPDATE embed_builds SET status = ?, artifacts = ?, ts = ?"
            " WHERE job_id = ?",
            (status, json.dumps(artifacts) if artifacts else None, _now_iso(), job_id),
        )
        await self._conn.commit()

    def list_embed_builds(self, limit: int = 100) -> list[dict]:
        return self._submit(self._list_embed_builds(limit)) or []

    async def _list_embed_builds(self, limit: int) -> list[dict]:
        if self._conn is None:
            return []
        async with self._conn.execute(
            "SELECT job_id, machine, image, status, ts, artifacts"
            " FROM embed_builds ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
        return [
            {"job_id": r[0], "machine": r[1], "image": r[2], "status": r[3],
             "ts": r[4], "artifacts": json.loads(r[5]) if r[5] else []}
            for r in rows
        ]


# Module-level singleton — started by main.py startup handler
DB_WORKER = DbWorker()
