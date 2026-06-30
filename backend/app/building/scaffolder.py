"""Repository scaffolding for the building layer."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SCAFFOLDS: dict[str, dict[str, Any]] = {}

DEFAULT_DIRS = ("src", "tests", "docs", ".github/workflows")
DEFAULT_FILES: dict[str, str] = {
    "README.md": "# {name}\n\n{description}\n",
    ".gitignore": "__pycache__/\n*.pyc\n.env\ndist/\nbuild/\n",
    "requirements.txt": "# Add dependencies here\n",
}

# Scaffolding is always a planning/dry-run operation from the public API.
# Actual on-disk creation is only performed when called from internal code
# with an explicitly trusted root (never from user-supplied paths).
_TRUSTED_SCAFFOLD_ROOT: Path = Path("/tmp/symon_scaffolds")


class RepoScaffolder:
    """Scaffold new repository or module directory structures.

    The public ``scaffold()`` method always runs as a *dry-run plan*.
    Use ``scaffold_to_disk()`` (internal) for actual file creation, which is
    restricted to the trusted internal scaffold root.
    """

    def scaffold(
        self,
        name: str,
        description: str = "",
        extra_dirs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Plan a scaffold (always dry-run, no file I/O)."""
        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        dirs = list(DEFAULT_DIRS) + (extra_dirs or [])
        files = {k: v.format(name=name, description=description) for k, v in DEFAULT_FILES.items()}

        result: dict[str, Any] = {
            "id": job_id,
            "name": name,
            "description": description,
            "dry_run": True,
            "planned_dirs": dirs,
            "planned_files": list(files),
            "created_dirs": [],
            "created_files": [],
            "status": "planned",
            "created_at": now,
        }
        _SCAFFOLDS[job_id] = result
        return result

    def scaffold_to_disk(self, job_id: str) -> dict[str, Any] | None:
        """Execute a previously planned scaffold into the trusted internal root."""
        plan = _SCAFFOLDS.get(job_id)
        if plan is None:
            return None
        if plan.get("status") != "planned":
            return plan

        name = plan["name"]
        description = plan["description"]
        dirs = plan["planned_dirs"]
        files = {k: v.format(name=name, description=description) for k, v in DEFAULT_FILES.items()}

        root = (_TRUSTED_SCAFFOLD_ROOT / name).resolve()
        # Ensure root is still within the trusted base (defence against symlink attacks).
        if not str(root).startswith(str(_TRUSTED_SCAFFOLD_ROOT.resolve())):
            plan["status"] = "error"
            plan["error"] = "Invalid scaffold name"
            return plan

        created_dirs: list[str] = []
        created_files: list[str] = []

        for d in dirs:
            target = (root / d).resolve()
            if str(target).startswith(str(root)):
                target.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(target))

        for fname, content in files.items():
            fpath = (root / fname).resolve()
            if str(fpath).startswith(str(root)):
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_text(content)
                created_files.append(str(fpath))

        plan["created_dirs"] = created_dirs
        plan["created_files"] = created_files
        plan["dry_run"] = False
        plan["status"] = "completed"
        return plan

    def get(self, job_id: str) -> dict[str, Any] | None:
        return _SCAFFOLDS.get(job_id)

    def list(self) -> list[dict[str, Any]]:
        return list(_SCAFFOLDS.values())
