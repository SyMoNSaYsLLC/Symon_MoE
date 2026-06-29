#!/usr/bin/env python3
"""
lora_merge.py — LoRA weight merging for LLM and diffusion checkpoints.

Supports merging LoRA adapter weights into a base model for:
- LLM checkpoints stored in .safetensors format (PEFT-style LoRA).
- Diffusion checkpoints in .safetensors format (Kohya-style LoRA).

The merged output is saved as a .safetensors file ready for downstream
conversion to GGUF.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

try:
    from safetensors import safe_open
    from safetensors.numpy import save_file as st_save_file
    HAS_SAFETENSORS = True
except ImportError:
    HAS_SAFETENSORS = False


def _require_safetensors() -> None:
    if not HAS_SAFETENSORS:
        raise ImportError("safetensors not installed. Run: pip install safetensors")


# ---------------------------------------------------------------------------
# Core merge logic
# ---------------------------------------------------------------------------

def load_tensors(path: str | Path) -> dict[str, np.ndarray]:
    """Load all tensors from a .safetensors file into a dict."""
    _require_safetensors()
    tensors: dict[str, np.ndarray] = {}
    with safe_open(str(path), framework="numpy") as f:
        for name in f.keys():
            tensors[name] = f.get_tensor(name)
    return tensors


def merge_lora_peft(
    base_tensors: dict[str, np.ndarray],
    lora_tensors: dict[str, np.ndarray],
    alpha: float = 1.0,
) -> dict[str, np.ndarray]:
    """
    Merge PEFT-style LoRA tensors into *base_tensors*.

    PEFT LoRA stores pairs: ``base_model.model.<layer>.lora_A.weight`` and
    ``base_model.model.<layer>.lora_B.weight``.  The merged weight is::

        W_merged = W_base + alpha * (lora_B @ lora_A)

    Parameters
    ----------
    base_tensors : Tensors loaded from the base model.
    lora_tensors : Tensors loaded from the LoRA adapter.
    alpha        : Scaling factor (typically lora_alpha / lora_rank).

    Returns
    -------
    dict[str, np.ndarray] : Merged tensor dict (shallow copy of base updated in place).
    """
    merged = {k: v.copy() for k, v in base_tensors.items()}

    # Collect LoRA A/B pairs
    lora_a: dict[str, np.ndarray] = {}
    lora_b: dict[str, np.ndarray] = {}
    for key, tensor in lora_tensors.items():
        if "lora_A" in key:
            base_key = key.replace("base_model.model.", "").replace(".lora_A.weight", ".weight")
            lora_a[base_key] = tensor
        elif "lora_B" in key:
            base_key = key.replace("base_model.model.", "").replace(".lora_B.weight", ".weight")
            lora_b[base_key] = tensor

    applied = 0
    for base_key in lora_a:
        if base_key not in lora_b:
            continue
        if base_key not in merged:
            print(f"[lora_merge] WARNING: base key not found: {base_key}", file=sys.stderr)
            continue
        A = lora_a[base_key].astype(np.float32)
        B = lora_b[base_key].astype(np.float32)
        W = merged[base_key].astype(np.float32)
        delta = alpha * (B @ A)
        if W.shape != delta.shape:
            print(
                f"[lora_merge] Shape mismatch for {base_key}: {W.shape} vs {delta.shape}",
                file=sys.stderr,
            )
            continue
        merged[base_key] = (W + delta).astype(merged[base_key].dtype)
        applied += 1

    print(f"[lora_merge] Applied {applied} LoRA weight pairs (PEFT style)")
    return merged


def merge_lora_kohya(
    base_tensors: dict[str, np.ndarray],
    lora_tensors: dict[str, np.ndarray],
    alpha: float = 1.0,
) -> dict[str, np.ndarray]:
    """
    Merge Kohya-style LoRA tensors into *base_tensors*.

    Kohya LoRA stores pairs: ``<module>.lora_down.weight`` and
    ``<module>.lora_up.weight``.  The merged weight is::

        W_merged = W_base + alpha * (lora_up @ lora_down)
    """
    merged = {k: v.copy() for k, v in base_tensors.items()}

    lora_down: dict[str, np.ndarray] = {}
    lora_up: dict[str, np.ndarray] = {}
    for key, tensor in lora_tensors.items():
        if key.endswith(".lora_down.weight"):
            base_key = key[: -len(".lora_down.weight")] + ".weight"
            lora_down[base_key] = tensor
        elif key.endswith(".lora_up.weight"):
            base_key = key[: -len(".lora_up.weight")] + ".weight"
            lora_up[base_key] = tensor

    applied = 0
    for base_key in lora_down:
        if base_key not in lora_up:
            continue
        if base_key not in merged:
            print(f"[lora_merge] WARNING: base key not found: {base_key}", file=sys.stderr)
            continue
        down = lora_down[base_key].astype(np.float32)
        up = lora_up[base_key].astype(np.float32)
        W = merged[base_key].astype(np.float32)
        delta = alpha * (up @ down)
        if W.shape != delta.shape:
            print(
                f"[lora_merge] Shape mismatch for {base_key}: {W.shape} vs {delta.shape}",
                file=sys.stderr,
            )
            continue
        merged[base_key] = (W + delta).astype(merged[base_key].dtype)
        applied += 1

    print(f"[lora_merge] Applied {applied} LoRA weight pairs (Kohya style)")
    return merged


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge LoRA adapter weights into a base model checkpoint"
    )
    parser.add_argument("base", help="Base model .safetensors file")
    parser.add_argument("lora", help="LoRA adapter .safetensors file")
    parser.add_argument("output", help="Output merged .safetensors file")
    parser.add_argument(
        "--alpha", type=float, default=1.0,
        help="LoRA merge scale (default: 1.0)"
    )
    parser.add_argument(
        "--style", choices=["peft", "kohya"], default="peft",
        help="LoRA adapter format style (default: peft)"
    )
    args = parser.parse_args()

    _require_safetensors()

    print(f"Loading base model: {args.base}")
    base = load_tensors(args.base)
    print(f"Loading LoRA adapter: {args.lora}")
    lora = load_tensors(args.lora)

    if args.style == "peft":
        merged = merge_lora_peft(base, lora, args.alpha)
    else:
        merged = merge_lora_kohya(base, lora, args.alpha)

    print(f"Saving merged model to: {args.output}")
    st_save_file(merged, args.output)
    print("Done.")


if __name__ == "__main__":
    main()
