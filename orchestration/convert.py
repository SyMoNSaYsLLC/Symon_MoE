#!/usr/bin/env python3
"""
Symon_MoE Orchestration Converter
----------------------------------
Detects the model architecture from a Hugging Face model directory and
dispatches to the correct conversion engine:
  - Text / VLM (Llama, Qwen, Mistral, Gemma, …) → llama.cpp
  - Diffusion / Flux (Flux, SD3, SDXL, …)        → ComfyUI-GGUF

Usage:
  python3 orchestration/convert.py <model_dir> [--outfile <name>.gguf] [--outtype q8_0]

Examples:
  # Auto-detect and convert an LLM
  python3 orchestration/convert.py /path/to/Qwen2-7B --outfile qwen2.gguf --outtype q8_0

  # Auto-detect and convert a diffusion model
  python3 orchestration/convert.py /path/to/flux1-dev --outfile flux1.gguf

  # Explicit safetensors input for diffusion models
  python3 orchestration/convert.py /path/to/flux1-dev --src flux1_dev.safetensors --outfile flux1.gguf
"""

import argparse
import glob
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LLM_ENGINE = os.path.join(REPO_ROOT, "converters", "llm_engine", "convert_hf_to_gguf.py")
DIFF_ENGINE = os.path.join(REPO_ROOT, "converters", "diff_engine", "tools", "convert.py")
DIFF_HELPER = os.path.join(REPO_ROOT, "helpers", "python", "diffusion_convert.py")

# Architectures that belong to the diffusion engine.
DIFFUSION_ARCH_KEYWORDS = {"Flux", "SD3", "SDXL", "StableDiffusion", "Unet", "UNet"}


def detect_architecture(model_dir: str) -> str | None:
    """Return the first architecture string from config.json, or None."""
    config_path = os.path.join(model_dir, "config.json")
    if not os.path.isfile(config_path):
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    archs = config.get("architectures") or []
    return archs[0] if archs else config.get("_class_name")


def is_diffusion(arch: str | None) -> bool:
    if arch is None:
        return False
    return any(kw.lower() in arch.lower() for kw in DIFFUSION_ARCH_KEYWORDS)


def find_safetensors(model_dir: str) -> str | None:
    """Return the first .safetensors file found in model_dir, or None."""
    matches = glob.glob(os.path.join(model_dir, "*.safetensors"))
    return matches[0] if matches else None


def convert_llm(model_dir: str, outfile: str, outtype: str) -> int:
    cmd = [
        sys.executable,
        LLM_ENGINE,
        model_dir,
        "--outfile", outfile,
        "--outtype", outtype,
    ]
    print(f"[LLM engine] {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def convert_diffusion(model_dir: str, src: str | None, outfile: str) -> int:
    if src is None:
        src = find_safetensors(model_dir)
    if src is None:
        print(
            "ERROR: No .safetensors file found in model directory. "
            "Pass --src <file.safetensors> explicitly.",
            file=sys.stderr,
        )
        return 1
    if not os.path.isabs(src):
        src = os.path.join(model_dir, src)

    # Prefer helpers/python/diffusion_convert.py (wraps stable-diffusion.cpp CLI)
    # if the GGUF-direct conversion is desired; fall back to diff_engine otherwise.
    if os.path.isfile(DIFF_HELPER):
        cmd = [
            sys.executable,
            DIFF_HELPER,
            "convert",
            src,
            outfile,
        ]
        print(f"[Diffusion helper] {' '.join(cmd)}")
    else:
        cmd = [
            sys.executable,
            DIFF_ENGINE,
            "--src", src,
            "--dst", outfile,
        ]
        print(f"[Diffusion engine] {' '.join(cmd)}")

    result = subprocess.run(cmd)
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Symon_MoE: convert any HuggingFace model to GGUF"
    )
    parser.add_argument("model_dir", help="Path to the HuggingFace model directory")
    parser.add_argument("--outfile", default="model.gguf", help="Output GGUF file path")
    parser.add_argument(
        "--outtype",
        default="q8_0",
        help="Quantisation type for LLM engine (default: q8_0)",
    )
    parser.add_argument(
        "--src",
        default=None,
        help="Source .safetensors file (diffusion models only; auto-detected if omitted)",
    )
    parser.add_argument(
        "--engine",
        choices=["llm", "diffusion", "auto"],
        default="auto",
        help="Force a specific conversion engine (default: auto)",
    )
    args = parser.parse_args()

    model_dir = os.path.abspath(args.model_dir)
    if not os.path.isdir(model_dir):
        print(f"ERROR: model directory not found: {model_dir}", file=sys.stderr)
        sys.exit(1)

    arch = detect_architecture(model_dir)
    print(f"Detected architecture: {arch or '(unknown)'}")

    use_diffusion = args.engine == "diffusion" or (
        args.engine == "auto" and is_diffusion(arch)
    )

    if use_diffusion:
        rc = convert_diffusion(model_dir, args.src, args.outfile)
    else:
        rc = convert_llm(model_dir, args.outfile, args.outtype)

    sys.exit(rc)


if __name__ == "__main__":
    main()
