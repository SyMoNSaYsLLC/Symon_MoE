"""Task breakdown for the planning layer."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

_TASKS: dict[str, dict[str, Any]] = {}


class TaskBreaker:
    """Break milestones into discrete tasks."""

    def create(
        self,
        milestone_id: str,
        name: str,
        description: str = "",
        estimate_hours: float = 0.0,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        task = {
            "id": task_id,
            "milestone_id": milestone_id,
            "name": name,
            "description": description,
            "estimate_hours": estimate_hours,
            "assignee": assignee,
            "status": "pending",
            "subtasks": [],
            "created_at": now,
            "updated_at": now,
        }
        _TASKS[task_id] = task
        return task

    def get(self, task_id: str) -> dict[str, Any] | None:
        return _TASKS.get(task_id)

    def list(self, milestone_id: str | None = None) -> list[dict[str, Any]]:
        tasks = list(_TASKS.values())
        if milestone_id is not None:
            tasks = [t for t in tasks if t["milestone_id"] == milestone_id]
        return tasks

    def update_status(self, task_id: str, status: str) -> dict[str, Any] | None:
        task = _TASKS.get(task_id)
        if task is None:
            return None
        task["status"] = status
        task["updated_at"] = datetime.now(UTC).isoformat()
        return task

    def add_subtask(self, task_id: str, name: str) -> dict[str, Any] | None:
        task = _TASKS.get(task_id)
        if task is None:
            return None
        subtask = {"id": str(uuid.uuid4()), "name": name, "done": False}
        task["subtasks"].append(subtask)
        task["updated_at"] = datetime.now(UTC).isoformat()
        return subtask
