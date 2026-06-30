from __future__ import annotations


class TransformersWorker:
    capabilities = ["chat", "embeddings", "classification", "inference"]

    def run(self, payload: dict) -> dict:
        # TODO: Wire HF Transformers runtime execution.
        return {"worker": "transformers", "status": "stub", "payload": payload}
