from __future__ import annotations

from importlib import import_module

from .registry import WORKER_REGISTRY
from .schemas import WorkerDescriptor


WORKER_SPECS = {
    "transformers": "backend.app.workers.transformers.worker:TransformersWorker",
    "diffusers": "backend.app.workers.diffusers.worker:DiffusersWorker",
    "gguf": "backend.app.workers.gguf.worker:GGUFWorker",
    "onnx": "backend.app.workers.onnx.worker:ONNXWorker",
    "peft": "backend.app.workers.peft.worker:PEFTWorker",
    "sentence_transformers": "backend.app.workers.sentence_transformers.worker:SentenceTransformersWorker",
    "embedded": "backend.app.workers.embedded.worker:EmbeddedWorker",
}


def _register_workers() -> None:
    if WORKER_REGISTRY.names():
        return
    for name, spec in WORKER_SPECS.items():
        WORKER_REGISTRY.register(name, spec)


def _resolve_descriptor(name: str, spec: str) -> WorkerDescriptor:
    module_name, class_name = spec.split(":", maxsplit=1)
    module = import_module(module_name)
    worker_type = getattr(module, class_name)
    return WorkerDescriptor(
        name=name,
        module=spec,
        interface={
            "run": "dict -> dict",
            "capabilities": list(getattr(worker_type, "capabilities", [])),
        },
    )


def load_worker(worker_name: str):
    _register_workers()
    spec = WORKER_REGISTRY.get(worker_name)
    module_name, class_name = spec.split(":", maxsplit=1)
    module = import_module(module_name)
    worker_type = getattr(module, class_name)
    return worker_type()


def list_workers() -> list[WorkerDescriptor]:
    _register_workers()
    return [_resolve_descriptor(name, WORKER_REGISTRY.get(name)) for name in WORKER_REGISTRY.names()]
