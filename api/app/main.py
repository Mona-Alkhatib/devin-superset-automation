import asyncio
import hashlib
import hmac
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from . import db, devin, poller

logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"].encode()
GITHUB_REPO = os.environ["GITHUB_REPO"]
API_TOKEN = os.environ.get("API_ACCESS_TOKEN", "")

# Disable interactive API docs in production; set ENABLE_DOCS=1 to re-enable.
_enable_docs = os.environ.get("ENABLE_DOCS", "0") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    task = asyncio.create_task(poller.run_forever())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    lifespan=lifespan,
    title="Devin Superset Automation",
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
)

# Explicit CORS: only allow the dashboard origin by default.
_allowed_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
_allowed_origins = [o.strip() for o in _allowed_origins if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


def _require_api_token(authorization: str = Header(default="")) -> None:
    """Lightweight bearer-token check for internal endpoints."""
    if not API_TOKEN:
        return  # no token configured — skip (local dev)
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(403, "forbidden")


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
            issue = payload.get("issue")
            if not issue:
                raise HTTPException(422, "payload missing 'issue' field")

            for key in ("number", "html_url", "title"):
                if key not in issue:
                    raise HTTPException(
                        422, f"issue object missing required '{key}' field"
                    )

            title = f"Fix #{issue['number']}: {issue['title']}"
            try:
                session = await devin.create_session(
                    prompt=build_prompt(issue),
                    title=title,
                )
            except Exception:
                logger.exception(
                    "Devin API call failed for issue #%s", issue["number"]
                )
                raise HTTPException(
                    502, "failed to create Devin session"
                ) from None

            session_id = session.get("session_id")
            if not session_id:
                logger.error(
                    "Devin API response missing session_id: %s", session
                )
                raise HTTPException(502, "Devin API returned no session_id")

            db.record_session(
                session_id=session_id,
                issue_number=issue["number"],
                issue_url=issue["html_url"],
                session_url=session.get("url"),
            )
            return {"status": "dispatched"}

    return {"status": "ignored"}


@app.get("/sessions")
def list_sessions(authorization: str = Header(default="")):
    _require_api_token(authorization)
    return db.all_sessions()


@app.get("/healthz")
def health():
    return {"ok": True}
