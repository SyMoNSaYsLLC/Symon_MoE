#!/usr/bin/env python3
"""
ollama_compat.py — Modelfile generator and push/pull wrappers for Ollama REST API.

Provides utilities to:
- Generate an Ollama Modelfile from a GGUF path and optional parameters.
- Push a model to an Ollama instance via the REST API.
- Pull a model from the Ollama registry.
- List models currently loaded in an Ollama instance.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Generator

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

DEFAULT_OLLAMA_BASE = "http://localhost:11434"


def _client(base_url: str, timeout: float = 120.0) -> "httpx.Client":
    if not HAS_HTTPX:
        raise ImportError("httpx not installed. Run: pip install httpx")
    return httpx.Client(base_url=base_url, timeout=timeout)


# ---------------------------------------------------------------------------
# Modelfile generation
# ---------------------------------------------------------------------------

def generate_modelfile(
    gguf_path: str | Path,
    system_prompt: str | None = None,
    template: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> str:
    """
    Generate an Ollama Modelfile string for a local GGUF file.

    Parameters
    ----------
    gguf_path     : Absolute path to the .gguf file.
    system_prompt : Optional SYSTEM directive content.
    template      : Optional TEMPLATE directive (chat template string).
    parameters    : Optional dict of PARAMETER directives (e.g. {"temperature": 0.7}).

    Returns
    -------
    str : The rendered Modelfile content.
    """
    lines: list[str] = [f'FROM "{Path(gguf_path).resolve()}"']

    if system_prompt:
        escaped = system_prompt.replace('"""', '\\"\\"\\"')
        lines.append(f'\nSYSTEM """\n{escaped}\n"""')

    if template:
        escaped = template.replace('"""', '\\"\\"\\"')
        lines.append(f'\nTEMPLATE """\n{escaped}\n"""')

    if parameters:
        for key, value in parameters.items():
            lines.append(f"\nPARAMETER {key} {value}")

    return "\n".join(lines) + "\n"


def write_modelfile(
    path: str | Path,
    gguf_path: str | Path,
    system_prompt: str | None = None,
    template: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> Path:
    """Write a Modelfile to *path* and return the resolved path."""
    content = generate_modelfile(gguf_path, system_prompt, template, parameters)
    out = Path(path)
    out.write_text(content, encoding="utf-8")
    print(f"Modelfile written to: {out}")
    return out


# ---------------------------------------------------------------------------
# REST API wrappers
# ---------------------------------------------------------------------------

def list_models(base_url: str = DEFAULT_OLLAMA_BASE) -> list[dict]:
    """Return the list of models available in an Ollama instance."""
    with _client(base_url) as client:
        resp = client.get("/api/tags")
        resp.raise_for_status()
        return resp.json().get("models", [])


def create_model(
    name: str,
    modelfile_content: str,
    base_url: str = DEFAULT_OLLAMA_BASE,
    stream: bool = False,
) -> Generator[dict, None, None] | dict:
    """
    Create (register) a model in Ollama via the /api/create endpoint.

    Yields status dicts when stream=True, otherwise returns the final response.
    """
    payload = {"name": name, "modelfile": modelfile_content, "stream": stream}
    if stream:
        def _stream() -> Generator[dict, None, None]:
            with _client(base_url) as client:
                with client.stream("POST", "/api/create", json=payload) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if line.strip():
                            yield json.loads(line)
        return _stream()
    else:
        with _client(base_url) as client:
            resp = client.post("/api/create", json=payload)
            resp.raise_for_status()
            return resp.json()


def pull_model(
    name: str,
    base_url: str = DEFAULT_OLLAMA_BASE,
) -> list[dict]:
    """Pull a model from the Ollama registry. Returns all streamed status dicts."""
    payload = {"name": name, "stream": True}
    statuses: list[dict] = []
    with _client(base_url, timeout=600.0) as client:
        with client.stream("POST", "/api/pull", json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line.strip():
                    status = json.loads(line)
                    statuses.append(status)
                    print(status.get("status", ""))
    return statuses


def delete_model(name: str, base_url: str = DEFAULT_OLLAMA_BASE) -> None:
    """Delete a model from an Ollama instance."""
    with _client(base_url) as client:
        resp = client.request("DELETE", "/api/delete", json={"name": name})
        resp.raise_for_status()
    print(f"Deleted model: {name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Ollama compatibility helpers")
    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE)
    sub = parser.add_subparsers(dest="command", required=True)

    gen_p = sub.add_parser("modelfile", help="Generate a Modelfile from a GGUF path")
    gen_p.add_argument("gguf", help="Path to .gguf file")
    gen_p.add_argument("--out", default=None, help="Write Modelfile to this path")
    gen_p.add_argument("--system", default=None, help="System prompt")
    gen_p.add_argument("--temperature", type=float, default=None)

    list_p = sub.add_parser("list", help="List models in an Ollama instance")

    pull_p = sub.add_parser("pull", help="Pull a model from Ollama registry")
    pull_p.add_argument("name", help="Model name (e.g. llama3:8b)")

    del_p = sub.add_parser("delete", help="Delete a model from Ollama")
    del_p.add_argument("name", help="Model name to delete")

    args = parser.parse_args()

    if args.command == "modelfile":
        params = {}
        if args.temperature is not None:
            params["temperature"] = args.temperature
        content = generate_modelfile(args.gguf, args.system, parameters=params or None)
        if args.out:
            Path(args.out).write_text(content)
            print(f"Written to {args.out}")
        else:
            print(content)
    elif args.command == "list":
        for m in list_models(args.base_url):
            print(m.get("name", m))
    elif args.command == "pull":
        pull_model(args.name, args.base_url)
    elif args.command == "delete":
        delete_model(args.name, args.base_url)
