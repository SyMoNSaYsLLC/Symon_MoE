from __future__ import annotations


class SentenceTransformersWorker:
    capabilities = ["embeddings", "semantic-search"]

    def run(self, payload: dict) -> dict:
        # TODO: Wire sentence-transformers execution.
        return {"worker": "sentence_transformers", "status": "stub", "payload": payload}
