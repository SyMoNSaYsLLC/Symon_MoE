from __future__ import annotations

import asyncio
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

DB_TIMEOUT_SECONDS = float(os.getenv("DB_TIMEOUT_SECONDS", "60"))


class DbWorker:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._conn: aiosqlite.Connection | None = None
        self._ready = threading.Event()
        self._write_queue: asyncio.Queue[tuple[str, dict[str, Any], asyncio.Future | None] | None] | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        def _runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            loop.run_until_complete(self._bootstrap())
            loop.run_forever()

        self._thread = threading.Thread(target=_runner, name="db-worker", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=10)

    async def _bootstrap(self) -> None:
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA synchronous=NORMAL")
        await self._ensure_tables()
        await self._conn.commit()
        self._write_queue = asyncio.Queue()
        asyncio.create_task(self._flush_loop())
        self._ready.set()

    async def _ensure_tables(self) -> None:
        assert self._conn is not None
        await self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                worker TEXT,
                request_json TEXT NOT NULL,
                result_json TEXT,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS job_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                line TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS worker_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mining_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                hashrate REAL,
                temperature REAL,
                accepted_shares INTEGER,
                rejected_shares INTEGER,
                payload_json TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS embed_builds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT,
                timestamp TEXT NOT NULL
            );
            """
        )

    def _run_coro(self, coro):
        if not self._loop:
            raise RuntimeError("DbWorker loop not started")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=DB_TIMEOUT_SECONDS)

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    async def _queue_write(self, op: str, payload: dict[str, Any], wait: bool = True) -> None:
        assert self._write_queue is not None
        signal: asyncio.Future | None = asyncio.get_running_loop().create_future() if wait else None
        await self._write_queue.put((op, payload, signal))
        if signal is not None:
            await signal

    async def _flush_loop(self) -> None:
        assert self._write_queue is not None
        while True:
            item = await self._write_queue.get()
            if item is None:
                self._write_queue.task_done()
                break
            op, payload, signal = item
            try:
                await self._execute_write(op, payload)
                if signal and not signal.done():
                    signal.set_result(True)
            except Exception as exc:
                if signal and not signal.done():
                    signal.set_exception(exc)
            finally:
                self._write_queue.task_done()

    async def _execute_write(self, op: str, payload: dict[str, Any]) -> None:
        assert self._conn is not None
        if op == "create_job":
            await self._conn.execute(
                """
                INSERT INTO jobs(id, job_type, status, created_at, updated_at, worker, request_json, result_json, error)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["job_type"],
                    payload["status"],
                    payload["created_at"],
                    payload["updated_at"],
                    payload.get("worker"),
                    json.dumps(payload.get("request") or {}),
                    json.dumps(payload.get("result")) if payload.get("result") is not None else None,
                    payload.get("error"),
                ),
            )
        elif op == "update_job":
            await self._conn.execute(
                """
                UPDATE jobs
                SET status=?, updated_at=?, worker=?, result_json=?, error=?
                WHERE id=?
                """,
                (
                    payload["status"],
                    payload["updated_at"],
                    payload.get("worker"),
                    json.dumps(payload.get("result")) if payload.get("result") is not None else None,
                    payload.get("error"),
                    payload["id"],
                ),
            )
        elif op == "append_log":
            await self._conn.execute(
                "INSERT INTO job_logs(job_id, timestamp, line) VALUES(?, ?, ?)",
                (payload["job_id"], payload["timestamp"], payload["line"]),
            )
            await self._conn.execute(
                "UPDATE jobs SET updated_at=? WHERE id=?",
                (payload["timestamp"], payload["job_id"]),
            )
        elif op == "worker_event":
            await self._conn.execute(
                "INSERT INTO worker_events(worker_name, event_type, payload_json, timestamp) VALUES(?, ?, ?, ?)",
                (
                    payload["worker_name"],
                    payload["event_type"],
                    json.dumps(payload.get("payload") or {}),
                    payload["timestamp"],
                ),
            )
        elif op == "mining_stat":
            await self._conn.execute(
                """
                INSERT INTO mining_stats(device_id, hashrate, temperature, accepted_shares, rejected_shares, payload_json, timestamp)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["device_id"],
                    payload.get("hashrate"),
                    payload.get("temperature"),
                    payload.get("accepted_shares"),
                    payload.get("rejected_shares"),
                    json.dumps(payload.get("payload") or {}),
                    payload["timestamp"],
                ),
            )
        elif op == "embed_build":
            await self._conn.execute(
                "INSERT INTO embed_builds(job_id, stage, status, payload_json, timestamp) VALUES(?, ?, ?, ?, ?)",
                (
                    payload.get("job_id"),
                    payload["stage"],
                    payload["status"],
                    json.dumps(payload.get("payload") or {}),
                    payload["timestamp"],
                ),
            )
        await self._conn.commit()

    def create_job(self, job: dict[str, Any]) -> None:
        payload = {**job}
        payload.setdefault("created_at", self._now())
        payload.setdefault("updated_at", payload["created_at"])
        self._run_coro(self._queue_write("create_job", payload))

    def update_job(self, job_id: str, status: str, worker: str | None = None, result: dict | None = None, error: str | None = None) -> None:
        self._run_coro(
            self._queue_write(
                "update_job",
                {
                    "id": job_id,
                    "status": status,
                    "updated_at": self._now(),
                    "worker": worker,
                    "result": result,
                    "error": error,
                },
            )
        )

    def append_log(self, job_id: str, line: str) -> None:
        self._run_coro(self._queue_write("append_log", {"job_id": job_id, "line": line, "timestamp": self._now()}))

    def add_worker_event(self, worker_name: str, event_type: str, payload: dict[str, Any] | None = None) -> None:
        self._run_coro(
            self._queue_write(
                "worker_event",
                {
                    "worker_name": worker_name,
                    "event_type": event_type,
                    "payload": payload or {},
                    "timestamp": self._now(),
                },
                wait=False,
            )
        )

    def add_mining_stat(self, device_id: str, stats: dict[str, Any]) -> None:
        payload = {
            "device_id": device_id,
            "hashrate": stats.get("hashrate"),
            "temperature": stats.get("temperature"),
            "accepted_shares": stats.get("accepted_shares"),
            "rejected_shares": stats.get("rejected_shares"),
            "payload": stats,
            "timestamp": self._now(),
        }
        self._run_coro(self._queue_write("mining_stat", payload, wait=False))

    def add_embed_build(self, job_id: str | None, stage: str, status: str, payload: dict[str, Any] | None = None) -> None:
        self._run_coro(
            self._queue_write(
                "embed_build",
                {
                    "job_id": job_id,
                    "stage": stage,
                    "status": status,
                    "payload": payload or {},
                    "timestamp": self._now(),
                },
                wait=False,
            )
        )

    async def _job_row_to_dict(self, row: aiosqlite.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "job_type": row["job_type"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "worker": row["worker"],
            "request": json.loads(row["request_json"] or "{}"),
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error": row["error"],
        }

    async def _read_job(self, job_id: str) -> dict[str, Any] | None:
        assert self._conn is not None
        cur = await self._conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        row = await cur.fetchone()
        await cur.close()
        if row is None:
            return None
        job = await self._job_row_to_dict(row)
        job["logs"] = await self._read_logs(job_id)
        return job

    async def _read_jobs(self) -> list[dict[str, Any]]:
        assert self._conn is not None
        cur = await self._conn.execute("SELECT * FROM jobs ORDER BY created_at ASC")
        rows = await cur.fetchall()
        await cur.close()
        jobs = []
        for row in rows:
            job = await self._job_row_to_dict(row)
            job["logs"] = await self._read_logs(job["id"])
            jobs.append(job)
        return jobs

    async def _read_logs(self, job_id: str) -> list[str]:
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT line FROM job_logs WHERE job_id=? ORDER BY id ASC", (job_id,)
        )
        rows = await cur.fetchall()
        await cur.close()
        return [row["line"] for row in rows]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self._run_coro(self._read_job(job_id))

    def list_jobs(self) -> list[dict[str, Any]]:
        return self._run_coro(self._read_jobs())

    def get_job_logs(self, job_id: str) -> list[str]:
        return self._run_coro(self._read_logs(job_id))

    async def _read_worker_events(self, limit: int = 200) -> list[dict[str, Any]]:
        assert self._conn is not None
        cur = await self._conn.execute(
            "SELECT worker_name, event_type, payload_json, timestamp FROM worker_events ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
        await cur.close()
        return [
            {
                "worker_name": row["worker_name"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"] or "{}"),
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    def list_worker_events(self, limit: int = 200) -> list[dict[str, Any]]:
        return self._run_coro(self._read_worker_events(limit))
