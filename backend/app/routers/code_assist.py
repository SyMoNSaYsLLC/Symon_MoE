from __future__ import annotations

import json
import os

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/code", tags=["code_assist"])

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_CODE_MODEL = os.environ.get("CODE_MODEL", "codellama")

_ACTION_PROMPTS: dict[str, str] = {
    "explain": (
        "You are an expert software engineer. Explain the following code clearly and concisely, "
        "describing what it does, how it works, and any notable patterns or potential issues.\n\n"
        "Code:\n```\n{code}\n```"
    ),
    "complete": (
        "You are an expert software engineer. Complete the following code. "
        "Only output the completed code without extra explanation.\n\n"
        "Partial code:\n```\n{code}\n```"
    ),
    "refactor": (
        "You are an expert software engineer. Refactor the following code to improve readability, "
        "maintainability, and performance. Show the refactored version with a brief explanation "
        "of each change.\n\n"
        "Original code:\n```\n{code}\n```"
    ),
    "debug": (
        "You are an expert software engineer and debugger. Analyse the following code for bugs, "
        "logic errors, and potential issues. For each issue found, explain the problem and provide "
        "a fix.\n\n"
        "Code:\n```\n{code}\n```"
    ),
}


class CodeRequest(BaseModel):
    code: str
    action: str = "explain"    # explain | complete | refactor | debug
    language: str | None = None
    model: str | None = None
    stream: bool = True


@router.post("")
async def code_assist(request: CodeRequest):
    """Submit a code snippet for LLM-assisted explanation, completion, refactoring, or debugging."""
    if request.action not in _ACTION_PROMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action '{request.action}'. Valid: {list(_ACTION_PROMPTS.keys())}"
        )

    template = _ACTION_PROMPTS[request.action]
    code_block = request.code
    if request.language:
        code_block = f"# Language: {request.language}\n{code_block}"
    prompt = template.format(code=code_block)

    model = request.model or DEFAULT_CODE_MODEL
    payload: dict = {"model": model, "prompt": prompt, "stream": request.stream}

    if request.stream:
        async def _generator():
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", f"{OLLAMA_BASE_URL}/api/generate", json=payload
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        raise HTTPException(
                            status_code=502,
                            detail=f"Ollama error {resp.status_code}: {body.decode()}"
                        )
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        yield chunk.get("response", "")
                        if chunk.get("done"):
                            break

        return StreamingResponse(_generator(), media_type="text/plain")

    # Non-streaming
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate", json={**payload, "stream": False}
            )
            resp.raise_for_status()
            return {"response": resp.json().get("response", "")}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
