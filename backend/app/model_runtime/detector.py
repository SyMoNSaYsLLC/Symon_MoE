from __future__ import annotations

from pathlib import Path

from .registry import CONVERTER_REGISTRY, DETECTOR_REGISTRY, LOADER_REGISTRY, RUNTIME_REGISTRY
from .schemas import DetectionMatch, InspectResponse


def _normalize_files(path: str, files: list[str]) -> list[str]:
    if files:
        return [entry.lower() for entry in files]
    return [Path(path).name.lower()]


def _contains_any(items: list[str], tokens: tuple[str, ...]) -> bool:
    return any(any(token in item for token in tokens) for item in items)


def _extension_match(items: list[str], suffixes: tuple[str, ...]) -> bool:
    return any(item.endswith(suffixes) for item in items)


def _register_defaults() -> None:
    if DETECTOR_REGISTRY.names():
        return

    def by_ext(suffixes: tuple[str, ...], reason: str):
        def detector(_path: str, files: list[str]):
            if _extension_match(files, suffixes):
                return (0.95, [reason])
            return None

        return detector

    def by_token(tokens: tuple[str, ...], reason: str, confidence: float = 0.8):
        def detector(_path: str, files: list[str]):
            if _contains_any(files, tokens):
                return (confidence, [reason])
            return None

        return detector

    DETECTOR_REGISTRY.register("gguf", by_ext((".gguf",), "Found GGUF artifact"))
    DETECTOR_REGISTRY.register(
        "transformers",
        by_token(
            ("config.json", "tokenizer.json", "model.safetensors"),
            "Found Transformers metadata",
            confidence=0.99,
        ),
    )
    DETECTOR_REGISTRY.register(
        "diffusers",
        by_token(
            ("model_index.json", "unet", "vae", "scheduler"),
            "Found Diffusers pipeline files",
        ),
    )
    DETECTOR_REGISTRY.register(
        "peft",
        by_token(("adapter_config.json", "adapter_model", "lora"), "Found PEFT/LoRA adapter files"),
    )
    DETECTOR_REGISTRY.register(
        "sentence-transformers",
        by_token(
            ("sentence_bert_config", "modules.json", "sentence-transformers"),
            "Found sentence-transformers files",
        ),
    )
    DETECTOR_REGISTRY.register("onnx", by_ext((".onnx",), "Found ONNX graph"))
    DETECTOR_REGISTRY.register("coreml", by_ext((".mlmodel", ".mlpackage"), "Found CoreML model"))
    DETECTOR_REGISTRY.register("openvino", by_token(("openvino", ".xml", ".bin"), "Found OpenVINO IR assets"))
    DETECTOR_REGISTRY.register("mlx", by_token(("mlx", "weights.npz"), "Found MLX model files"))
    DETECTOR_REGISTRY.register(
        "tensorflow-keras",
        by_token(
            (".pb", ".h5", ".keras", ".ckpt.index", ".ckpt.data-"),
            "Found TensorFlow/Keras artifact",
            confidence=0.93,
        ),
    )
    DETECTOR_REGISTRY.register("pytorch-checkpoint", by_ext((".pt", ".pth", ".ckpt"), "Found PyTorch checkpoint"))
    DETECTOR_REGISTRY.register("safetensors", by_ext((".safetensors",), "Found safetensors checkpoint"))
    DETECTOR_REGISTRY.register("sklearn-joblib-pickle", by_ext((".joblib", ".pkl", ".pickle"), "Found scikit-learn serialized artifact"))

    LOADER_REGISTRY.register("gguf", "workers.gguf.worker:GGUFWorker")
    LOADER_REGISTRY.register("transformers", "workers.transformers.worker:TransformersWorker")
    LOADER_REGISTRY.register("diffusers", "workers.diffusers.worker:DiffusersWorker")
    LOADER_REGISTRY.register("peft", "workers.peft.worker:PEFTWorker")
    LOADER_REGISTRY.register("sentence-transformers", "workers.sentence_transformers.worker:SentenceTransformersWorker")
    LOADER_REGISTRY.register("onnx", "workers.onnx.worker:ONNXWorker")
    LOADER_REGISTRY.register("coreml", "workers.embedded.worker:EmbeddedWorker")
    LOADER_REGISTRY.register("openvino", "workers.embedded.worker:EmbeddedWorker")
    LOADER_REGISTRY.register("mlx", "workers.embedded.worker:EmbeddedWorker")
    LOADER_REGISTRY.register("tensorflow-keras", "workers.embedded.worker:EmbeddedWorker")
    LOADER_REGISTRY.register("pytorch-checkpoint", "workers.transformers.worker:TransformersWorker")
    LOADER_REGISTRY.register("safetensors", "workers.transformers.worker:TransformersWorker")
    LOADER_REGISTRY.register("sklearn-joblib-pickle", "workers.embedded.worker:EmbeddedWorker")

    CONVERTER_REGISTRY.register("gguf", "none")
    CONVERTER_REGISTRY.register("transformers", "convert:transformers-to-runtime")
    CONVERTER_REGISTRY.register("diffusers", "convert:diffusers-to-runtime")
    CONVERTER_REGISTRY.register("peft", "convert:merge-peft-adapter")
    CONVERTER_REGISTRY.register("sentence-transformers", "convert:sentence-transformers-export")
    CONVERTER_REGISTRY.register("onnx", "convert:onnx-optimize")
    CONVERTER_REGISTRY.register("coreml", "convert:coreml-export")
    CONVERTER_REGISTRY.register("openvino", "convert:openvino-optimize")
    CONVERTER_REGISTRY.register("mlx", "convert:mlx-export")
    CONVERTER_REGISTRY.register("tensorflow-keras", "convert:tensorflow-export")
    CONVERTER_REGISTRY.register("pytorch-checkpoint", "convert:pytorch-export")
    CONVERTER_REGISTRY.register("safetensors", "convert:safetensors-export")
    CONVERTER_REGISTRY.register("sklearn-joblib-pickle", "convert:sklearn-export")

    RUNTIME_REGISTRY.register("gguf", "llama.cpp")
    RUNTIME_REGISTRY.register("transformers", "transformers")
    RUNTIME_REGISTRY.register("diffusers", "diffusers")
    RUNTIME_REGISTRY.register("peft", "transformers")
    RUNTIME_REGISTRY.register("sentence-transformers", "sentence-transformers")
    RUNTIME_REGISTRY.register("onnx", "onnxruntime")
    RUNTIME_REGISTRY.register("coreml", "coreml")
    RUNTIME_REGISTRY.register("openvino", "openvino")
    RUNTIME_REGISTRY.register("mlx", "mlx")
    RUNTIME_REGISTRY.register("tensorflow-keras", "tensorflow")
    RUNTIME_REGISTRY.register("pytorch-checkpoint", "pytorch")
    RUNTIME_REGISTRY.register("safetensors", "pytorch")
    RUNTIME_REGISTRY.register("sklearn-joblib-pickle", "python-sklearn")


