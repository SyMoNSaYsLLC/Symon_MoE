#!/usr/bin/env python3
"""
video_pipeline.py — Text-to-video inference wrapper.

Routes text-to-video generation to CogVideoX or ModelScope depending on
which backend is configured via the VIDEO_BACKEND environment variable.

Usage:
  python3 orchestration/video_pipeline.py \
    --prompt "A timelapse of clouds over a mountain range" \
    --output output.mp4 \
    --frames 16 --fps 8 --width 512 --height 320
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

VIDEO_BACKEND = os.environ.get("VIDEO_BACKEND", "cogvideo").lower()
HF_MODEL_ID   = os.environ.get(
    "VIDEO_MODEL_ID",
    "THUDM/CogVideoX-5b" if VIDEO_BACKEND == "cogvideo" else "damo-vilab/text-to-video-ms-1.7b",
)
DEVICE = os.environ.get("VIDEO_DEVICE", "cuda")


# ---------------------------------------------------------------------------
# CogVideoX backend
# ---------------------------------------------------------------------------

def _run_cogvideo(
    prompt: str,
    output: Path,
    frames: int,
    fps: int,
    width: int,
    height: int,
) -> int:
    """Run text-to-video with CogVideoX (requires diffusers + torch)."""
    try:
        import torch
        from diffusers import CogVideoXPipeline
        from diffusers.utils import export_to_video
    except ImportError:
        print(
            "ERROR: CogVideoX requires: pip install diffusers transformers accelerate torch",
            file=sys.stderr,
        )
        return 1

    print(f"[video_pipeline] Loading CogVideoX model: {HF_MODEL_ID}")
    pipe = CogVideoXPipeline.from_pretrained(
        HF_MODEL_ID,
        torch_dtype=torch.bfloat16,
    )
    pipe.enable_model_cpu_offload()

    print(f"[video_pipeline] Generating: {prompt!r}")
    video = pipe(
        prompt=prompt,
        num_videos_per_prompt=1,
        num_inference_steps=50,
        num_frames=frames,
        guidance_scale=6,
        generator=torch.Generator(device="cpu").manual_seed(42),
    ).frames[0]

    export_to_video(video, str(output), fps=fps)
    print(f"[video_pipeline] Video saved to: {output}")
    return 0


# ---------------------------------------------------------------------------
# ModelScope backend
# ---------------------------------------------------------------------------

def _run_modelscope(
    prompt: str,
    output: Path,
    frames: int,
    fps: int,
    width: int,
    height: int,
) -> int:
    """Run text-to-video with ModelScope (requires modelscope + torch)."""
    try:
        from modelscope.pipelines import pipeline
        from modelscope.outputs import OutputKeys
        import imageio
    except ImportError:
        print(
            "ERROR: ModelScope requires: pip install modelscope imageio",
            file=sys.stderr,
        )
        return 1

    print(f"[video_pipeline] Loading ModelScope model: {HF_MODEL_ID}")
    p = pipeline("text-to-video-synthesis", HF_MODEL_ID)
    result = p({"text": prompt})
    video_frames = result[OutputKeys.OUTPUT_VIDEO]

    output.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(str(output), video_frames, fps=fps)
    print(f"[video_pipeline] Video saved to: {output}")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Symon_MoE text-to-video pipeline"
    )
    parser.add_argument("--prompt",  required=True, help="Text prompt")
    parser.add_argument("--output",  default="output.mp4", help="Output .mp4 path")
    parser.add_argument("--frames",  type=int, default=16,  help="Number of frames")
    parser.add_argument("--fps",     type=int, default=8,   help="Frames per second")
    parser.add_argument("--width",   type=int, default=512, help="Frame width")
    parser.add_argument("--height",  type=int, default=320, help="Frame height")
    parser.add_argument(
        "--backend",
        choices=["cogvideo", "modelscope"],
        default=VIDEO_BACKEND,
        help="Video generation backend (default: from VIDEO_BACKEND env var)",
    )
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.backend == "cogvideo":
        rc = _run_cogvideo(args.prompt, output, args.frames, args.fps, args.width, args.height)
    else:
        rc = _run_modelscope(args.prompt, output, args.frames, args.fps, args.width, args.height)

    sys.exit(rc)


if __name__ == "__main__":
    main()
