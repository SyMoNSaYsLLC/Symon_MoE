"""Worker implementation plan generator for the planning layer."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

_PLANS: dict[str, dict[str, Any]] = {}

WORKER_TYPES = (
    "gguf",
    "onnx",
    "transformers",
    "diffusers",
    "peft",
    "sentence_transformers",
    "embedded",
    "custom",
)


class WorkerPlanGenerator:
    """Generate implementation plans for new worker types."""

    def generate(
        self,
        worker_type: str,
        architecture: str,
        capabilities: list[str],
        notes: str = "",
    ) -> dict[str, Any]:
        plan_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        steps = self._default_steps(worker_type, architecture)
        plan = {
            "id": plan_id,
            "worker_type": worker_type,
            "architecture": architecture,
            "capabilities": capabilities,
            "notes": notes,
            "steps": steps,
            "status": "draft",
            "created_at": now,
            "updated_at": now,
        }
        _PLANS[plan_id] = plan
        return plan

    def get(self, plan_id: str) -> dict[str, Any] | None:
        return _PLANS.get(plan_id)

    def list(self) -> list[dict[str, Any]]:
        return list(_PLANS.values())

    def approve(self, plan_id: str) -> dict[str, Any] | None:
        plan = _PLANS.get(plan_id)
        if plan is None:
            return None
        plan["status"] = "approved"
        plan["updated_at"] = datetime.now(UTC).isoformat()
        return plan

    @staticmethod
    def _default_steps(worker_type: str, architecture: str) -> list[dict[str, str]]:
        return [
            {"step": "1", "action": f"Define {architecture} model schema for {worker_type} worker"},
            {"step": "2", "action": "Implement loader and initialisation logic"},
            {"step": "3", "action": "Implement inference/run method"},
            {"step": "4", "action": "Add hardware throttle integration"},
            {"step": "5", "action": "Register worker in worker_loader registry"},
            {"step": "6", "action": "Write unit tests"},
            {"step": "7", "action": "Update documentation and API schemas"},
        ]
