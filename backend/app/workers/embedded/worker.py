from __future__ import annotations


class EmbeddedWorker:
    capabilities = ["deployment", "packaging", "edge-inference"]

    def run(self, payload: dict) -> dict:
        # TODO: Wire embedded deployment packaging and runtime handoff.
        return {"worker": "embedded", "status": "stub", "payload": payload}
