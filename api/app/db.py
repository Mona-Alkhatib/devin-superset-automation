import logging
import os
import sqlite3
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DB_PATH = os.environ["DB_PATH"]


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                issue_number INTEGER,
                issue_url    TEXT,
                session_url  TEXT,
                status       TEXT DEFAULT 'working',
                pr_url       TEXT,
                created_at   TEXT,
                updated_at   TEXT
            )
            """
        )
    logger.info("Database initialised at %s", DB_PATH)


def record_session(
    session_id: str,
    issue_number: int,
    issue_url: str,
    session_url: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cursor = c.execute(
            "INSERT OR IGNORE INTO sessions "
            "(session_id, issue_number, issue_url, session_url, status, pr_url, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'working', NULL, ?, ?)",
            (session_id, issue_number, issue_url, session_url, now, now),
        )
        if cursor.rowcount == 0:
            logger.warning(
                "Duplicate session %s for issue #%s — insert skipped",
                session_id,
                issue_number,
            )


def update_status(session_id: str, status: str, pr_url: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cursor = c.execute(
            "UPDATE sessions SET status=?, pr_url=COALESCE(?, pr_url), updated_at=? "
            "WHERE session_id=?",
            (status, pr_url, now, session_id),
        )
        if cursor.rowcount == 0:
            logger.warning(
                "update_status: session %s not found in DB", session_id
            )


def open_sessions() -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM sessions "
            "WHERE status NOT IN ('finished', 'blocked', 'expired')"
        )]


def all_sessions() -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM sessions ORDER BY created_at DESC"
        )]
