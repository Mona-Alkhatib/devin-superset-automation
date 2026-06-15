import asyncio
import hashlib
import hmac
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request

from . import db, devin, poller

WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"].encode()
GITHUB_REPO = os.environ["GITHUB_REPO"]


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


def build_prompt(issue: dict) -> str:
    return (
        f"You are working on the GitHub repository {GITHUB_REPO}.\n"
        f"Clone it, read issue #{issue['number']}: {issue['html_url']}\n\n"
        f"The issue body contains the problem, evidence, acceptance criteria, "
        f"and out-of-scope items. Follow it strictly.\n\n"
        f"Workflow:\n"
        f"1. Create a feature branch named `devin/issue-{issue['number']}`.\n"
        f"2. Implement the change described in the issue.\n"
        f"3. Run the verification commands listed in the issue's acceptance criteria.\n"
        f"4. Commit and push the branch.\n"
        f"5. Open a pull request against `master` and link it to the issue "
        f"with `Closes #{issue['number']}`.\n\n"
        f"Constraints:\n"
        f"- Keep the diff minimal — only what the issue requires.\n"
        f"- Do not touch files marked out-of-scope in the issue.\n"
        f"- Stop and ask if a step is ambiguous; do not invent requirements."
    )


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
            title = f"Fix #{issue['number']}: {issue['title']}"
            session = await devin.create_session(
                prompt=build_prompt(issue),
                title=title,
            )
            db.record_session(
                session_id=session["session_id"],
                issue_number=issue["number"],
                issue_url=issue["html_url"],
                session_url=session.get("url"),
            )
            return {
                "status": "dispatched",
                "session_id": session["session_id"],
                "session_url": session.get("url"),
            }

    return {"status": "ignored"}


@app.get("/sessions")
def list_sessions():
    return db.all_sessions()


@app.get("/healthz")
def health():
    return {"ok": True}
