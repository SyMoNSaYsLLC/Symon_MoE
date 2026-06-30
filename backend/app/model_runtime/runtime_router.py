from __future__ import annotations

from ..embedded.device_profiles.registry import list_profiles
from .converter_router import select_converter
from .schemas import CapabilitiesResponse, RouteRequest, RuntimeDecision
from .task_router import pipeline_for_task


def _worker_for_runtime(runtime: str) -> str:
    mapping = {
        "llama.cpp": "gguf",
        "transformers": "transformers",
        "diffusers": "diffusers",
        "sentence-transformers": "sentence_transformers",
        "onnxruntime": "onnx",
        "pytorch": "transformers",
        "openvino": "embedded",
        "coreml": "embedded",
        "mlx": "embedded",
        "tensorflow": "embedded",
        "python-sklearn": "embedded",
    }
    return mapping.get(runtime, "embedded")


def route_runtime(request: RouteRequest) -> RuntimeDecision:
    pipeline = pipeline_for_task(request.task)
    runtime = request.target_runtime or request.inspection.suggested_runtime
    worker = _worker_for_runtime(runtime)
    converter = select_converter(request)

    packaging = None
    notes: list[str] = []
    if request.target_device_profile:
        if request.target_device_profile not in set(list_profiles()):
            raise ValueError(f"Unknown device profile: {request.target_device_profile}")
        packaging = "embedded-package"
        notes.append("Device profile controls deployment packaging")

    return RuntimeDecision(
        task=request.task,
        pipeline=pipeline,
        loader=request.inspection.suggested_loader,
        converter=converter,
        runtime=runtime,
        worker=worker,
        device_profile=request.target_device_profile,
        deployment_packaging=packaging,
        notes=notes,
    )


def runtime_capabilities() -> CapabilitiesResponse:
    return CapabilitiesResponse(
        formats=[
            "gguf",
            "transformers",
            "diffusers",
            "peft",
            "sentence-transformers",
            "onnx",
            "coreml",
            "openvino",
            "mlx",
            "tensorflow-keras",
            "pytorch-checkpoint",
            "safetensors",
            "sklearn-joblib-pickle",
        ],
        runtimes=[
            "llama.cpp",
            "transformers",
            "diffusers",
            "sentence-transformers",
            "onnxruntime",
            "pytorch",
            "tensorflow",
            "openvino",
            "coreml",
            "mlx",
            "python-sklearn",
        ],
        tasks=[
            "chat",
            "embeddings",
            "text-to-image",
            "image-to-image",
            "classification",
            "inference",
            "conversion",
            "deployment",
        ],
    )
