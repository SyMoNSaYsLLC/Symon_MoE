"""Test execution orchestration for the building layer."""
from __future__ import annotations

import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_RUNS: dict[str, dict[str, Any]] = {}

# Allowlist of safe pytest flags. Values are the canonical constant strings
# used in commands — user input is only used as a lookup key, never as a value.
_SAFE_FLAGS: dict[str, str] = {f: f for f in (
    "-v", "-q", "-s", "--tb=short", "--tb=long", "--tb=no",
    "--no-header", "-x", "--maxfail=1", "--maxfail=2", "--maxfail=3",
    "--collect-only",
)}


def _validate_extra_args(args: list[str]) -> list[str]:
    """Return only canonical safe pytest flags from the allowlist.

    User input is used only as a dict key; the actual command argument is the
    constant value from *_SAFE_FLAGS*, breaking the user-input taint chain.
    """
    safe: list[str] = []
    for arg in args:
        canonical = _SAFE_FLAGS.get(arg)
        if canonical is None:
            raise ValueError(f"Disallowed pytest argument: {arg!r}")
        safe.append(canonical)
    return safe


class TestRunner:
    """Run the repository test suite and record results."""

    __test__ = False

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = (repo_root or Path(__file__).resolve().parents[4]).resolve()

    def run(self, extra_args: list[str] | None = None) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        # The test path is always the fixed repo-local tests directory.
        test_dir = self._root / "tests"

        try:
            safe_extra = _validate_extra_args(extra_args or [])
        except ValueError as exc:
            return {
                "id": run_id,
                "status": "error",
                "error": str(exc),
                "created_at": now,
                "updated_at": now,
            }

        cmd = ["python", "-m", "pytest", str(test_dir), "--tb=short", "-q"] + safe_extra

        record: dict[str, Any] = {
            "id": run_id,
            "command": cmd,
            "test_path": str(test_dir),
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
