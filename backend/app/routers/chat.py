from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Default Ollama base URL (override via env var OLLAMA_BASE_URL)
import os
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


class ChatMessage(BaseModel):
    role: str       # "system" | "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = True
    temperature: float | None = None
    system: str | None = None


async def _stream_ollama(model: str, messages: list[dict], options: dict) -> asyncio.Queue:
    """Stream tokens from Ollama /api/chat into an asyncio.Queue."""
    q: asyncio.Queue = asyncio.Queue()

    async def _fetch() -> None:
        payload: dict = {"model": model, "messages": messages, "stream": True}
        if options:
            payload["options"] = options
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        await q.put(
                            RuntimeError(f"Ollama error {resp.status_code}: {body.decode()}")
                        )
                        return
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            await q.put(content)
                        if chunk.get("done"):
                            break
        except Exception as exc:  # pragma: no cover
            await q.put(exc)
        finally:
            await q.put(None)   # sentinel

    asyncio.create_task(_fetch())
    return q


@router.get("/models")
async def list_chat_models() -> dict:
    """Return models currently available in the Ollama instance."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama unreachable: {exc}") from exc


@router.post("")
async def chat(request: ChatRequest):
    """Stream or collect a chat response from Ollama."""
    options: dict = {}
    if request.temperature is not None:
        options["temperature"] = request.temperature

    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    if request.system:
        messages.insert(0, {"role": "system", "content": request.system})

    if request.stream:
        q = await _stream_ollama(request.model, messages, options)

        async def _generator():
            while True:
                item = await q.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item

        return StreamingResponse(_generator(), media_type="text/plain")

    # Non-streaming
    payload: dict = {"model": request.model, "messages": messages, "stream": False}
    if options:
        payload["options"] = options
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return {"response": data.get("message", {}).get("content", "")}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
