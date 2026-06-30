"""Test execution orchestration for the building layer."""
from __future__ import annotations

import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_RUNS: dict[str, dict[str, Any]] = {}


def _safe_child_path(root: Path, relative: str) -> Path:
    """Resolve *relative* within *root* and raise ValueError on path traversal."""
    resolved = (root / relative).resolve()
    if not str(resolved).startswith(str(root.resolve())):
        raise ValueError(f"test_path must be within the repository root: {relative!r}")
    return resolved


class TestRunner:
    """Run the repository test suite and record results."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = (repo_root or Path(__file__).resolve().parents[4]).resolve()

    def run(
        self,
        test_path: str = "tests",
        extra_args: list[str] | None = None,
    ) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        try:
            target = _safe_child_path(self._root, test_path)
        except ValueError as exc:
            return {
                "id": run_id,
                "status": "error",
                "error": str(exc),
                "created_at": now,
                "updated_at": now,
            }

        cmd = ["python", "-m", "pytest", str(target), "--tb=short", "-q"] + (extra_args or [])

        record: dict[str, Any] = {
            "id": run_id,
            "command": cmd,
            "test_path": str(target),
            "status": "running",
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "created_at": now,
            "updated_at": now,
        }
        _RUNS[run_id] = record

        try:
            proc = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self._root),
            )
            record["return_code"] = proc.returncode
            record["stdout"] = proc.stdout
            record["stderr"] = proc.stderr
            record["status"] = "passed" if proc.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            record["status"] = "timeout"
            record["error"] = "Test run timed out after 300 seconds"
        except Exception as exc:  # pragma: no cover
            record["status"] = "error"
            record["error"] = str(exc)

        record["updated_at"] = datetime.now(UTC).isoformat()
        return record

    def get(self, run_id: str) -> dict[str, Any] | None:
        return _RUNS.get(run_id)

    def list(self) -> list[dict[str, Any]]:
        return list(_RUNS.values())
