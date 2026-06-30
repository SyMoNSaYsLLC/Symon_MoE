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

DB_PATH = Path(os.getenv("DB_PATH", str(MODELS_ROOT / "symoneural.db"))).resolve()
MINING_ENABLED = os.getenv("MINING_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
EMBEDDED_BUILD_ROOT = Path(
    os.getenv("EMBEDDED_BUILD_ROOT", str(REPO_ROOT / "embedded" / "workspace"))
).resolve()
TERMINAL_SHELL = os.getenv("TERMINAL_SHELL", "/bin/bash")
HARDWARE_THROTTLE_CPU_LIMIT = float(os.getenv("HARDWARE_THROTTLE_CPU_LIMIT", "95"))
HARDWARE_THROTTLE_GPU_LIMIT = float(os.getenv("HARDWARE_THROTTLE_GPU_LIMIT", "95"))

PLANNING_DATA_DIR = Path(
    os.getenv("SYMON_PLANNING_DIR", str(MODELS_ROOT / "planning"))
).resolve()
BUILDING_OUTPUT_DIR = Path(
    os.getenv("SYMON_BUILDING_DIR", str(REPO_ROOT / "dist"))
).resolve()

SCOPE_DECISIONS = {
    "migration_v1_architectures": ["llama", "qwen2", "mistral"],
    "frontend_location": "inside_this_repository:/frontend",
    "cloudflare_handles_auth": False,
}
