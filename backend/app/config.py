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

# ---------------------------------------------------------------------------
# SQLite database
# ---------------------------------------------------------------------------
DB_PATH = Path(os.getenv("SYMON_DB_PATH", str(MODELS_ROOT / "symoneural.db"))).resolve()

# ---------------------------------------------------------------------------
# Mining feature flag
# ---------------------------------------------------------------------------
MINING_ENABLED: bool = os.getenv("SYMON_MINING_ENABLED", "false").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Embedded / Yocto build workspace
# ---------------------------------------------------------------------------
DEFAULT_EMBEDDED_BUILD_ROOT = REPO_ROOT / "embedded_builds"
EMBEDDED_BUILD_ROOT = Path(
    os.getenv("SYMON_EMBEDDED_BUILD_ROOT", str(DEFAULT_EMBEDDED_BUILD_ROOT))
).resolve()

# ---------------------------------------------------------------------------
# Web terminal
# ---------------------------------------------------------------------------
TERMINAL_SHELL: str = os.getenv("SYMON_TERMINAL_SHELL", "/bin/bash")

# ---------------------------------------------------------------------------
# Hardware throttle limits (percentage 0-100)
# ---------------------------------------------------------------------------
HARDWARE_THROTTLE_CPU_LIMIT: float = float(os.getenv("SYMON_CPU_LIMIT", "90"))
HARDWARE_THROTTLE_GPU_LIMIT: float = float(os.getenv("SYMON_GPU_LIMIT", "90"))

SCOPE_DECISIONS = {
    "migration_v1_architectures": ["llama", "qwen2", "mistral"],
    "frontend_location": "inside_this_repository:/frontend",
    "cloudflare_handles_auth": False,
}
