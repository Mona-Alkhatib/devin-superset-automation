import asyncio
import logging
import os
import re

from . import db, devin

logger = logging.getLogger(__name__)

INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "30"))

# From Devin API v1 status_enum:
# working, blocked, expired, finished, suspend_requested,
# suspend_requested_frontend, resume_requested, resume_requested_frontend, resumed
TERMINAL_STATUSES = {"finished", "blocked", "expired"}

PR_URL_RE = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/pull/\d+")


def _extract_pr_url(info: dict) -> str | None:
    pr = info.get("pull_request") or {}
    if isinstance(pr, dict) and pr.get("url"):
        return pr["url"]
    for msg in info.get("messages") or []:
        text = msg.get("message") or ""
        m = PR_URL_RE.search(text)
        if m:
            return m.group(0)
    return None


async def _poll_session(row: dict) -> None:
    """Poll a single session and update the DB on terminal status or PR URL."""
    session_id = row["session_id"]
    try:
        info = await devin.get_session(session_id)
    except Exception:
        logger.exception("Failed to poll session %s", session_id)
        return

    status = info.get("status_enum") or info.get("status") or "working"
    pr_url = _extract_pr_url(info)
    if status in TERMINAL_STATUSES or pr_url:
        db.update_status(session_id, status, pr_url)
        logger.info("Session %s -> %s (pr=%s)", session_id, status, pr_url)


async def run_forever() -> None:
    """Background loop: poll in-flight sessions, record PR URLs and terminal statuses."""
    while True:
        try:
            sessions = db.open_sessions()
        except Exception:
            logger.exception("Failed to query open sessions from DB")
            await asyncio.sleep(INTERVAL)
            continue

        for row in sessions:
            await _poll_session(row)

        await asyncio.sleep(INTERVAL)
