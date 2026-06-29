from __future__ import annotations

"""
tensor_lab.py — Tensor inspection and API-key-based model customisation router.

Exposes:
  GET  /api/tensor/dtypes          — list supported dtypes
  POST /api/tensor/create          — create a tensor (zeros/ones/range/random)
  POST /api/tensor/op              — apply binary op to two tensors
  GET  /api/tensor/model/info      — fetch model parameter info from Ollama
  POST /api/tensor/chat            — chat completion with full parameter control
                                     (supports api_key + custom base_url for
                                      OpenAI-compatible endpoints)
"""

import json
import os
import sys
from pathlib import Path

import httpx
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/tensor", tags=["tensor_lab"])

REPO_ROOT = Path(__file__).resolve().parents[4]
_HELPERS = str(REPO_ROOT / "helpers" / "python")
if _HELPERS not in sys.path:
    sys.path.insert(0, _HELPERS)

DEFAULT_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


# ---------------------------------------------------------------------------
# Dtype catalogue
# ---------------------------------------------------------------------------

_DTYPE_INFO: list[dict] = [
    {"name": "float32", "alias": "fp32", "bits": 32, "description": "Full-precision 32-bit float — reference quality"},
    {"name": "float16", "alias": "fp16", "bits": 16, "description": "Half-precision float — GPU inference standard"},
    {"name": "bfloat16", "alias": "bf16", "bits": 16, "description": "Brain float16 — better dynamic range than fp16"},
    {"name": "int8",    "alias": "q8",   "bits": 8,  "description": "8-bit integer — near-lossless quantisation"},
    {"name": "int32",   "alias": "i32",  "bits": 32, "description": "32-bit integer"},
    {"name": "uint8",   "alias": "u8",   "bits": 8,  "description": "8-bit unsigned integer"},
]

_NP_DTYPE_MAP: dict[str, np.dtype] = {
    "float32":  np.dtype("float32"),
    "fp32":     np.dtype("float32"),
    "float16":  np.dtype("float16"),
    "fp16":     np.dtype("float16"),
    "bfloat16": np.dtype("float32"),   # numpy has no bfloat16; upcast to float32
    "bf16":     np.dtype("float32"),
    "int8":     np.dtype("int8"),
    "q8":       np.dtype("int8"),
    "int32":    np.dtype("int32"),
    "i32":      np.dtype("int32"),
    "uint8":    np.dtype("uint8"),
    "u8":       np.dtype("uint8"),
}


def _resolve_dtype(name: str) -> np.dtype:
    dt = _NP_DTYPE_MAP.get(name.lower())
    if dt is None:
        raise ValueError(f"Unsupported dtype '{name}'. Use one of: {list(_NP_DTYPE_MAP.keys())}")
    return dt


@router.get("/dtypes")
async def list_dtypes() -> dict:
    """List supported tensor data types with descriptions."""
    return {"dtypes": _DTYPE_INFO}


# ---------------------------------------------------------------------------
# Tensor creation
# ---------------------------------------------------------------------------

class TensorCreateRequest(BaseModel):
    shape: list[int] = Field(..., description="Tensor dimensions, e.g. [3, 4]")
    dtype: str = Field("float32", description="Data type string, e.g. float32, fp16, int8")
    fill: str = Field("zeros", description="Fill method: zeros | ones | range | random")


@router.post("/create")
async def create_tensor(request: TensorCreateRequest) -> dict:
    """
    Create a tensor with the given shape, dtype, and fill method.

    Returns tensor metadata and a flat preview of values (up to 64 elements).
    """
    try:
        dtype = _resolve_dtype(request.dtype)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    shape = request.shape
    if not shape or any(d <= 0 for d in shape):
        raise HTTPException(status_code=422, detail="All shape dimensions must be positive integers")

    n_elements = 1
    for d in shape:
        n_elements *= d
    if n_elements > 1_000_000:
        raise HTTPException(status_code=422, detail="Tensor too large (max 1 000 000 elements)")

    fill = request.fill.lower()
    if fill == "zeros":
        arr = np.zeros(shape, dtype=dtype)
    elif fill == "ones":
        arr = np.ones(shape, dtype=dtype)
    elif fill == "range":
        arr = np.arange(n_elements, dtype=dtype).reshape(shape)
    elif fill == "random":
        if np.issubdtype(dtype, np.integer):
            arr = np.random.randint(0, 128, size=shape).astype(dtype)
        else:
            arr = np.random.randn(*shape).astype(dtype)
    else:
        raise HTTPException(status_code=422, detail=f"Unknown fill '{fill}'. Use: zeros, ones, range, random")

    flat = arr.flatten()
    preview = flat[:64].tolist()

    return {
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "n_elements": int(n_elements),
        "nbytes": int(arr.nbytes),
        "preview": preview,
        "truncated": n_elements > 64,
    }