def inspect_model(path: str, files: list[str] | None = None) -> InspectResponse:
    _register_defaults()
    inspected_files = _normalize_files(path, files or [])

    matches: list[DetectionMatch] = []
    for detector_name in DETECTOR_REGISTRY.names():
        detector = DETECTOR_REGISTRY.get(detector_name)
        result = detector(path, inspected_files)
        if result is None:
            continue
        confidence, reasons = result
        matches.append(
            DetectionMatch(
                detector=detector_name,
                format=detector_name,
                family=detector_name,
                confidence=confidence,
                reasons=reasons,
                suggested_loader=LOADER_REGISTRY.get(detector_name),
                suggested_converter=CONVERTER_REGISTRY.get(detector_name),
                suggested_runtime=RUNTIME_REGISTRY.get(detector_name),
            )
        )

    if not matches:
        fallback = DetectionMatch(
            detector="unknown",
            format="unknown",
            family="unknown",
            confidence=0.1,
            reasons=["No known detector rule matched"],
            suggested_loader="workers.embedded.worker:EmbeddedWorker",
            suggested_converter="convert:manual",
            suggested_runtime="python",
        )
        return InspectResponse(selected=fallback, matches=[fallback])

    matches.sort(key=lambda item: item.confidence, reverse=True)
    return InspectResponse(selected=matches[0], matches=matches)
