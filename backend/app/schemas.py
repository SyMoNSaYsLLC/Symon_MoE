from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class ConversionJobRequest(APIModel):
    model_name: str = Field(..., description="Folder name under models/raw")
    architecture: Literal["llama", "qwen2", "mistral", "diffusion"]
    outtype: str = "q8_0"
    output_name: str | None = None
    source_file: str | None = None


class MigrationSource(APIModel):
    architecture: Literal["llama", "qwen2", "mistral"]
    artifact_name: str


class MigrationJobRequest(APIModel):
    sources: list[MigrationSource] = Field(..., min_length=3, max_length=3)
    target_name: str = "symoneural-migrated.gguf"


class JobRecord(APIModel):
    id: str
    job_type: Literal["conversion", "migration", "llm"]
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime
    updated_at: datetime
    worker: str | None = None
    request: dict
    logs: list[str] = Field(default_factory=list)
    result: dict | None = None
    error: str | None = None
