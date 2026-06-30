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

_SCAFFOLD_BASE_ROOTS: tuple[Path, ...] = (Path("/tmp"),)


def _safe_scaffold_root(base_path: str) -> Path:
    """Resolve *base_path* and ensure it falls under an allowed scaffold root."""
    resolved = Path(base_path).resolve()
    for root in _SCAFFOLD_BASE_ROOTS:
        if str(resolved).startswith(str(root.resolve())):
            return resolved
    raise ValueError(
        f"base_path {base_path!r} is not within an allowed scaffold root. "
        f"Allowed roots: {[str(r) for r in _SCAFFOLD_BASE_ROOTS]}"
    )


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
            try:
                safe_base = _safe_scaffold_root(base_path)
            except ValueError as exc:
                return {
                    "id": job_id,
                    "status": "error",
                    "error": str(exc),
                    "created_at": now,
                    "updated_at": now,
                }
            root = safe_base / name
            for d in dirs:
                target = (root / d).resolve()
                if not str(target).startswith(str(root.resolve())):
                    continue  # skip any dir that would escape the scaffold root
                target.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(target))
            for fname, content in files.items():
                fpath = (root / fname).resolve()
                if not str(fpath).startswith(str(root.resolve())):
                    continue
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
