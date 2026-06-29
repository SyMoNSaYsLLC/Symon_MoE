from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import (
    CONVERTED_MODELS_DIR,
    METADATA_PATH,
    MIGRATED_MODELS_DIR,
    RAW_MODELS_DIR,
)


def ensure_storage_contract() -> None:
    for directory in (RAW_MODELS_DIR, CONVERTED_MODELS_DIR, MIGRATED_MODELS_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    if not METADATA_PATH.exists():
        METADATA_PATH.write_text(json.dumps({"models": {}, "artifacts": {}}, indent=2), encoding="utf-8")


def load_metadata() -> dict[str, Any]:
    ensure_storage_contract()
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


def save_metadata(metadata: dict[str, Any]) -> None:
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")


def _raw_model_required_files(model_path: Path) -> list[str]:
    has_config = (model_path / "config.json").exists()
    has_safetensors = any(model_path.glob("*.safetensors"))
    required = []
    if not has_config:
        required.append("config.json (required for LLM conversion)")
    if not has_safetensors:
        required.append("*.safetensors (required for diffusion conversion)")
    return required


def scan_models() -> dict[str, Any]:
    ensure_storage_contract()
    metadata = load_metadata()

    raw_models = []
    for model_dir in sorted([p for p in RAW_MODELS_DIR.iterdir() if p.is_dir()]):
        has_config = (model_dir / "config.json").exists()
        has_safetensors = any(model_dir.glob("*.safetensors"))
        missing = _raw_model_required_files(model_dir)
        raw_models.append(
            {
                "name": model_dir.name,
                "path": str(model_dir),
                "missing_requirements": missing,
                "ready_for_llm": has_config,
                "ready_for_diffusion": has_safetensors,
            }
        )

    converted_artifacts = [
        {"name": file.name, "path": str(file)}
        for file in sorted(CONVERTED_MODELS_DIR.glob("*.gguf"))
        if file.is_file()
    ]

    migrated_artifacts = [
        {"name": file.name, "path": str(file)}
        for file in sorted(MIGRATED_MODELS_DIR.glob("*.gguf"))
        if file.is_file()
    ]

    return {
        "storage_contract": {
            "raw_models_dir": str(RAW_MODELS_DIR),
            "converted_models_dir": str(CONVERTED_MODELS_DIR),
            "migrated_models_dir": str(MIGRATED_MODELS_DIR),
            "metadata_file": str(METADATA_PATH),
        },
        "raw_models": raw_models,
        "converted_artifacts": converted_artifacts,
        "migrated_artifacts": migrated_artifacts,
        "metadata": metadata,
    }
