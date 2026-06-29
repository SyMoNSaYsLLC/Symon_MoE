from __future__ import annotations

import sys
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/iptv", tags=["iptv"])

# Add helpers/python to path for the Rust m3u_parser fallback (Python-based parser)
REPO_ROOT = Path(__file__).resolve().parents[4]

# ---------------------------------------------------------------------------
# Python fallback M3U parser (used if Rust binary is unavailable)
# ---------------------------------------------------------------------------

def _parse_m3u_python(content: str) -> list[dict]:
    """Minimal Python M3U parser fallback."""
    channels: list[dict] = []
    lines = content.splitlines()
    pending: dict | None = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF:"):
            info = line[8:]
            name = info.split(",", 1)[-1].strip() if "," in info else ""
            attrs_raw = info.split(",", 1)[0] if "," in info else ""

            def _get_attr(key: str) -> str | None:
                idx = attrs_raw.find(f'{key}="')
                if idx == -1:
                    return None
                start = idx + len(key) + 2
                end = attrs_raw.find('"', start)
                return attrs_raw[start:end] if end != -1 else None

            pending = {
                "name": name,
                "group": _get_attr("group-title"),
                "logo": _get_attr("tvg-logo"),
                "tvg_id": _get_attr("tvg-id"),
            }
        elif line.startswith("#"):
            continue
        else:
            ch = {**(pending or {}), "url": line}
            if not pending:
                ch["name"] = line
            channels.append(ch)
            pending = None

    return channels


class ParseRequest(BaseModel):
    url: str


class ParseFromTextRequest(BaseModel):
    content: str


@router.post("/parse")
async def parse_m3u_url(request: ParseRequest) -> dict:
    """Fetch and parse an M3U playlist from a URL, returning a structured channel list."""
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "Symon_MoE/1.0 IPTV-Parser"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(request.url)
            resp.raise_for_status()
            content = resp.text
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch playlist ({exc.response.status_code}): {request.url}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Network error: {exc}") from exc

    channels = _parse_m3u_python(content)
    groups = sorted({c.get("group") or "Uncategorised" for c in channels})
    return {
        "source": request.url,
        "total": len(channels),
        "groups": groups,
        "channels": channels,
    }


@router.post("/parse/text")
async def parse_m3u_text(request: ParseFromTextRequest) -> dict:
    """Parse a raw M3U playlist string, returning a structured channel list."""
    channels = _parse_m3u_python(request.content)
    groups = sorted({c.get("group") or "Uncategorised" for c in channels})
    return {
        "source": "(text)",
        "total": len(channels),
        "groups": groups,
        "channels": channels,
    }
