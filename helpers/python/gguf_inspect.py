#!/usr/bin/env python3
"""
gguf_inspect.py — GGUF file metadata reader/writer.

Wraps the `gguf` Python package to expose a convenient CLI and importable
API for inspecting and patching GGUF metadata key-value pairs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import gguf  # type: ignore[import-untyped]
    from gguf import GGUFReader, GGUFValueType
    HAS_GGUF = True
except ImportError:
    HAS_GGUF = False


def _require_gguf() -> None:
    if not HAS_GGUF:
        raise ImportError("gguf package not installed. Run: pip install gguf")


# ---------------------------------------------------------------------------
# Reader helpers
# ---------------------------------------------------------------------------

def read_metadata(path: str | Path) -> dict:
    """Return all metadata KV pairs from a GGUF file as a plain dict."""
    _require_gguf()
    reader = GGUFReader(str(path), "r")
    result: dict = {}
    for field in reader.fields.values():
        name = field.name
        # Scalar vs array
        if field.types and field.types[0] == GGUFValueType.ARRAY:
            result[name] = [part.tolist() for part in field.parts[:-1]]
        elif field.parts:
            raw = field.parts[-1]
            result[name] = raw.tolist() if hasattr(raw, "tolist") else str(raw)
        else:
            result[name] = None
    return result


def list_tensors(path: str | Path) -> list[dict]:
    """Return a list of tensor descriptors (name, shape, type) from a GGUF file."""
    _require_gguf()
    reader = GGUFReader(str(path), "r")
    tensors = []
    for tensor in reader.tensors:
        tensors.append({
            "name": tensor.name,
            "shape": list(tensor.shape),
            "type": int(tensor.tensor_type),
            "type_name": tensor.tensor_type.name,
            "n_elements": int(tensor.n_elements),
            "data_offset": int(tensor.data_offset),
        })
    return tensors


def read_key(path: str | Path, key: str) -> object:
    """Read a single metadata value by *key* from a GGUF file."""
    meta = read_metadata(path)
    if key not in meta:
        raise KeyError(f"Key '{key}' not found in GGUF metadata")
    return meta[key]


# ---------------------------------------------------------------------------
# Writer helpers
# ---------------------------------------------------------------------------

def patch_metadata(
    src_path: str | Path,
    dst_path: str | Path,
    patches: dict[str, object],
) -> None:
    """
    Write a copy of *src_path* to *dst_path* with *patches* applied to metadata.

    Only string and numeric scalar patches are supported; tensor data is
    copied verbatim.
    """
    _require_gguf()
    import shutil

    src_path = Path(src_path)
    dst_path = Path(dst_path)

    # Read existing metadata
    existing_meta = read_metadata(src_path)
    existing_meta.update(patches)

    # Copy file then rewrite metadata using GGUFWriter
    shutil.copy2(src_path, dst_path)

    # Use gguf writer to create patched copy from scratch (append mode workaround)
    writer = gguf.GGUFWriter(str(dst_path), overwrite=True)
    for k, v in existing_meta.items():
        if isinstance(v, str):
            writer.add_string(k, v)
        elif isinstance(v, bool):
            writer.add_bool(k, v)
        elif isinstance(v, int):
            writer.add_int32(k, v)
        elif isinstance(v, float):
            writer.add_float32(k, v)
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli_read(args: argparse.Namespace) -> None:
    if args.key:
        value = read_key(args.path, args.key)
        print(json.dumps({args.key: value}, indent=2))
    elif args.tensors:
        tensors = list_tensors(args.path)
        print(json.dumps(tensors, indent=2))
    else:
        meta = read_metadata(args.path)
        print(json.dumps(meta, indent=2, default=str))


def _cli_patch(args: argparse.Namespace) -> None:
    patches = json.loads(args.patches)
    patch_metadata(args.path, args.output, patches)
    print(f"Patched GGUF written to: {args.output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="GGUF metadata inspector/patcher")
    sub = parser.add_subparsers(dest="command", required=True)

    read_p = sub.add_parser("read", help="Read metadata from a GGUF file")
    read_p.add_argument("path", help="Path to .gguf file")
    read_p.add_argument("--key", default=None, help="Read a single metadata key")
    read_p.add_argument("--tensors", action="store_true", help="List tensors instead of metadata")
    read_p.set_defaults(func=_cli_read)

    patch_p = sub.add_parser("patch", help="Patch metadata in a GGUF file")
    patch_p.add_argument("path", help="Source .gguf file")
    patch_p.add_argument("output", help="Destination .gguf file")
    patch_p.add_argument("patches", help='JSON object of key→value patches, e.g. \'{"general.name":"MyModel"}\'')
    patch_p.set_defaults(func=_cli_patch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
