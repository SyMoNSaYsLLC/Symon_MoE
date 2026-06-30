# Model Runtime Architecture

## Overview

This first-pass layer separates model inspection, task routing, runtime selection, and worker execution.

### Core rule chain

1. Task decides the pipeline.
2. Files decide the loader/converter.
3. Runtime decides execution.
4. Device profile decides deployment packaging.
5. Workers perform the actual work.

## New backend modules

- `backend/app/model_runtime/detector.py` — file-based model inspection and format detection.
- `backend/app/model_runtime/registry.py` — plugin-style registries for detectors, loaders, converters, runtimes, and tasks.
- `backend/app/model_runtime/task_router.py` — task-to-pipeline mapping.
- `backend/app/model_runtime/converter_router.py` — conversion decision layer.
- `backend/app/model_runtime/runtime_router.py` — runtime and worker routing.
- `backend/app/model_runtime/worker_loader.py` — worker registration and dynamic loading.
- `backend/app/model_runtime/schemas.py` — clean Pydantic contracts.

## API endpoints

- `POST /model-runtime/inspect`
- `POST /model-runtime/route`
- `GET /model-runtime/capabilities`
- `GET /model-runtime/workers`

## Supported detection families

- GGUF
- Hugging Face Transformers
- Diffusers / Stable Diffusion
- PEFT / LoRA
- sentence-transformers
- ONNX
- CoreML
- OpenVINO
- MLX
- TensorFlow / Keras
- PyTorch raw checkpoints
- safetensors
- scikit-learn joblib/pickle

## Notes

- Worker modules are stubs with explicit interfaces.
- TODO markers identify intentionally incomplete runtime execution details.
