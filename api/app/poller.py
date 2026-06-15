import asyncio
import os
import re

from shared.config import TERMINAL_STATUSES

from . import db, devin

INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "30"))

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


async def run_forever() -> None:
    """Background loop: poll in-flight sessions, record PR URLs and terminal statuses."""
    while True:
        try:
            for row in db.open_sessions():
                info = await devin.get_session(row["session_id"])
                status = info.get("status_enum") or info.get("status") or "working"
                pr_url = _extract_pr_url(info)
                if status in TERMINAL_STATUSES or pr_url:
                    db.update_status(row["session_id"], status, pr_url)
        except Exception as e:
            print(f"[poller] error: {e}", flush=True)
        await asyncio.sleep(INTERVAL)
