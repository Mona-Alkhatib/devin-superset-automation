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


async def _request(method: str, path: str, **kwargs: object) -> dict:
    """Send a request to the Devin API and return the parsed JSON response."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.request(method, f"{BASE}{path}", headers=_headers(), **kwargs)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            logger.error(
                "Devin %s %s failed: %s %s", method, path, r.status_code, r.text
            )
            raise
        return r.json()


async def create_session(prompt: str, title: str | None = None) -> dict:
    """POST /v1/sessions"""
    body: dict = {"prompt": prompt, "idempotent": False}
    if title:
        body["title"] = title
    return await _request("POST", "/sessions", json=body)


async def get_session(session_id: str) -> dict:
    """GET /v1/sessions/{session_id}"""
    return await _request("GET", f"/sessions/{session_id}")
