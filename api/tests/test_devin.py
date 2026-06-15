import os

import httpx
import pytest
import respx

from app import devin

os.environ.setdefault("DEVIN_API_KEY", "fake-key")


@pytest.mark.asyncio
class TestCreateSession:
    @respx.mock
    async def test_returns_session_dict(self):
        mock_response = {
            "session_id": "sess-123",
            "url": "https://app.devin.ai/sessions/sess-123",
            "is_new_session": True,
        }
        respx.post(f"{devin.BASE}/sessions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await devin.create_session(prompt="Fix bug", title="Fix #1")
        assert result == mock_response

    @respx.mock
    async def test_sends_prompt_and_title(self):
        route = respx.post(f"{devin.BASE}/sessions").mock(
            return_value=httpx.Response(200, json={"session_id": "x", "url": "u"})
        )

        await devin.create_session(prompt="do stuff", title="My Title")

        request = route.calls.last.request
        body = request.read()
        import json

        payload = json.loads(body)
        assert payload["prompt"] == "do stuff"
        assert payload["title"] == "My Title"
        assert payload["idempotent"] is True

    @respx.mock
    async def test_omits_title_when_none(self):
        route = respx.post(f"{devin.BASE}/sessions").mock(
            return_value=httpx.Response(200, json={"session_id": "x", "url": "u"})
        )

        await devin.create_session(prompt="p")

        payload = __import__("json").loads(route.calls.last.request.read())
        assert "title" not in payload

    @respx.mock
    async def test_raises_on_http_error(self):
        respx.post(f"{devin.BASE}/sessions").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with pytest.raises(httpx.HTTPStatusError):
            await devin.create_session(prompt="p")

    @respx.mock
    async def test_sends_auth_header(self):
        route = respx.post(f"{devin.BASE}/sessions").mock(
            return_value=httpx.Response(200, json={"session_id": "x", "url": "u"})
        )

        await devin.create_session(prompt="p")

        auth = route.calls.last.request.headers["Authorization"]
        assert auth == f"Bearer {os.environ['DEVIN_API_KEY']}"


@pytest.mark.asyncio
class TestGetSession:
    @respx.mock
    async def test_returns_session_info(self):
        mock_response = {
            "session_id": "sess-1",
            "status_enum": "finished",
            "pull_request": {"url": "https://github.com/pr/1"},
        }
        respx.get(f"{devin.BASE}/sessions/sess-1").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await devin.get_session("sess-1")
        assert result["status_enum"] == "finished"
        assert result["pull_request"]["url"] == "https://github.com/pr/1"

    @respx.mock
    async def test_raises_on_404(self):
        respx.get(f"{devin.BASE}/sessions/bad").mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        with pytest.raises(httpx.HTTPStatusError):
            await devin.get_session("bad")
