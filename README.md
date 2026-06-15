# Devin Superset Automation

> Event-driven automation that turns labeled GitHub issues into autonomous
> Devin sessions, opens pull requests on a forked Apache Superset, and
> surfaces real-time progress for engineering leadership.

**What it solves.** Mechanical code-modernization work (deprecation cleanups,
PEP 585/604 typing migrations, dependency bumps) eats engineering time without
moving the product forward. This system routes that backlog to Devin and gives
leadership a single screen to answer *"is the automation working?"*.

**Who it's for.** A VP of Engineering evaluating Devin as a long-term primitive
in their developer-experience stack, and the senior ICs who'd own the integration.

---

## Architecture

```
                                                ┌───────────────────────┐
   GitHub Issue labeled `devin-fix`             │  Devin API (v1)       │
                │                               │  api.devin.ai/v1      │
                │ webhook                       └───────────▲───────────┘
                ▼                                           │
        ┌───────────────┐    create session   ┌─────────────┴──────────┐
        │  smee.io      │ ──────────────────▶ │  FastAPI               │
        │  (tunnel)     │                     │  POST /webhooks/github │
        └───────┬───────┘                     │  - HMAC verification   │
                │                             │  - Prompt builder      │
                │ forward                     │  - Background poller   │
                ▼                             └────────┬───────────────┘
        ┌───────────────┐                              │
        │  smee-client  │                              │ insert / update
        │  (local)      │                              ▼
        └───────────────┘                     ┌────────────────────────┐
                                              │  SQLite (./data)       │
                                              │  sessions table        │
                                              └────────┬───────────────┘
                                                       │
                                                       │ read
                                                       ▼
                                              ┌────────────────────────┐
                                              │  Streamlit dashboard   │
                                              │  metrics + links       │
                                              └────────────────────────┘
```

**Components**

| Path | Role |
|---|---|
| `api/`       | FastAPI: webhook receiver, Devin client, background poller |
| `dashboard/` | Streamlit UI: 5 metrics + clickable session/PR/issue links |
| `data/`      | SQLite volume (gitignored) |

---

## Remediation targets (this demo)

