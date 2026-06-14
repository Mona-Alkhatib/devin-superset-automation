"""
Thin Devin API client.

NOTE: verify exact endpoint paths and request/response shapes against
https://docs.devin.ai/api-reference/overview — names below are best-guess
placeholders. Adjust create_session / get_session as needed.
"""
import os
import httpx

BASE = "https://api.devin.ai/v1"


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.environ['DEVIN_API_KEY']}"}


async def create_session(prompt: str, repo: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{BASE}/sessions",
            headers=_headers(),
            json={"prompt": prompt, "idempotent": True},
        )
        r.raise_for_status()
        data = r.json()
        return data.get("session_id") or data["id"]


async def get_session(session_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{BASE}/session/{session_id}",
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()
