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


class RepoScaffolder:
    """Scaffold new repository or module directory structures."""

    def scaffold(
        self,
        name: str,
        description: str = "",
        base_path: str | None = None,
        extra_dirs: list[str] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        dirs = list(DEFAULT_DIRS) + (extra_dirs or [])
        files = {k: v.format(name=name, description=description) for k, v in DEFAULT_FILES.items()}

        created_dirs: list[str] = []
        created_files: list[str] = []

        if not dry_run and base_path:
            root = Path(base_path) / name
            for d in dirs:
                target = root / d
                target.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(target))
            for fname, content in files.items():
                fpath = root / fname
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_text(content)
                created_files.append(str(fpath))

        result: dict[str, Any] = {
            "id": job_id,
            "name": name,
            "description": description,
            "base_path": base_path,
            "dry_run": dry_run,
            "planned_dirs": dirs,
            "planned_files": list(files),
            "created_dirs": created_dirs,
            "created_files": created_files,
            "status": "completed",
            "created_at": now,
        }
        _SCAFFOLDS[job_id] = result
        return result

    def get(self, job_id: str) -> dict[str, Any] | None:
        return _SCAFFOLDS.get(job_id)

    def list(self) -> list[dict[str, Any]]:
        return list(_SCAFFOLDS.values())
