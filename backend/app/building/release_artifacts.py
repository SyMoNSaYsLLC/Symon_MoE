"""Release artifact creation for the building layer."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_RELEASES: dict[str, dict[str, Any]] = {}

RELEASE_TYPES = ("stable", "rc", "nightly", "hotfix")


class ReleaseArtifactCreator:
    """Assemble and register release artifacts."""

    def create(
        self,
        version: str,
        release_type: str = "stable",
        artifacts: list[dict[str, str]] | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        if release_type not in RELEASE_TYPES:
            raise ValueError(f"release_type must be one of {sorted(RELEASE_TYPES)}")
        release_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        release: dict[str, Any] = {
            "id": release_id,
            "version": version,
            "release_type": release_type,
            "artifacts": artifacts or [],
            "notes": notes,
            "status": "draft",
            "checksums": {},
            "created_at": now,
            "updated_at": now,
        }
        _RELEASES[release_id] = release
        return release

    def attach_artifact(
        self, release_id: str, name: str, path: str, artifact_type: str = "binary"
    ) -> dict[str, Any] | None:
        release = _RELEASES.get(release_id)
        if release is None:
            return None
        entry: dict[str, str] = {"name": name, "path": path, "type": artifact_type}
        if Path(path).exists():
            import hashlib
            sha256 = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            entry["sha256"] = sha256
            release["checksums"][name] = sha256
        release["artifacts"].append(entry)
        release["updated_at"] = datetime.now(UTC).isoformat()
        return release

    def publish(self, release_id: str) -> dict[str, Any] | None:
        release = _RELEASES.get(release_id)
        if release is None:
            return None
        release["status"] = "published"
        release["updated_at"] = datetime.now(UTC).isoformat()
        return release

    def get(self, release_id: str) -> dict[str, Any] | None:
        return _RELEASES.get(release_id)

    def list(self, release_type: str | None = None) -> list[dict[str, Any]]:
        releases = list(_RELEASES.values())
        if release_type is not None:
            releases = [r for r in releases if r["release_type"] == release_type]
        return releases
