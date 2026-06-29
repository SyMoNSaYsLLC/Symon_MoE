#!/usr/bin/env python3
"""
quant_utils.py — Quantisation preset helper for GGUF models.

Provides named presets for common quantisation types used with llama.cpp and
stable-diffusion.cpp, along with helpers to validate and expand preset names
before passing them to conversion pipelines.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Preset definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QuantPreset:
    name: str
    llama_cpp_flag: str
    description: str
    bits_per_weight: float
    suitable_for: list[str] = field(default_factory=list)


PRESETS: dict[str, QuantPreset] = {
    # ---- Full precision ----
    "fp32": QuantPreset(
        name="fp32",
        llama_cpp_flag="f32",
        description="32-bit floating point — no quantisation, largest size",
        bits_per_weight=32.0,
        suitable_for=["reference", "fine-tuning"],
    ),
    "fp16": QuantPreset(
        name="fp16",
        llama_cpp_flag="f16",
        description="16-bit floating point — good quality, half the size of fp32",
        bits_per_weight=16.0,
        suitable_for=["inference", "diffusion"],
    ),
    "bf16": QuantPreset(
        name="bf16",
        llama_cpp_flag="bf16",
        description="bfloat16 — better training stability than fp16",
        bits_per_weight=16.0,
        suitable_for=["training", "inference"],
    ),
    # ---- 8-bit ----
    "q8_0": QuantPreset(
        name="q8_0",
        llama_cpp_flag="q8_0",
        description="8-bit integer quantisation (block size 32) — near-lossless",
        bits_per_weight=8.5,
        suitable_for=["inference", "high-quality"],
    ),
    # ---- 5-bit ----
    "q5_k_s": QuantPreset(
        name="q5_k_s",
        llama_cpp_flag="q5_k_s",
        description="5-bit K-quant (small) — good quality/size trade-off",
        bits_per_weight=5.54,
        suitable_for=["inference", "balanced"],
    ),
    "q5_k_m": QuantPreset(
        name="q5_k_m",
        llama_cpp_flag="q5_k_m",
        description="5-bit K-quant (medium) — slightly better quality than q5_k_s",
        bits_per_weight=5.68,
        suitable_for=["inference", "balanced"],
    ),
    # ---- 4-bit ----
    "q4_k_s": QuantPreset(
        name="q4_k_s",
        llama_cpp_flag="q4_k_s",
        description="4-bit K-quant (small) — compact, moderate quality",
        bits_per_weight=4.37,
        suitable_for=["inference", "memory-constrained"],
    ),
    "q4_k_m": QuantPreset(
        name="q4_k_m",
        llama_cpp_flag="q4_k_m",
        description="4-bit K-quant (medium) — recommended default for most use cases",
        bits_per_weight=4.58,
        suitable_for=["inference", "memory-constrained", "recommended"],
    ),
    "q4_0": QuantPreset(
        name="q4_0",
        llama_cpp_flag="q4_0",
        description="Legacy 4-bit integer quantisation (block size 32)",
        bits_per_weight=4.5,
        suitable_for=["inference", "legacy"],
    ),
    "q4_1": QuantPreset(
        name="q4_1",
        llama_cpp_flag="q4_1",
        description="Legacy 4-bit integer quantisation with non-zero minimum",
        bits_per_weight=5.0,
        suitable_for=["inference", "legacy"],
    ),
    # ---- 3-bit ----
    "q3_k_s": QuantPreset(
        name="q3_k_s",
        llama_cpp_flag="q3_k_s",
        description="3-bit K-quant (small) — very compact, some quality loss",
        bits_per_weight=3.5,
        suitable_for=["inference", "very-memory-constrained"],
    ),
    "q3_k_m": QuantPreset(
        name="q3_k_m",
        llama_cpp_flag="q3_k_m",
        description="3-bit K-quant (medium)",
        bits_per_weight=3.91,
        suitable_for=["inference", "very-memory-constrained"],
    ),
    # ---- 2-bit ----
    "q2_k": QuantPreset(
        name="q2_k",
        llama_cpp_flag="q2_k",
        description="2-bit K-quant — extreme compression, significant quality loss",
        bits_per_weight=2.63,
        suitable_for=["inference", "extreme-compression"],
    ),
}

# Aliases for common shorthand
ALIASES: dict[str, str] = {
    "f32": "fp32",
    "f16": "fp16",
    "q4km": "q4_k_m",
    "q5km": "q5_k_m",
    "q4ks": "q4_k_s",
    "q5ks": "q5_k_s",
}


def resolve_preset(name: str) -> QuantPreset:
    """Resolve a preset name or alias to a QuantPreset. Raises ValueError if unknown."""
    canonical = ALIASES.get(name.lower(), name.lower())
    if canonical not in PRESETS:
        available = ", ".join(sorted(PRESETS.keys()))
        raise ValueError(
            f"Unknown quantisation preset '{name}'. Available: {available}"
        )
    return PRESETS[canonical]


def llama_cpp_flag(name: str) -> str:
    """Return the llama.cpp --outtype flag value for a given preset name."""
    return resolve_preset(name).llama_cpp_flag


def estimate_model_size_gb(
    n_parameters: int,
    preset: str,
    overhead_gb: float = 0.1,
) -> float:
    """
    Estimate the on-disk size in GB for a quantised model.

    Parameters
    ----------
    n_parameters : Number of model parameters.
    preset       : Quantisation preset name.
    overhead_gb  : Fixed overhead for GGUF headers and metadata (default 0.1 GB).
    """
    p = resolve_preset(preset)
    weight_bits = p.bits_per_weight * n_parameters
    return weight_bits / 8 / 1e9 + overhead_gb


def list_presets(suitable_for: str | None = None) -> list[QuantPreset]:
    """Return all presets, optionally filtered by *suitable_for* tag."""
    presets = list(PRESETS.values())
    if suitable_for:
        presets = [p for p in presets if suitable_for in p.suitable_for]
    return sorted(presets, key=lambda p: p.bits_per_weight, reverse=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantisation preset helper")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all available quantisation presets")

    info_p = sub.add_parser("info", help="Show details for a preset")
    info_p.add_argument("preset", help="Preset name (e.g. q4_k_m)")

    est_p = sub.add_parser("estimate", help="Estimate model size for a preset")
    est_p.add_argument("params", type=float, help="Number of parameters (e.g. 7e9)")
    est_p.add_argument("preset", help="Quantisation preset name")

    args = parser.parse_args()

    if args.command == "list":
        for p in list_presets():
            print(f"  {p.name:<12} {p.bits_per_weight:>5.2f} bpw  {p.description}")
    elif args.command == "info":
        p = resolve_preset(args.preset)
        print(json.dumps({
            "name": p.name,
            "llama_cpp_flag": p.llama_cpp_flag,
            "bits_per_weight": p.bits_per_weight,
            "description": p.description,
            "suitable_for": p.suitable_for,
        }, indent=2))
    elif args.command == "estimate":
        size = estimate_model_size_gb(int(args.params), args.preset)
        print(f"Estimated size: {size:.2f} GB")
