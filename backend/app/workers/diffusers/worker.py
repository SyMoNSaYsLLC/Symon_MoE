from __future__ import annotations


class DiffusersWorker:
    capabilities = ["text-to-image", "image-to-image"]

    def run(self, payload: dict) -> dict:
        # TODO: Wire Diffusers / Stable Diffusion pipeline execution.
        return {"worker": "diffusers", "status": "stub", "payload": payload}
