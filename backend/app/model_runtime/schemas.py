from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RuntimeModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class InspectRequest(RuntimeModel):
    path: str = Field(..., description="File or folder path to inspect")
    files: list[str] = Field(default_factory=list, description="Optional file listing for virtual inspection")


class DetectionMatch(RuntimeModel):
    detector: str
    format: str
    family: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    suggested_loader: str
    suggested_converter: str | None = None
    suggested_runtime: str


class InspectResponse(RuntimeModel):
    selected: DetectionMatch
    matches: list[DetectionMatch]


class RouteRequest(RuntimeModel):
    task: Literal[
        "chat",
        "embeddings",
        "text-to-image",
        "image-to-image",
        "classification",
        "inference",
        "conversion",
        "deployment",
    ] = "inference"
    inspection: DetectionMatch
    target_runtime: str | None = None
    target_device_profile: str | None = None


class RuntimeDecision(RuntimeModel):
    task: str
    pipeline: str
    loader: str
    converter: str | None = None
    runtime: str
    worker: str
    device_profile: str | None = None
    deployment_packaging: str | None = None
    notes: list[str] = Field(default_factory=list)


class CapabilitiesResponse(RuntimeModel):
    formats: list[str]
    runtimes: list[str]
    tasks: list[str]


class WorkerDescriptor(RuntimeModel):
    name: str
    module: str
    interface: dict[str, Any]
