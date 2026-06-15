import asyncio
import os

from shared.config import TERMINAL_STATUSES

from . import db, devin

INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "30"))


async def run_forever() -> None:
    """Background loop: poll in-flight sessions, record PR URLs and terminal statuses."""
    while True:
        try:
            for row in db.open_sessions():
                info = await devin.get_session(row["session_id"])
                status = info.get("status_enum") or info.get("status") or "working"
                pr = info.get("pull_request") or {}
                pr_url = pr.get("url") if isinstance(pr, dict) else None
                if status in TERMINAL_STATUSES or pr_url:
                    db.update_status(row["session_id"], status, pr_url)
        except Exception as e:
            print(f"[poller] error: {e}", flush=True)
        await asyncio.sleep(INTERVAL)
