# Devin Superset Automation

Event-driven automation that watches a forked Apache Superset repo for issues
labeled `devin-fix` and dispatches Devin API sessions to remediate them. Each
session is tracked in SQLite and surfaced on a Streamlit dashboard.

## Architecture

```
GitHub Issue (labeled `devin-fix`)
       │  webhook
       ▼
FastAPI  ──► Devin API (create session)
   │              │
   │              ▼
   │         Devin runs, opens PR
   ▼              │
SQLite ◄── Poller polls session status, records PR URL
   ▲
   │
Streamlit dashboard
```

- **api/**       — FastAPI service: webhook receiver + background poller
- **dashboard/** — Streamlit UI showing sessions + metrics
- **data/**      — SQLite DB volume (gitignored)

## Run locally

1. Copy env file and fill in `DEVIN_API_KEY`:
   ```bash
   cp .env.example .env
   # edit .env
   ```
2. Boot the stack:
   ```bash
   docker compose up --build
   ```
3. Open:
   - API docs:  http://localhost:8000/docs
   - Dashboard: http://localhost:8501

## Connect the GitHub webhook

The FastAPI service needs a public URL. Easiest path:

```bash
ngrok http 8000
```

Then in your forked Superset repo:

1. **Settings → Webhooks → Add webhook**
2. Payload URL: `https://<your-ngrok-id>.ngrok.io/webhooks/github`
3. Content type: `application/json`
4. Secret: same value as `GITHUB_WEBHOOK_SECRET` in `.env`
5. Events: **Issues** only
6. Save.

## Demo flow

1. Create an issue in your forked Superset repo (e.g., "Bump `pyarrow` to fix CVE-XXXX").
2. Add the label `devin-fix` to the issue.
3. The webhook fires → FastAPI dispatches a Devin session.
4. The dashboard at :8501 shows the session as **running**.
5. The poller flips the row to **finished** with a PR URL once Devin opens the PR.

## Triggers supported

| Trigger | Status |
|---|---|
| GitHub webhook (issue labeled `devin-fix`) | ✅ primary |
| Scheduled sweeper (catch missed issues) | optional extension |

## Observability

- **Per-session row** in SQLite: session id, issue, status, PR URL, timestamps.
- **Dashboard** (Streamlit): total / running / finished / PRs-opened metrics + table.
- **API**: `GET /sessions` for raw JSON, `GET /healthz` for liveness.

## Configuration

| Env var | Description |
|---|---|
| `DEVIN_API_KEY` | Devin API token |
| `GITHUB_WEBHOOK_SECRET` | Shared secret for HMAC signature verification |
| `GITHUB_REPO` | Forked repo, e.g., `Mona-Alkhatib/fork_superset` |
| `DB_PATH` | SQLite path (default `/data/automation.db`) |
| `POLL_INTERVAL_SECONDS` | Poll cadence for in-flight sessions |

## Notes

- Devin API endpoint paths in `api/app/devin.py` are best-guess placeholders.
  Verify against https://docs.devin.ai/api-reference/overview and adjust.
- Force-pushing, force-merging, and any destructive GitHub ops should remain
  manual — Devin only opens PRs; humans review and merge.
