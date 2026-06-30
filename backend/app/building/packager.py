"""Package creation for the building layer."""
from __future__ import annotations

import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_PACKAGES: dict[str, dict[str, Any]] = {}

SUPPORTED_FORMATS = ("wheel", "sdist", "tarball", "zip")


def _safe_dir(path_str: str, allowed_roots: tuple[Path, ...]) -> Path:
    """Resolve *path_str* and raise ValueError if not inside any of *allowed_roots*."""
    resolved = Path(path_str).resolve()
    for root in allowed_roots:
        if str(resolved).startswith(str(root.resolve())):
            return resolved
    raise ValueError(
        f"Path {path_str!r} is not within an allowed directory. "
        f"Allowed roots: {[str(r) for r in allowed_roots]}"
    )


class Packager:
    """Create distributable packages from source."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = (repo_root or Path(__file__).resolve().parents[4]).resolve()

    def create(
        self,
        package_name: str,
        source_dir: str,
        fmt: str = "wheel",
        output_dir: str | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError(f"fmt must be one of {sorted(SUPPORTED_FORMATS)}")

        out_path = output_dir or str(self._root / "dist")

        # Validate both directories are within the repo root before any I/O
        try:
            safe_source = _safe_dir(source_dir, (self._root,))
            safe_output = _safe_dir(out_path, (self._root,))
        except ValueError:
            raise

        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        record: dict[str, Any] = {
            "id": job_id,
            "package_name": package_name,
            "source_dir": str(safe_source),
            "format": fmt,
            "output_dir": str(safe_output),
            "dry_run": dry_run,
            "status": "queued",
            "artifacts": [],
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        _PACKAGES[job_id] = record

        if dry_run:
            record["status"] = "dry_run_complete"
            record["updated_at"] = datetime.now(UTC).isoformat()
            return record

        try:
            if fmt in ("wheel", "sdist"):
                cmd = ["python", "-m", "build", "--outdir", str(safe_output)]
                if fmt == "wheel":
                    cmd.append("--wheel")
                else:
                    cmd.append("--sdist")
                proc = subprocess.run(  # noqa: S603
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(safe_source),
                )
                record["return_code"] = proc.returncode
                if proc.returncode == 0:
                    record["status"] = "completed"
                    record["artifacts"] = [
                        str(p) for p in safe_output.iterdir() if p.is_file()
                    ]
                else:
                    record["status"] = "failed"
                    record["error"] = proc.stderr
            elif fmt == "tarball":
                dest = safe_output / f"{package_name}.tar.gz"
                safe_output.mkdir(parents=True, exist_ok=True)
                shutil.make_archive(str(dest.with_suffix("").with_suffix("")), "gztar", str(safe_source))
                record["status"] = "completed"
                record["artifacts"] = [str(dest)]
            elif fmt == "zip":
                dest = safe_output / package_name
                safe_output.mkdir(parents=True, exist_ok=True)
                shutil.make_archive(str(dest), "zip", str(safe_source))
                record["status"] = "completed"
                record["artifacts"] = [str(dest) + ".zip"]
        except Exception as exc:  # pragma: no cover
            record["status"] = "error"
            record["error"] = str(exc)

        record["updated_at"] = datetime.now(UTC).isoformat()
        return record

    def get(self, job_id: str) -> dict[str, Any] | None:
        return _PACKAGES.get(job_id)

    def list(self) -> list[dict[str, Any]]:
        return list(_PACKAGES.values())
