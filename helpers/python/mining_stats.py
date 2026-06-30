from __future__ import annotations

from typing import Any


def normalize_stats(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "hashrate": float(payload.get("MHS av", payload.get("hashrate", 0.0))),
        "temperature": float(payload.get("Temperature", payload.get("temperature", 0.0))),
        "accepted_shares": int(payload.get("Accepted", payload.get("accepted_shares", 0))),
        "rejected_shares": int(payload.get("Rejected", payload.get("rejected_shares", 0))),
    }
