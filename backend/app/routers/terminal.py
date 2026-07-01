from __future__ import annotations

import asyncio
import os
import pty
import secrets

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import TERMINAL_ENABLED, TERMINAL_SHELL, TERMINAL_TOKEN

router = APIRouter(tags=["terminal"])


@router.websocket("/api/terminal/ws")
async def terminal_ws(websocket: WebSocket) -> None:
    await websocket.accept()

    if not TERMINAL_ENABLED:
        await websocket.close(code=1008, reason="Terminal is disabled")
        return

    if TERMINAL_TOKEN:
        token = websocket.query_params.get("token", "")
        if not secrets.compare_digest(token, TERMINAL_TOKEN):
            await websocket.close(code=1008, reason="Unauthorized")
            return

    master_fd, slave_fd = pty.openpty()
    proc = await asyncio.create_subprocess_shell(
        TERMINAL_SHELL,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
    )
    os.close(slave_fd)

    async def reader() -> None:
        loop = asyncio.get_running_loop()
        while True:
            data = await loop.run_in_executor(None, os.read, master_fd, 1024)
            if not data:
                break
            await websocket.send_text(data.decode(errors="ignore"))

    async def writer() -> None:
        loop = asyncio.get_running_loop()
        while True:
            message = await websocket.receive_text()
            await loop.run_in_executor(None, os.write, master_fd, message.encode())

    try:
        await asyncio.gather(reader(), writer())
    except WebSocketDisconnect:
        pass
    finally:
        proc.terminate()
        await proc.wait()
        os.close(master_fd)
