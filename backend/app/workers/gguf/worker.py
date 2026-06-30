from __future__ import annotations


class GGUFWorker:
    capabilities = ["chat", "inference"]

    def run(self, payload: dict) -> dict:
        # TODO: Wire llama.cpp GGUF runtime execution.
        return {"worker": "gguf", "status": "stub", "payload": payload}
