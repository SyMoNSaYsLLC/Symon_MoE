from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PROFILE_DIR = Path(__file__).resolve().parent


def _profile_paths(profile_dir: Path) -> list[Path]:
    return sorted(path for path in profile_dir.glob("*.json") if path.is_file())


def list_profiles(profile_dir: Path | None = None) -> list[str]:
    base = profile_dir or DEFAULT_PROFILE_DIR
    return [path.stem for path in _profile_paths(base)]


def get_profile(name: str, profile_dir: Path | None = None) -> dict:
    base = profile_dir or DEFAULT_PROFILE_DIR
    profile_path = base / f"{name}.json"
    if not profile_path.exists():
        raise KeyError(f"Unknown device profile: {name}")
    return json.loads(profile_path.read_text(encoding="utf-8"))
