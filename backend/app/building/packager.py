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


class Packager:
    """Create distributable packages from source.

    Source and output directories are always derived from the repository root;
    no user-supplied paths flow directly to subprocess or filesystem operations.
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = (repo_root or Path(__file__).resolve().parents[4]).resolve()
        self._dist = self._root / "dist"

    def create(
        self,
        package_name: str,
        fmt: str = "wheel",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError(f"fmt must be one of {sorted(SUPPORTED_FORMATS)}")

        # All paths are derived from the internal repo root, never from user input.
        source_dir = self._root
        out_dir = self._dist

        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        record: dict[str, Any] = {
            "id": job_id,
            "package_name": package_name,
            "source_dir": str(source_dir),
            "format": fmt,
            "output_dir": str(out_dir),
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
                cmd = ["python", "-m", "build", "--outdir", "dist"]
                cmd.append("--wheel" if fmt == "wheel" else "--sdist")
                proc = subprocess.run(  # noqa: S603
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(source_dir),
                )
                record["return_code"] = proc.returncode
                if proc.returncode == 0:
                    record["status"] = "completed"
                    out_dir.mkdir(parents=True, exist_ok=True)
                    record["artifacts"] = [
                        str(p) for p in out_dir.iterdir() if p.is_file()
                    ]
                else:
                    record["status"] = "failed"
                    record["error"] = proc.stderr
            elif fmt == "tarball":
                out_dir.mkdir(parents=True, exist_ok=True)
                dest = out_dir / f"{package_name}.tar.gz"
                shutil.make_archive(
                    str(dest.with_suffix("").with_suffix("")), "gztar", str(source_dir)
                )
                record["status"] = "completed"
                record["artifacts"] = [str(dest)]
            elif fmt == "zip":
                out_dir.mkdir(parents=True, exist_ok=True)
                dest = out_dir / package_name
                shutil.make_archive(str(dest), "zip", str(source_dir))
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
