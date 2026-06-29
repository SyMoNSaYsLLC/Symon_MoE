#!/usr/bin/env python3
"""
tensor_utils.py — safetensors/GGUF tensor inspection, slicing, and dtype casting.

Mirrors the tensor-handling logic from llama.cpp/convert_hf_to_gguf.py so that
other helper scripts can reuse it without depending on the full conversion pipeline.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

import numpy as np

try:
    from safetensors import safe_open
    from safetensors.numpy import save_file as st_save_file
    HAS_SAFETENSORS = True
except ImportError:
    HAS_SAFETENSORS = False

# ---------------------------------------------------------------------------
# dtype mapping helpers
# ---------------------------------------------------------------------------

DTYPE_MAP: dict[str, np.dtype] = {
    "fp32":  np.dtype("float32"),
    "fp16":  np.dtype("float16"),
    "bf16":  np.dtype("float32"),   # numpy has no bf16; upcast on load
    "int8":  np.dtype("int8"),
    "uint8": np.dtype("uint8"),
}

_GGUF_DTYPE_NAMES: dict[int, str] = {
    0: "F32",
    1: "F16",
    2: "Q4_0",
    3: "Q4_1",
    6: "Q5_0",
    7: "Q5_1",
    8: "Q8_0",
    9: "Q8_1",
    10: "Q2_K",
    11: "Q3_K",
    12: "Q4_K",
    13: "Q5_K",
    14: "Q6_K",
    15: "Q8_K",
    30: "BF16",
}


def dtype_name_to_np(name: str) -> np.dtype:
    """Convert a string dtype name (e.g. 'fp16', 'float32') to a numpy dtype."""
    name_lower = name.lower().replace(" ", "")
    if name_lower in DTYPE_MAP:
        return DTYPE_MAP[name_lower]
    # Fall back to numpy parsing
    return np.dtype(name)


def cast_tensor(tensor: np.ndarray, target_dtype: str) -> np.ndarray:
    """Cast a numpy tensor to *target_dtype* string (e.g. 'fp16', 'float32')."""
    return tensor.astype(dtype_name_to_np(target_dtype))


# ---------------------------------------------------------------------------
# safetensors helpers
# ---------------------------------------------------------------------------

def list_safetensors(path: str | Path) -> list[dict[str, Any]]:
    """Return a list of tensor descriptors from a .safetensors file."""
    if not HAS_SAFETENSORS:
        raise ImportError("safetensors package not installed. Run: pip install safetensors")

    path = Path(path)
    tensors: list[dict[str, Any]] = []
    with safe_open(str(path), framework="numpy") as f:
        for name in f.keys():
            t = f.get_tensor(name)
            tensors.append({
                "name": name,
                "shape": list(t.shape),
                "dtype": str(t.dtype),
                "nbytes": t.nbytes,
            })
    return tensors


def load_safetensors_tensor(path: str | Path, name: str) -> np.ndarray:
    """Load a single named tensor from a .safetensors file as a numpy array."""
    if not HAS_SAFETENSORS:
        raise ImportError("safetensors package not installed. Run: pip install safetensors")

    with safe_open(str(path), framework="numpy") as f:
        return f.get_tensor(name)


def slice_tensor(tensor: np.ndarray, *slices: slice | int) -> np.ndarray:
    """Return a view/copy of *tensor* for the given index slices."""
    return tensor[tuple(slices)]


# ---------------------------------------------------------------------------
# GGUF tensor-block helpers (minimal — no full parser dependency)
# ---------------------------------------------------------------------------

def gguf_dtype_name(gguf_type: int) -> str:
    """Return a human-readable name for a GGUF tensor type integer."""
    return _GGUF_DTYPE_NAMES.get(gguf_type, f"UNKNOWN({gguf_type})")


def nbytes_gguf_block(gguf_type: int, n_elements: int) -> int:
    """Estimate byte size for a quantised GGUF block (approximate for Q types)."""
    block_sizes: dict[int, tuple[int, int]] = {
        2:  (32, 18),   # Q4_0: 32 elems, 18 bytes/block
        3:  (32, 20),   # Q4_1
        6:  (32, 22),   # Q5_0
        7:  (32, 24),   # Q5_1
        8:  (32, 34),   # Q8_0
    }
    if gguf_type == 0:   # F32
        return n_elements * 4
    if gguf_type == 1:   # F16
        return n_elements * 2
    if gguf_type == 30:  # BF16
        return n_elements * 2
    if gguf_type in block_sizes:
        blk_elems, blk_bytes = block_sizes[gguf_type]
        n_blocks = (n_elements + blk_elems - 1) // blk_elems
        return n_blocks * blk_bytes
    raise ValueError(f"Unsupported GGUF type {gguf_type} for byte estimation")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Inspect a .safetensors file")
    parser.add_argument("path", help="Path to .safetensors file")
    parser.add_argument("--tensor", default=None, help="Print info for one named tensor")
    args = parser.parse_args()

    info = list_safetensors(args.path)
    if args.tensor:
        info = [t for t in info if t["name"] == args.tensor]
    print(json.dumps(info, indent=2))
