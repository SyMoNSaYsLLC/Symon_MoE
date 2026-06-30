from __future__ import annotations

from .registry import TASK_PIPELINE_REGISTRY


def _register_task_pipelines() -> None:
    if TASK_PIPELINE_REGISTRY.names():
        return
    TASK_PIPELINE_REGISTRY.register("chat", "llm-inference")
    TASK_PIPELINE_REGISTRY.register("embeddings", "embedding-inference")
    TASK_PIPELINE_REGISTRY.register("text-to-image", "diffusion-generation")
    TASK_PIPELINE_REGISTRY.register("image-to-image", "diffusion-generation")
    TASK_PIPELINE_REGISTRY.register("classification", "general-inference")
    TASK_PIPELINE_REGISTRY.register("inference", "general-inference")
    TASK_PIPELINE_REGISTRY.register("conversion", "model-conversion")
    TASK_PIPELINE_REGISTRY.register("deployment", "embedded-deployment")


def pipeline_for_task(task: str) -> str:
    _register_task_pipelines()
    try:
        return TASK_PIPELINE_REGISTRY.get(task)
    except KeyError:
        return "general-inference"
