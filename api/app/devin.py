"""
Thin Devin API v1 client.

Spec: https://docs.devin.ai/api-reference/v1/sessions/create-a-new-devin-session
      https://docs.devin.ai/api-reference/v1/sessions/retrieve-details-about-an-existing-session
"""
import os
import httpx

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
        r.raise_for_status()
        return r.json()


async def get_session(session_id: str) -> dict:
    """
    GET /v1/sessions/{session_id}
    Returns full session including: status, status_enum, pull_request (nullable {url}).
    """
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{BASE}/sessions/{session_id}", headers=_headers())
        r.raise_for_status()
        return r.json()
