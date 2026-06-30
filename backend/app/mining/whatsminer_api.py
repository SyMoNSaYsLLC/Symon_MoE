from __future__ import annotations


def run_whatsminer_action(miner_ip: str, action: str, payload: dict | None = None) -> dict:
    return {
        "miner_ip": miner_ip,
        "action": action,
        "payload": payload or {},
        "status": "queued",
        "detail": "WhatsMiner API integration stub executed.",
    }
