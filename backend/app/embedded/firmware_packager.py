from __future__ import annotations

import hashlib
from pathlib import Path


def build_manifest(image_dir: Path) -> list[dict]:
    if not image_dir.exists():
        return []
    artifacts = []
    for file in sorted(image_dir.glob("*")):
        if not file.is_file():
            continue
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        artifacts.append({"name": file.name, "path": str(file), "sha256": digest, "size": file.stat().st_size})
    return artifacts
