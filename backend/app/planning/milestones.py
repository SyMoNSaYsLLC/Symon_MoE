"""Milestone tracking for the planning layer."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

VALID_STATUSES = {"pending", "in_progress", "completed", "blocked"}

_MILESTONES: dict[str, dict[str, Any]] = {}


class MilestoneTracker:
    """Create and track project milestones."""

    def create(
        self,
        roadmap_id: str,
        name: str,
        target_date: str | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        milestone_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        milestone = {
            "id": milestone_id,
            "roadmap_id": roadmap_id,
            "name": name,
            "description": description,
            "target_date": target_date,
            "status": "pending",
            "tasks": [],
            "created_at": now,
            "updated_at": now,
        }
        _MILESTONES[milestone_id] = milestone
        return milestone

    def get(self, milestone_id: str) -> dict[str, Any] | None:
        return _MILESTONES.get(milestone_id)

    def list(self, roadmap_id: str | None = None) -> list[dict[str, Any]]:
        milestones = list(_MILESTONES.values())
        if roadmap_id is not None:
            milestones = [m for m in milestones if m["roadmap_id"] == roadmap_id]
        return milestones

    def update_status(self, milestone_id: str, status: str) -> dict[str, Any] | None:
        if status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        milestone = _MILESTONES.get(milestone_id)
        if milestone is None:
            return None
        milestone["status"] = status
        milestone["updated_at"] = datetime.now(UTC).isoformat()
        return milestone
