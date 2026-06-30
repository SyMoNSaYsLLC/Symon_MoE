from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from typing import Any

from ..jobs import JOB_MANAGER


class MiningWorker:
    def __init__(self) -> None:
        self._threads: dict[str, threading.Thread] = {}
        self._active: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def start(self, device_id: str, pool: str) -> dict[str, Any]:
        with self._lock:
            if device_id in self._threads and self._threads[device_id].is_alive():
                return {"device_id": device_id, "status": "already_running"}

            self._active[device_id] = {
                "device_id": device_id,
                "pool": pool,
                "hashrate": 0.0,
                "temperature": 0.0,
                "accepted_shares": 0,
                "rejected_shares": 0,
                "started_at": datetime.now(UTC).isoformat(),
                "running": True,
            }

            t = threading.Thread(target=self._loop, args=(device_id,), daemon=True)
            self._threads[device_id] = t
            t.start()
            JOB_MANAGER.db.add_worker_event("mining:worker", "miner_started", {"device_id": device_id, "pool": pool})
            return {"device_id": device_id, "status": "started"}

    def stop(self, device_id: str) -> dict[str, Any]:
        with self._lock:
            entry = self._active.get(device_id)
            if not entry:
                return {"device_id": device_id, "status": "not_running"}
            entry["running"] = False
            JOB_MANAGER.db.add_worker_event("mining:worker", "miner_stopped", {"device_id": device_id})
            return {"device_id": device_id, "status": "stopping"}

    def _loop(self, device_id: str) -> None:
        while True:
            with self._lock:
                item = self._active.get(device_id)
                if not item or not item.get("running"):
                    self._active.pop(device_id, None)
                    return
                item["hashrate"] = round(item.get("hashrate", 0.0) + 1.25, 2)
                item["temperature"] = round(55.0 + (item["hashrate"] % 15), 2)
                item["accepted_shares"] += 1
                stats = dict(item)
            JOB_MANAGER.db.add_mining_stat(device_id, stats)
            time.sleep(3)

    def status(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(v) for v in self._active.values()]
