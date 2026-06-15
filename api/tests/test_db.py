import sqlite3

from app import db


class TestInit:
    def test_creates_sessions_table(self, tmp_db):
        conn = sqlite3.connect(tmp_db)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        assert cur.fetchone() is not None
        conn.close()

    def test_idempotent(self, tmp_db):
        db.init()  # second call should not raise
        conn = sqlite3.connect(tmp_db)
        tables = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='sessions'"
        ).fetchone()[0]
        assert tables == 1
        conn.close()


class TestRecordSession:
    def test_inserts_row(self, tmp_db):
        db.record_session("s1", 42, "https://gh/issues/42", "https://devin/s1")
        rows = db.all_sessions()
        assert len(rows) == 1
        row = rows[0]
        assert row["session_id"] == "s1"
        assert row["issue_number"] == 42
        assert row["issue_url"] == "https://gh/issues/42"
        assert row["session_url"] == "https://devin/s1"
        assert row["status"] == "working"
        assert row["pr_url"] is None

    def test_ignores_duplicate(self, tmp_db):
        db.record_session("dup", 1, "u", "su")
        db.record_session("dup", 1, "u", "su")
        assert len(db.all_sessions()) == 1

    def test_nullable_session_url(self, tmp_db):
        db.record_session("s2", 10, "url")
        row = db.all_sessions()[0]
        assert row["session_url"] is None


class TestUpdateStatus:
    def test_updates_status_and_pr(self, tmp_db):
        db.record_session("s1", 1, "u")
        db.update_status("s1", "finished", "https://pr/1")
        row = db.all_sessions()[0]
        assert row["status"] == "finished"
        assert row["pr_url"] == "https://pr/1"

    def test_preserves_existing_pr_when_none_passed(self, tmp_db):
        db.record_session("s1", 1, "u")
        db.update_status("s1", "finished", "https://pr/1")
        db.update_status("s1", "blocked")
        row = db.all_sessions()[0]
        assert row["status"] == "blocked"
        assert row["pr_url"] == "https://pr/1"

    def test_updates_updated_at(self, tmp_db):
        db.record_session("s1", 1, "u")
        before = db.all_sessions()[0]["updated_at"]
        db.update_status("s1", "finished")
        after = db.all_sessions()[0]["updated_at"]
        assert after >= before


class TestOpenSessions:
    def test_returns_only_non_terminal(self, tmp_db):
        db.record_session("working1", 1, "u")
        db.record_session("working2", 2, "u")
        db.record_session("done", 3, "u")
        db.update_status("done", "finished")

        open_rows = db.open_sessions()
        ids = {r["session_id"] for r in open_rows}
        assert ids == {"working1", "working2"}

    def test_excludes_blocked_and_expired(self, tmp_db):
        db.record_session("b", 1, "u")
        db.record_session("e", 2, "u")
        db.update_status("b", "blocked")
        db.update_status("e", "expired")
        assert db.open_sessions() == []


class TestAllSessions:
    def test_returns_all_ordered_by_created_at_desc(self, tmp_db):
        db.record_session("a", 1, "u")
        db.record_session("b", 2, "u")
        rows = db.all_sessions()
        assert len(rows) == 2
        # Most recent first
        assert rows[0]["session_id"] == "b"