The system was pointed at these three issues on
[`Mona-Alkhatib/fork_superset`](https://github.com/Mona-Alkhatib/fork_superset/issues):

| # | Title | Why it matters |
|---|---|---|
| 1 | Replace deprecated `datetime.utcnow()` (27 call sites) | Python 3.12+ deprecation; naive datetimes are a recurring tz-bug source |
| 2 | Adopt PEP 585 built-in generics in `superset/utils/` | `typing.List/Dict/...` soft-deprecated since 3.9 |
| 3 | Adopt PEP 604 union syntax in `superset/utils/` | `Optional[X]` → `X \| None`, enforced by `ruff` UP007 |

Each issue body is written as a strict spec for Devin — problem, evidence,
acceptance criteria with verification commands, and explicit "out of scope".

---

## Quickstart

### 0. Prerequisites
- Docker + Docker Compose (tested with OrbStack)
- A Devin API key (`apk_user_*` personal key works)
- A GitHub fork of `apache/superset` with Issues enabled and a `devin-fix` label

### 1. Configure

```bash
git clone https://github.com/Mona-Alkhatib/devin-superset-automation.git
cd devin-superset-automation
cp .env.example .env
# Open .env and fill in DEVIN_API_KEY + GITHUB_WEBHOOK_SECRET
```

### 2. Boot the stack

```bash
docker compose up --build
```

Then open:
- API docs:  http://localhost:8000/docs
- Sessions:  http://localhost:8000/sessions
- Dashboard: http://localhost:8501

### 3. Expose the webhook

Easiest path (no signup), using GitHub's webhook proxy:

```bash
# 1. Open https://smee.io/new in a browser to get a tunnel URL
# 2. Install the forwarder once
npm install -g smee-client

# 3. Forward smee.io traffic to your local FastAPI
smee --url https://smee.io/<YOUR-ID> --target http://localhost:8000/webhooks/github
```

### 4. Register the webhook on the fork

```bash
gh api repos/<YOU>/<FORK>/hooks \
  --method POST \
  --raw-field name=web \
  --field active=true \
  --raw-field 'events[]=issues' \
  --raw-field "config[url]=https://smee.io/<YOUR-ID>" \
  --raw-field 'config[content_type]=json' \
  --raw-field "config[secret]=$GITHUB_WEBHOOK_SECRET"
```

### 5. Dispatch a remediation

```bash
gh issue edit <N> --repo <YOU>/<FORK> --add-label "devin-fix"
```

Within seconds the dashboard shows a new session row. Within minutes Devin
opens a PR; the row picks up the PR URL automatically.

---

## Observability — "How would an engineering leader know this is working?"

The dashboard answers four leadership-level questions at a glance:

| Metric | What it tells the VP |
|---|---|
| **Total sessions** | Throughput — how much work has been dispatched |
| **In flight** | Capacity — are agents currently busy? |
| **Finished** | Success volume |
| **PRs opened** | The only metric that matters for *delivered* value |
| **Blocked / expired** | Failure signal — when does Devin need a human? |

Plus a per-row table with clickable links to:
- the originating **GitHub issue**,
- the **Devin session** (live stream of what the agent is doing),
- and the resulting **pull request**.

For deeper analysis the API exposes `GET /sessions` as raw JSON, suitable for
piping into any data warehouse or BI tool.

---

## Why Devin (and not a script)?

The three issues in this demo could be done with `sed`. The real point of
this automation is the *next* set of issues — where a one-line `sed` isn't
enough but the work is still mechanical:

- "Replace `flask.g` accesses with the new request-scoped state helper"
- "Add type annotations to all public functions in `superset/db_engine_specs/`"
- "Bump `pandas` to 2.x and fix the resulting type errors"

These need code understanding, test running, and iteration — not text
substitution. Devin handles them autonomously and opens a reviewable PR.
The same scaffolding (webhook → session → dashboard) extends to all of them
without code changes; only the issue spec changes.

---

## Configuration

| Env var | Description |
|---|---|
| `DEVIN_API_KEY` | Devin API token (`apk_user_*` or `apk_*`) |
| `GITHUB_WEBHOOK_SECRET` | Shared secret for HMAC signature verification |
| `GITHUB_REPO` | Forked repo, e.g., `Mona-Alkhatib/fork_superset` |
| `DB_PATH` | SQLite path (default `/data/automation.db`) |
| `POLL_INTERVAL_SECONDS` | Poll cadence for in-flight sessions (default 30) |

---

## Limitations & honest trade-offs

- **No auth on the dashboard.** Fine for a localhost demo; needs SSO behind a reverse proxy in real use.
- **Single-tenant SQLite.** Good up to ~thousands of sessions; swap for Postgres for production.
- **Polling, not push.** Devin doesn't expose webhooks yet, so we poll every 30s. Easy migration once events ship.
- **Idempotency is on Devin's side.** We pass `idempotent: true` so the same issue+prompt won't double-dispatch, but the dashboard doesn't dedupe explicitly.

---

## Next steps (in a real customer engagement)

1. **Replace SQLite + Streamlit with Postgres + a real BI surface** (Looker / Superset itself) so leadership can slice success rates by repo, label, or engineer.
2. **Scanner integration**: feed Dependabot / Snyk / `pip-audit` findings directly as labeled issues — no human triage step.
3. **PR review gate**: on PR open, dispatch a second Devin session for self-review or hand off to a `code-reviewer` agent.
4. **Org-level rollout**: switch from personal v1 API to v3 organization endpoints with seat-level ACU budgets per team.
5. **Cost guardrails**: per-issue `max_acu_limit` driven by issue label (e.g., `complexity:s/m/l`).

---

## Project layout

```
devin-superset-automation/
├── README.md
├── docker-compose.yml
├── .env.example
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py        FastAPI: /webhooks/github, /sessions, /healthz
│       ├── devin.py       Devin v1 API client (create + get session)
│       ├── db.py          SQLite helpers
│       └── poller.py      Background task: polls in-flight sessions
└── dashboard/
    ├── Dockerfile
    ├── requirements.txt
    └── app.py             Streamlit dashboard (metrics + table)
```
