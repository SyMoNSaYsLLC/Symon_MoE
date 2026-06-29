from __future__ import annotations


def run_braiins_action(miner_ip: str, action: str, payload: dict | None = None) -> dict:
    return {
        "miner_ip": miner_ip,
        "action": action,
        "payload": payload or {},
        "status": "queued",
        "detail": "Braiins OS integration stub executed.",
    }
