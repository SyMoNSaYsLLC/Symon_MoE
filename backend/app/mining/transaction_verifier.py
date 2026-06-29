from __future__ import annotations

from collections import deque
from datetime import UTC, datetime


class TransactionVerifier:
    def __init__(self, limit: int = 100) -> None:
        self._events: deque[dict] = deque(maxlen=limit)

    def record(self, txid: str, source: str = "mempool.space") -> None:
        self._events.appendleft(
            {
                "txid": txid,
                "source": source,
                "verified_at": datetime.now(UTC).isoformat(),
            }
        )

    def recent(self) -> list[dict]:
        return list(self._events)
