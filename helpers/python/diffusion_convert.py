#!/usr/bin/env python3
"""
diffusion_convert.py — .safetensors → GGUF pipeline helper.

Wraps the stable-diffusion.cpp CLI (converters/diffusers_cpp) to convert
diffusion model weights from .safetensors format to GGUF, with optional
quantisation.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SD_CPP_DIR = REPO_ROOT / "converters" / "diffusers_cpp"

# Default convert binary built by CMake inside the submodule
DEFAULT_CONVERT_BIN = SD_CPP_DIR / "build" / "bin" / "sd"


def find_convert_bin(custom_bin: str | None = None) -> Path:
    """Resolve the stable-diffusion.cpp binary path."""
    if custom_bin:
        return Path(custom_bin)
    if DEFAULT_CONVERT_BIN.exists():
        return DEFAULT_CONVERT_BIN
    # Fall back to PATH
    from shutil import which
    found = which("sd")
    if found:
        return Path(found)
    raise FileNotFoundError(
        f"stable-diffusion.cpp binary not found at {DEFAULT_CONVERT_BIN}. "
        "Build it first: cd converters/diffusers_cpp && mkdir build && cd build && cmake .. && make -j"
    )


def convert_safetensors_to_gguf(
    src: str | Path,
    dst: str | Path,
    quant_type: str = "f16",
    convert_bin: str | None = None,
    extra_args: list[str] | None = None,
) -> int:
    """
    Convert a .safetensors diffusion checkpoint to GGUF.

    Parameters
    ----------
    src        : Source .safetensors file.
    dst        : Destination .gguf file.
    quant_type : Quantisation type string passed to sd binary (default: f16).
    convert_bin: Override path to the sd binary.
    extra_args : Additional CLI arguments forwarded verbatim.

    Returns
    -------
    int : Return code from the conversion process (0 = success).
    """
    bin_path = find_convert_bin(convert_bin)
    src = Path(src).resolve()
    dst = Path(dst).resolve()

    cmd: list[str] = [
        str(bin_path),
        "--convert", str(src),
        "--output", str(dst),
        "--type", quant_type,
    ]
    if extra_args:
        cmd.extend(extra_args)

    print(f"[diffusion_convert] {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def batch_convert(
    src_dir: str | Path,
    dst_dir: str | Path,
    quant_type: str = "f16",
    convert_bin: str | None = None,
) -> dict[str, int]:
    """
    Convert all .safetensors files in *src_dir* to GGUF in *dst_dir*.

    Returns a dict mapping each source filename to its conversion return code.
    """
    src_dir = Path(src_dir)
    dst_dir = Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, int] = {}
    for st_file in sorted(src_dir.glob("*.safetensors")):
        out_file = dst_dir / (st_file.stem + ".gguf")
        rc = convert_safetensors_to_gguf(st_file, out_file, quant_type, convert_bin)
        results[st_file.name] = rc
        status = "OK" if rc == 0 else f"FAILED (rc={rc})"
        print(f"  {st_file.name} → {out_file.name}: {status}")

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert .safetensors diffusion checkpoints to GGUF via stable-diffusion.cpp"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    single = sub.add_parser("convert", help="Convert a single .safetensors file")
    single.add_argument("src", help="Source .safetensors file")
    single.add_argument("dst", help="Destination .gguf file")
    single.add_argument("--type", dest="quant_type", default="f16",
                        help="Quantisation type (f16, q4_0, q8_0, …)")
    single.add_argument("--bin", dest="convert_bin", default=None,
                        help="Override path to sd binary")

    batch = sub.add_parser("batch", help="Convert all .safetensors in a directory")
    batch.add_argument("src_dir", help="Source directory containing .safetensors files")
    batch.add_argument("dst_dir", help="Destination directory for .gguf outputs")
    batch.add_argument("--type", dest="quant_type", default="f16",
                       help="Quantisation type (default: f16)")
    batch.add_argument("--bin", dest="convert_bin", default=None,
                       help="Override path to sd binary")

    args = parser.parse_args()

    if args.command == "convert":
        rc = convert_safetensors_to_gguf(
            args.src, args.dst, args.quant_type, args.convert_bin
        )
        sys.exit(rc)
    elif args.command == "batch":
        results = batch_convert(
            args.src_dir, args.dst_dir, args.quant_type, args.convert_bin
        )
        failed = [k for k, v in results.items() if v != 0]
        if failed:
            print(f"\n{len(failed)} conversion(s) failed: {', '.join(failed)}")
            sys.exit(1)
        print(f"\nAll {len(results)} conversion(s) succeeded.")


if __name__ == "__main__":
    main()
