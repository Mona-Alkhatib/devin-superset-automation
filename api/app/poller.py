import asyncio
import os

from . import db, devin

INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "30"))
TERMINAL_STATUSES = {"finished", "stopped", "blocked", "expired", "failed"}


async def run_forever() -> None:
    while True:
        try:
            for row in db.open_sessions():
                info = await devin.get_session(row["session_id"])
                status = info.get("status_enum") or info.get("status") or "running"
                pr = info.get("pull_request") or {}
                pr_url = pr.get("url") if isinstance(pr, dict) else None
                if status in TERMINAL_STATUSES or pr_url:
                    db.update_status(
                        row["session_id"],
                        status if status in TERMINAL_STATUSES else "finished",
                        pr_url,
                    )
        except Exception as e:
            print(f"[poller] error: {e}", flush=True)
        await asyncio.sleep(INTERVAL)
