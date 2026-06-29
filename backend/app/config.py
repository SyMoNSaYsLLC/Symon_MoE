from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODELS_ROOT = REPO_ROOT / "frontend" / "models"
MODELS_ROOT = Path(os.getenv("SYMON_MODELS_ROOT", str(DEFAULT_MODELS_ROOT))).resolve()
ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "SYMON_ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if origin.strip()
)
RAW_MODELS_DIR = MODELS_ROOT / "raw"
CONVERTED_MODELS_DIR = MODELS_ROOT / "converted"
MIGRATED_MODELS_DIR = MODELS_ROOT / "migrated"
METADATA_PATH = MODELS_ROOT / "metadata.json"

ORCHESTRATION_CONVERTER = REPO_ROOT / "orchestration" / "convert.py"

SUPPORTED_ARCHITECTURES = ("llama", "qwen2", "mistral", "diffusion")
SUPPORTED_MIGRATION_COMBINATIONS = (
    ("llama", "qwen2", "mistral"),
)

SCOPE_DECISIONS = {
    "migration_v1_architectures": ["llama", "qwen2", "mistral"],
    "frontend_location": "inside_this_repository:/frontend",
    "cloudflare_handles_auth": False,
}
