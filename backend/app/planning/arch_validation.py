"""Architecture validation checklists for the planning layer."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

DEFAULT_CHECKLIST_ITEMS: list[dict[str, Any]] = [
    {"id": "sep-01", "category": "separation", "item": "Planning layer only decides – does not execute builds"},
    {"id": "sep-02", "category": "separation", "item": "Building layer only scaffolds/builds – does not run models"},
    {"id": "sep-03", "category": "separation", "item": "Runtime layer only executes models – does not scaffold"},
    {"id": "sep-04", "category": "separation", "item": "Embedded layer only deploys artifacts – does not generate code"},
    {"id": "api-01", "category": "api", "item": "All new endpoints use /api/<layer>/<resource> prefix convention"},
    {"id": "api-02", "category": "api", "item": "Pydantic models used for all request/response schemas"},
    {"id": "api-03", "category": "api", "item": "HTTPException raised with appropriate status codes"},
    {"id": "sec-01", "category": "security", "item": "File paths validated with SAFE_NAME_PATTERN before use"},
    {"id": "sec-02", "category": "security", "item": "No secrets committed to repository"},
    {"id": "sec-03", "category": "security", "item": "CORS origins configured via environment variable"},
    {"id": "perf-01", "category": "performance", "item": "Hardware throttle check performed before heavy jobs"},
    {"id": "test-01", "category": "testing", "item": "Unit tests added for all new modules"},
    {"id": "test-02", "category": "testing", "item": "Existing tests pass after changes"},
    {"id": "doc-01", "category": "documentation", "item": "README updated for significant feature additions"},
]

_VALIDATIONS: dict[str, dict[str, Any]] = {}


class ArchValidator:
    """Run architecture validation checklists against a planned change."""

    def start(self, change_description: str, custom_items: list[str] | None = None) -> dict[str, Any]:
        validation_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        items = [dict(i) | {"checked": False} for i in DEFAULT_CHECKLIST_ITEMS]
        if custom_items:
            for idx, text in enumerate(custom_items):
                items.append(
                    {
                        "id": f"custom-{idx + 1:02d}",
                        "category": "custom",
                        "item": text,
                        "checked": False,
                    }
                )
        validation = {
            "id": validation_id,
            "change_description": change_description,
            "items": items,
            "passed": False,
            "created_at": now,
            "updated_at": now,
        }
        _VALIDATIONS[validation_id] = validation
        return validation

    def check_item(self, validation_id: str, item_id: str, checked: bool) -> dict[str, Any] | None:
        validation = _VALIDATIONS.get(validation_id)
        if validation is None:
            return None
        for item in validation["items"]:
            if item["id"] == item_id:
                item["checked"] = checked
                break
        validation["passed"] = all(i["checked"] for i in validation["items"])
        validation["updated_at"] = datetime.now(UTC).isoformat()
        return validation

    def get(self, validation_id: str) -> dict[str, Any] | None:
        return _VALIDATIONS.get(validation_id)

    def list(self) -> list[dict[str, Any]]:
        return list(_VALIDATIONS.values())