# ---------------------------------------------------------------------------
# Tensor operations
# ---------------------------------------------------------------------------

class TensorOpRequest(BaseModel):
    a: list = Field(..., description="First tensor as nested list")
    b: list = Field(..., description="Second tensor as nested list")
    op: str = Field("add", description="Operation: add | sub | mul | matmul")


@router.post("/op")
async def tensor_op(request: TensorOpRequest) -> dict:
    """
    Apply a binary operation to two tensors supplied as nested lists.

    Supports: add, sub, mul (element-wise) and matmul (matrix multiply).
    Both tensors must have matching shapes for element-wise ops.
    For matmul, shapes must be compatible: (M×K) and (K×N).
    """
    try:
        a = np.array(request.a, dtype=np.float64)
        b = np.array(request.b, dtype=np.float64)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse tensor data: {exc}") from exc

    op = request.op.lower()
    try:
        if op == "add":
            result = np.add(a, b)
        elif op == "sub":
            result = np.subtract(a, b)
        elif op == "mul":
            result = np.multiply(a, b)
        elif op == "matmul":
            result = np.matmul(a, b)
        else:
            raise HTTPException(status_code=422, detail=f"Unknown op '{op}'. Use: add, sub, mul, matmul")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    flat = result.flatten()
    return {
        "op": op,
        "shape_a": list(a.shape),
        "shape_b": list(b.shape),
        "shape_result": list(result.shape),
        "result": result.tolist(),
        "preview": flat[:64].tolist(),
    }


# ---------------------------------------------------------------------------
# Model info via Ollama
# ---------------------------------------------------------------------------

@router.get("/model/info")
async def get_model_info(model: str) -> dict:
    """
    Return parameter and template information for a model from the Ollama instance.

    Pass ?model=<name>, e.g. /api/tensor/model/info?model=llama3
    """
    base_url = DEFAULT_OLLAMA_BASE_URL
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{base_url}/api/show", json={"name": model})
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Model '{model}' not found in Ollama")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama unreachable: {exc}") from exc

    # Return model info with parameters and template
    return {
        "model": model,
        "parameters": data.get("parameters", ""),
        "template": data.get("template", ""),
        "system": data.get("system", ""),
        "details": data.get("details", {}),
        "model_info": data.get("model_info", {}),
    }


# ---------------------------------------------------------------------------
# Custom chat completion (with full parameter control + API key support)
# ---------------------------------------------------------------------------

class TensorChatMessage(BaseModel):
    role: str
    content: str


class TensorChatRequest(BaseModel):
    model: str
    messages: list[TensorChatMessage]
    temperature: float | None = 0.8
    top_p: float | None = 0.9
    top_k: int | None = 40
    repeat_penalty: float | None = 1.1
    num_predict: int | None = 512
    num_ctx: int | None = 2048
    stream: bool = True
    # Connection overrides — api_key is passed as Authorization: ******
    base_url: str | None = None
    api_key: str | None = None


@router.post("/chat")
async def tensor_chat(request: TensorChatRequest):
    """
    Send a chat completion to an Ollama-compatible endpoint with full
    parameter control.

    Supports:
    - Custom ``base_url`` to target any Ollama-compatible server.
    - ``api_key`` forwarded as ``Authorization: ****** for endpoints
      that require authentication.
    - All standard Ollama sampling parameters (temperature, top_p, top_k,
      repeat_penalty, num_predict, num_ctx).
    """
    base_url = (request.base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/")

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if request.api_key:
        headers["Authorization"] = f"******"

    options: dict = {}
    if request.temperature is not None:
        options["temperature"] = request.temperature
    if request.top_p is not None:
        options["top_p"] = request.top_p
    if request.top_k is not None:
        options["top_k"] = request.top_k
    if request.repeat_penalty is not None:
        options["repeat_penalty"] = request.repeat_penalty
    if request.num_predict is not None:
        options["num_predict"] = request.num_predict
    if request.num_ctx is not None:
        options["num_ctx"] = request.num_ctx

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    payload: dict = {
        "model": request.model,
        "messages": messages,
        "stream": request.stream,
    }
    if options:
        payload["options"] = options

    if request.stream:
        async def _generator():
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/api/chat",
                    json=payload,
                    headers=headers,
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        raise HTTPException(
                            status_code=resp.status_code,
                            detail=f"Backend error {resp.status_code}: {body.decode()[:500]}",
                        )
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done"):
                            break

        return StreamingResponse(_generator(), media_type="text/plain")

    # Non-streaming
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{base_url}/api/chat",
                json={**payload, "stream": False},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return {"response": data.get("message", {}).get("content", "")}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
