import os

import pytest

# Set required env vars before any app module is imported.
os.environ.setdefault("DB_PATH", ":memory:")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("GITHUB_REPO", "Mona-Alkhatib/fork_superset")
os.environ.setdefault("DEVIN_API_KEY", "fake-key")
os.environ.setdefault("POLL_INTERVAL_SECONDS", "1")


@pytest.fixture()
def tmp_db(tmp_path):
    """Yield a temporary SQLite path and patch DB_PATH in the db module."""
    db_file = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = db_file

    from app import db  # noqa: E402  (import after env is set)

    # Reload the module-level DB_PATH constant
    db.DB_PATH = db_file
    db.init()
    yield db_file
