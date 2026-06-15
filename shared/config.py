import os

DB_PATH: str = os.environ.get("DB_PATH", "/data/automation.db")

TERMINAL_STATUSES: frozenset[str] = frozenset({"finished", "blocked", "expired"})
