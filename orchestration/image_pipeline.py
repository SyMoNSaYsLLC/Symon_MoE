#!/usr/bin/env python3
"""
image_pipeline.py — Text-to-image / img2img inference wrapper.

Wraps the stable-diffusion.cpp CLI (converters/diffusers_cpp) to provide a
unified Python-callable interface for text-to-image and image-to-image
generation with GGUF diffusion models.

Usage:
  python3 orchestration/image_pipeline.py txt2img \
    --model models/converted/model.gguf \
    --prompt "A cyberpunk cityscape at night" \
    --output output.png

  python3 orchestration/image_pipeline.py img2img \
    --model models/converted/model.gguf \
    --prompt "Turn it into an oil painting" \
    --input-image init.png \
    --strength 0.7 \
    --output output.png
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Path to the stable-diffusion.cpp binary built from the submodule
SD_CPP_BIN = Path(
    os.environ.get(
        "SD_CPP_BIN",
        str(REPO_ROOT / "converters" / "diffusers_cpp" / "build" / "bin" / "sd"),
    )
)


def _find_sd_bin() -> Path:
    if SD_CPP_BIN.exists():
        return SD_CPP_BIN
    from shutil import which
    found = which("sd")
    if found:
        return Path(found)
    raise FileNotFoundError(
        f"stable-diffusion.cpp binary not found at {SD_CPP_BIN}. "
        "Build it first: cd converters/diffusers_cpp && cmake -B build && cmake --build build -j"
    )


# ---------------------------------------------------------------------------
# txt2img
# ---------------------------------------------------------------------------

def txt2img(
    model: str | Path,
    prompt: str,
    output: str | Path,
    negative_prompt: str = "",
    width: int = 512,
    height: int = 512,
    steps: int = 20,
    cfg_scale: float = 7.0,
    seed: int = -1,
    extra_args: list[str] | None = None,
) -> int:
    """
    Run text-to-image generation using stable-diffusion.cpp.

    Returns the process return code (0 = success).
    """
    bin_path = _find_sd_bin()
    cmd = [
        str(bin_path),
        "--model",  str(model),
        "--prompt", prompt,
        "--output", str(output),
        "--width",  str(width),
        "--height", str(height),
        "--steps",  str(steps),
        "--cfg-scale", str(cfg_scale),
        "--seed",   str(seed),
        "--mode", "txt2img",
    ]
    if negative_prompt:
        cmd += ["--negative-prompt", negative_prompt]
    if extra_args:
        cmd.extend(extra_args)

    print(f"[image_pipeline] {' '.join(cmd[:6])} …")
    result = subprocess.run(cmd)
    return result.returncode


# ---------------------------------------------------------------------------
# img2img
# ---------------------------------------------------------------------------

def img2img(
    model: str | Path,
    prompt: str,
    input_image: str | Path,
    output: str | Path,
    negative_prompt: str = "",
    strength: float = 0.75,
    steps: int = 20,
    cfg_scale: float = 7.0,
    seed: int = -1,
    extra_args: list[str] | None = None,
) -> int:
    """
    Run image-to-image generation using stable-diffusion.cpp.

    Returns the process return code (0 = success).
    """
    bin_path = _find_sd_bin()
    cmd = [
        str(bin_path),
        "--model",       str(model),
        "--prompt",      prompt,
        "--init-img",    str(input_image),
        "--output",      str(output),
        "--strength",    str(strength),
        "--steps",       str(steps),
        "--cfg-scale",   str(cfg_scale),
        "--seed",        str(seed),
        "--mode",        "img2img",
    ]
    if negative_prompt:
        cmd += ["--negative-prompt", negative_prompt]
    if extra_args:
        cmd.extend(extra_args)

    print(f"[image_pipeline] {' '.join(cmd[:6])} …")
    result = subprocess.run(cmd)
    return result.returncode


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Symon_MoE image generation pipeline"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- txt2img ----
    t2i = sub.add_parser("txt2img", help="Text-to-image generation")
    t2i.add_argument("--model",    required=True)
    t2i.add_argument("--prompt",   required=True)
    t2i.add_argument("--output",   default="output.png")
    t2i.add_argument("--negative", default="", dest="negative_prompt")
    t2i.add_argument("--width",    type=int, default=512)
    t2i.add_argument("--height",   type=int, default=512)
    t2i.add_argument("--steps",    type=int, default=20)
    t2i.add_argument("--cfg",      type=float, default=7.0, dest="cfg_scale")
    t2i.add_argument("--seed",     type=int, default=-1)

    # ---- img2img ----
    i2i = sub.add_parser("img2img", help="Image-to-image generation")
    i2i.add_argument("--model",         required=True)
    i2i.add_argument("--prompt",        required=True)
    i2i.add_argument("--input-image",   required=True, dest="input_image")
    i2i.add_argument("--output",        default="output.png")
    i2i.add_argument("--negative",      default="", dest="negative_prompt")
    i2i.add_argument("--strength",      type=float, default=0.75)
    i2i.add_argument("--steps",         type=int, default=20)
    i2i.add_argument("--cfg",           type=float, default=7.0, dest="cfg_scale")
    i2i.add_argument("--seed",          type=int, default=-1)

    args = parser.parse_args()

    if args.command == "txt2img":
        rc = txt2img(
            args.model, args.prompt, args.output,
            args.negative_prompt, args.width, args.height,
            args.steps, args.cfg_scale, args.seed,
        )
    else:
        rc = img2img(
            args.model, args.prompt, args.input_image, args.output,
            args.negative_prompt, args.strength,
            args.steps, args.cfg_scale, args.seed,
        )

    sys.exit(rc)


if __name__ == "__main__":
    main()
