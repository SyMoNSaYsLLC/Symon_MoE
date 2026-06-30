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
    """Create distributable packages from source."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = repo_root or Path(__file__).resolve().parents[4]

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

        job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        out_path = output_dir or str(self._root / "dist")

        record: dict[str, Any] = {
            "id": job_id,
            "package_name": package_name,
            "source_dir": source_dir,
            "format": fmt,
            "output_dir": out_path,
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
                cmd = ["python", "-m", "build", "--outdir", out_path]
                if fmt == "wheel":
                    cmd.append("--wheel")
                else:
                    cmd.append("--sdist")
                proc = subprocess.run(  # noqa: S603
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=source_dir,
                )
                record["return_code"] = proc.returncode
                if proc.returncode == 0:
                    record["status"] = "completed"
                    record["artifacts"] = [
                        str(p) for p in Path(out_path).iterdir() if p.is_file()
                    ]
                else:
                    record["status"] = "failed"
                    record["error"] = proc.stderr
            elif fmt == "tarball":
                dest = Path(out_path) / f"{package_name}.tar.gz"
                Path(out_path).mkdir(parents=True, exist_ok=True)
                shutil.make_archive(str(dest.with_suffix("").with_suffix("")), "gztar", source_dir)
                record["status"] = "completed"
                record["artifacts"] = [str(dest)]
            elif fmt == "zip":
                dest = Path(out_path) / package_name
                Path(out_path).mkdir(parents=True, exist_ok=True)
                shutil.make_archive(str(dest), "zip", source_dir)
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
