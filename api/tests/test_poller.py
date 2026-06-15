import os
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("GITHUB_REPO", "Mona-Alkhatib/fork_superset")
os.environ.setdefault("DEVIN_API_KEY", "fake-key")
os.environ.setdefault("POLL_INTERVAL_SECONDS", "1")

from app import poller


class TestTerminalStatuses:
    def test_finished_is_terminal(self):
        assert "finished" in poller.TERMINAL_STATUSES

    def test_blocked_is_terminal(self):
        assert "blocked" in poller.TERMINAL_STATUSES

    def test_expired_is_terminal(self):
        assert "expired" in poller.TERMINAL_STATUSES

    def test_working_is_not_terminal(self):
        assert "working" not in poller.TERMINAL_STATUSES


@pytest.mark.asyncio
class TestRunForever:
    @patch("app.devin.get_session", new_callable=AsyncMock)
    @patch("app.db.open_sessions")
    @patch("app.db.update_status")
    async def test_updates_finished_session(
        self, mock_update, mock_open, mock_get
    ):
        mock_open.return_value = [{"session_id": "s1"}]
        mock_get.return_value = {
            "status_enum": "finished",
            "pull_request": {"url": "https://pr/1"},
        }

        # Run one iteration by cancelling after the first loop
        import asyncio

        task = asyncio.create_task(poller.run_forever())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_get.assert_called_once_with("s1")
        mock_update.assert_called_once_with("s1", "finished", "https://pr/1")

    @patch("app.devin.get_session", new_callable=AsyncMock)
    @patch("app.db.open_sessions")
    @patch("app.db.update_status")
    async def test_skips_still_working_session(
        self, mock_update, mock_open, mock_get
    ):
        mock_open.return_value = [{"session_id": "s2"}]
        mock_get.return_value = {
            "status_enum": "working",
            "pull_request": None,
        }

        import asyncio

        task = asyncio.create_task(poller.run_forever())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_update.assert_not_called()

    @patch("app.devin.get_session", new_callable=AsyncMock)
    @patch("app.db.open_sessions")
    @patch("app.db.update_status")
    async def test_updates_when_pr_present_even_if_not_terminal(
        self, mock_update, mock_open, mock_get
    ):
        mock_open.return_value = [{"session_id": "s3"}]
        mock_get.return_value = {
            "status_enum": "working",
            "pull_request": {"url": "https://pr/3"},
        }

        import asyncio

        task = asyncio.create_task(poller.run_forever())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_update.assert_called_once_with("s3", "working", "https://pr/3")

    @patch("app.devin.get_session", new_callable=AsyncMock)
    @patch("app.db.open_sessions")
    @patch("app.db.update_status")
    async def test_handles_api_error_gracefully(
        self, mock_update, mock_open, mock_get
    ):
        mock_open.return_value = [{"session_id": "s4"}]
        mock_get.side_effect = Exception("API timeout")

        import asyncio

        task = asyncio.create_task(poller.run_forever())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should not crash; update should not be called
        mock_update.assert_not_called()

    @patch("app.devin.get_session", new_callable=AsyncMock)
    @patch("app.db.open_sessions")
    @patch("app.db.update_status")
    async def test_handles_non_dict_pull_request(
        self, mock_update, mock_open, mock_get
    ):
        mock_open.return_value = [{"session_id": "s5"}]
        mock_get.return_value = {
            "status_enum": "finished",
            "pull_request": "not-a-dict",
        }

        import asyncio

        task = asyncio.create_task(poller.run_forever())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_update.assert_called_once_with("s5", "finished", None)

    @patch("app.devin.get_session", new_callable=AsyncMock)
    @patch("app.db.open_sessions")
    @patch("app.db.update_status")
    async def test_fallback_status_when_missing(
        self, mock_update, mock_open, mock_get
    ):
        mock_open.return_value = [{"session_id": "s6"}]
        mock_get.return_value = {}

        import asyncio

        task = asyncio.create_task(poller.run_forever())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # status defaults to "working", no pr — should not update
        mock_update.assert_not_called()
