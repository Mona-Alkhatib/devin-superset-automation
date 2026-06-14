import asyncio
import hashlib
import hmac
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request

from . import db, devin, poller

WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"].encode()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    task = asyncio.create_task(poller.run_forever())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(lifespan=lifespan, title="Devin Superset Automation")


def verify_signature(body: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(...),
    x_github_event: str = Header(...),
):
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(401, "bad signature")

    payload = await request.json()

    if x_github_event == "issues" and payload.get("action") == "labeled":
        label_name = payload.get("label", {}).get("name", "")
        if label_name == "devin-fix":
            issue = payload["issue"]
            repo = os.environ["GITHUB_REPO"]
            prompt = (
                f"You are remediating issue #{issue['number']} in {repo}. "
                f"Issue URL: {issue['html_url']}. "
                f"Read the issue, implement the fix on a feature branch, "
                f"and open a pull request against the default branch."
            )
            session_id = await devin.create_session(prompt=prompt, repo=repo)
            db.record_session(session_id, issue["number"], issue["html_url"])
            return {"status": "dispatched", "session_id": session_id}

    return {"status": "ignored"}


@app.get("/sessions")
def list_sessions():
    return db.all_sessions()


@app.get("/healthz")
def health():
    return {"ok": True}
