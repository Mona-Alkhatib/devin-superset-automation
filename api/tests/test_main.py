import hashlib
import hmac
import json
import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("GITHUB_REPO", "Mona-Alkhatib/fork_superset")
os.environ.setdefault("DEVIN_API_KEY", "fake-key")
os.environ.setdefault("DB_PATH", ":memory:")

from app.main import build_prompt, verify_signature


# ---------------------------------------------------------------------------
# verify_signature
# ---------------------------------------------------------------------------
class TestVerifySignature:
    def _sign(self, body: bytes) -> str:
        secret = os.environ["GITHUB_WEBHOOK_SECRET"].encode()
        return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()

    def test_valid_signature(self):
        body = b'{"action":"labeled"}'
        sig = self._sign(body)
        assert verify_signature(body, sig) is True

    def test_invalid_signature(self):
        assert verify_signature(b"body", "sha256=badhex") is False

    def test_empty_body(self):
        body = b""
        sig = self._sign(body)
        assert verify_signature(body, sig) is True


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------
class TestBuildPrompt:
    def test_contains_issue_number_and_url(self):
        issue = {"number": 42, "title": "Fix CVE", "html_url": "https://gh/42"}
        prompt = build_prompt(issue)
        assert "#42" in prompt
        assert "https://gh/42" in prompt

    def test_contains_repo_name(self):
        issue = {"number": 1, "title": "T", "html_url": "u"}
        prompt = build_prompt(issue)
        assert os.environ["GITHUB_REPO"] in prompt

    def test_contains_workflow_steps(self):
        issue = {"number": 1, "title": "T", "html_url": "u"}
        prompt = build_prompt(issue)
        assert "feature branch" in prompt.lower() or "devin/issue-1" in prompt
        assert "pull request" in prompt.lower()


# ---------------------------------------------------------------------------
# API endpoints via TestClient (lifespan disabled to avoid real poller/db)
# ---------------------------------------------------------------------------
@pytest.fixture()
def client(tmp_db):
    """Create a TestClient with lifespan disabled."""
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestHealthEndpoint:
    def test_healthz(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


class TestSessionsEndpoint:
    def test_empty(self, client):
        resp = client.get("/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_recorded_sessions(self, client, tmp_db):
        from app import db

        db.record_session("s1", 1, "u", "su")
        resp = client.get("/sessions")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["session_id"] == "s1"


class TestWebhookEndpoint:
    def _sign(self, body: bytes) -> str:
        secret = os.environ["GITHUB_WEBHOOK_SECRET"].encode()
        return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()

    def test_rejects_bad_signature(self, client):
        payload = json.dumps({"action": "labeled"}).encode()
        resp = client.post(
            "/webhooks/github",
            content=payload,
            headers={
                "X-Hub-Signature-256": "sha256=bad",
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401

    def test_ignores_non_issue_event(self, client):
        payload = json.dumps({"action": "opened"}).encode()
        sig = self._sign(payload)
        resp = client.post(
            "/webhooks/github",
            content=payload,
            headers={
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_ignores_non_labeled_action(self, client):
        payload = json.dumps({"action": "opened"}).encode()
        sig = self._sign(payload)
        resp = client.post(
            "/webhooks/github",
            content=payload,
            headers={
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_ignores_wrong_label(self, client):
        payload = json.dumps({
            "action": "labeled",
            "label": {"name": "bug"},
            "issue": {"number": 1, "title": "T", "html_url": "u"},
        }).encode()
        sig = self._sign(payload)
        resp = client.post(
            "/webhooks/github",
            content=payload,
            headers={
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @patch("app.devin.create_session", new_callable=AsyncMock)
    def test_dispatches_devin_session(self, mock_create, client):
        mock_create.return_value = {
            "session_id": "sess-abc",
            "url": "https://devin/sess-abc",
        }
        payload = json.dumps({
            "action": "labeled",
            "label": {"name": "devin-fix"},
            "issue": {
                "number": 99,
                "title": "Bump pyarrow",
                "html_url": "https://gh/issues/99",
            },
        }).encode()
        sig = self._sign(payload)
        resp = client.post(
            "/webhooks/github",
            content=payload,
            headers={
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "dispatched"
        assert body["session_id"] == "sess-abc"
        mock_create.assert_called_once()
