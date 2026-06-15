"""
Thin Devin API v1 client.

Spec: https://docs.devin.ai/api-reference/v1/sessions/create-a-new-devin-session
      https://docs.devin.ai/api-reference/v1/sessions/retrieve-details-about-an-existing-session
"""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

BASE = "https://api.devin.ai/v1"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['DEVIN_API_KEY']}",
        "Content-Type": "application/json",
    }


async def create_session(prompt: str, title: str | None = None) -> dict:
    """
    POST /v1/sessions
    Returns: {"session_id": str, "url": str, "is_new_session": bool | None}
    """
    body: dict = {"prompt": prompt, "idempotent": False}
    if title:
        body["title"] = title
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{BASE}/sessions", headers=_headers(), json=body)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            logger.error(
                "Devin create-session failed: %s %s", r.status_code, r.text
            )
            raise
        return r.json()


async def get_session(session_id: str) -> dict:
    """
    GET /v1/sessions/{session_id}
    Returns full session including: status, status_enum, pull_request (nullable {url}).
    """
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{BASE}/sessions/{session_id}", headers=_headers())
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            logger.error(
                "Devin get-session %s failed: %s %s",
                session_id,
                r.status_code,
                r.text,
            )
            raise
        return r.json()
