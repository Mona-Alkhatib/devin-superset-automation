import os
import sqlite3

import pandas as pd
import streamlit as st

DB_PATH = os.environ["DB_PATH"]

st.set_page_config(page_title="Devin Automation", layout="wide")
st.title("Devin Remediation Pipeline")
st.caption("Event-driven Devin automation against the forked Apache Superset repo.")

try:
    with sqlite3.connect(DB_PATH) as c:
        df = pd.read_sql_query(
            "SELECT * FROM sessions ORDER BY created_at DESC", c
        )
except (sqlite3.OperationalError, pd.errors.DatabaseError):
    df = pd.DataFrame(
        columns=["session_id", "issue_number", "issue_url", "status",
                 "pr_url", "created_at", "updated_at"]
    )

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total sessions", len(df))
c2.metric("Running", int((df["status"] == "running").sum()) if len(df) else 0)
c3.metric("Finished", int((df["status"] == "finished").sum()) if len(df) else 0)
c4.metric("PRs opened", int(df["pr_url"].notna().sum()) if len(df) else 0)

st.subheader("Sessions")
if len(df):
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No sessions yet. Label an issue with `devin-fix` to dispatch one.")

st.caption("Refresh the page to see new sessions.")
