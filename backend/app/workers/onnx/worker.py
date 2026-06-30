from __future__ import annotations


class ONNXWorker:
    capabilities = ["inference", "classification"]

    def run(self, payload: dict) -> dict:
        # TODO: Wire ONNX Runtime execution.
        return {"worker": "onnx", "status": "stub", "payload": payload}
