from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ConversionJobRequest(BaseModel):
    model_name: str = Field(..., description="Folder name under models/raw")
    architecture: Literal["llama", "qwen2", "mistral", "diffusion"]
    outtype: str = "q8_0"
    output_name: str | None = None
    source_file: str | None = None


class MigrationSource(BaseModel):
    architecture: Literal["llama", "qwen2", "mistral"]
    artifact_name: str


class MigrationJobRequest(BaseModel):
    sources: list[MigrationSource] = Field(..., min_length=3, max_length=3)
    target_name: str = "symoneural-migrated.gguf"


class JobRecord(BaseModel):
    id: str
    job_type: Literal["conversion", "migration"]
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime
    updated_at: datetime
    worker: str | None = None
    request: dict
    logs: list[str] = Field(default_factory=list)
    result: dict | None = None
    error: str | None = None
