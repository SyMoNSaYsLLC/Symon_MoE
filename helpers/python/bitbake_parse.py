from __future__ import annotations

from pathlib import Path


def parse_bitbake_log(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {"errors": [], "warnings": [], "timings": []}

    errors, warnings = [], []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "error" in line.lower():
            errors.append(line)
        if "warning" in line.lower():
            warnings.append(line)
    return {"errors": errors, "warnings": warnings, "timings": []}
