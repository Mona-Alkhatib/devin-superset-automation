import time

import pandas as pd
import streamlit as st

from shared.config import TERMINAL_STATUSES
from shared.db import all_sessions

EMPTY_COLUMNS = [
    "session_id", "issue_number", "issue_url", "session_url",
    "status", "pr_url", "created_at", "updated_at",
]

st.set_page_config(page_title="Devin Automation", layout="wide")
st.title("Devin Remediation Pipeline")
st.caption("Event-driven Devin automation against the forked Apache Superset repo.")

try:
    rows = all_sessions()
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=EMPTY_COLUMNS)
except Exception as exc:
    st.warning(f"Could not read sessions from the database: {exc}")
    df = pd.DataFrame(columns=EMPTY_COLUMNS)

in_flight = int((~df["status"].isin(TERMINAL_STATUSES)).sum()) if len(df) else 0
finished  = int((df["status"] == "finished").sum()) if len(df) else 0
prs       = int(df["pr_url"].notna().sum()) if len(df) else 0
blocked   = int(df["status"].isin({"blocked", "expired"}).sum()) if len(df) else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total sessions", len(df))
c2.metric("In flight", in_flight)
c3.metric("Finished", finished)
c4.metric("PRs opened", prs)
c5.metric("Blocked / expired", blocked)

st.subheader("Sessions")
if len(df):
    display = df.copy()
    if "session_url" in display.columns:
        display = display[[
            "issue_number", "status", "pr_url", "session_url",
            "issue_url", "created_at", "updated_at", "session_id",
        ]]
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "pr_url":      st.column_config.LinkColumn("PR"),
            "issue_url":   st.column_config.LinkColumn("Issue"),
            "session_url": st.column_config.LinkColumn("Devin session"),
        },
    )
else:
    st.info("No sessions yet. Label an issue with `devin-fix` to dispatch one.")

st.caption(f"Auto-refreshing every 10s — last refresh {time.strftime('%H:%M:%S')}")
time.sleep(10)
st.rerun()
