"""Project roadmap generation for the planning layer."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any


_ROADMAPS: dict[str, dict[str, Any]] = {}


class RoadmapGenerator:
    """Generate and store project roadmaps."""

    def create(self, title: str, description: str, phases: list[str]) -> dict[str, Any]:
        roadmap_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        roadmap = {
            "id": roadmap_id,
            "title": title,
            "description": description,
            "phases": [
                {"name": phase, "status": "pending", "milestones": []}
                for phase in phases
            ],
            "created_at": now,
            "updated_at": now,
        }
        _ROADMAPS[roadmap_id] = roadmap
        return roadmap

    def get(self, roadmap_id: str) -> dict[str, Any] | None:
        return _ROADMAPS.get(roadmap_id)

    def list(self) -> list[dict[str, Any]]:
        return list(_ROADMAPS.values())

    def update_phase_status(
        self, roadmap_id: str, phase_name: str, status: str
    ) -> dict[str, Any] | None:
        roadmap = _ROADMAPS.get(roadmap_id)
        if roadmap is None:
            return None
        for phase in roadmap["phases"]:
            if phase["name"] == phase_name:
                phase["status"] = status
                roadmap["updated_at"] = datetime.now(UTC).isoformat()
                break
        return roadmap
