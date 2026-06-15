# Loom Script — Devin Superset Automation

**Audience:** VP of Engineering + 2-3 senior ICs evaluating Devin as a platform primitive.
**Length:** 5 minutes (~750 spoken words). Cut, don't extend.
**Tone:** Engineer-to-engineer. Concrete, not promotional.

---

## Tabs to have open before recording

1. **Forked Superset issues page** — https://github.com/Mona-Alkhatib/fork_superset/issues
2. **Dashboard** — http://localhost:8501
3. **Live Devin session** — https://app.devin.ai/sessions/b565f23f598846e69f43b0b5bc32328c
4. **The opened PR** — paste URL once it lands
5. **VS Code (or editor)** with `api/app/main.py` and `api/app/devin.py` open in tabs
6. **GitHub repo** — https://github.com/Mona-Alkhatib/devin-superset-automation

Set screen to a clean, neutral wallpaper. Close Slack/Mail notifications.

---

## 0:00 — Cold open (10s)

**[Show: forked Superset issues page]**

> "Hi. This is a 5-minute walkthrough of an event-driven Devin automation I
> built against Apache Superset. The goal — give engineering leaders a
> turnkey way to route their modernization backlog to an autonomous agent
> and see, on one screen, whether it's actually working."

---

## 0:10 — WHAT: The problem (60s)

**[Show: Superset repo on GitHub — scroll the issues page briefly]**

> "Here's the workflow problem I'm solving. Apache Superset is a 500K-line
> Python and TypeScript codebase. Like most large codebases, it carries a
> permanent tail of mechanical work — deprecation warnings, typing
> migrations, dependency CVEs. None of it ships product. All of it has to
> get done."

**[Click on Issue #1, scroll the issue body]**

> "I created three concrete examples here in my fork. Issue 1: replace 27
> calls to `datetime.utcnow()` with the timezone-aware equivalent — Python
> 3.12 deprecation. Issue 2 and 3: PEP 585 and 604 typing migrations
> scoped to `superset/utils/`. Each issue body is a strict spec — problem,
> evidence, acceptance criteria with verification commands, and explicit
> out-of-scope items."

**[Beat]**

> "Traditional answers are bad. ICs hate this work, so it slips. Or
> someone batches it into a 50-file PR no one reviews carefully. I want
> to make it disappear entirely from the human queue."

---

## 1:10 — HOW: The demo (2:30)

**[Show: dashboard at http://localhost:8501]**

> "Here's the dashboard. Five metrics top-down — total sessions, in
> flight, finished, PRs opened, blocked. If I were a VP, this is the
> screen that tells me 'the automation is working.' Each row is a Devin
> session with clickable links to the originating GitHub issue, the live
> Devin session, and the resulting pull request."

**[Point at the row with `expired` status]**

> "Quick aside on this expired row — it's not a bug, it's the system
> doing its job. My first dispatch hit a Devin GitHub integration with
> read-only access. The agent cloned the repo, read the issue, and
> immediately flagged the auth boundary instead of silently failing or
> hallucinating a PR. I fixed the integration, re-dispatched, and the
> new row is the real run."

**[Open editor: `api/app/main.py`]**

> "Architecture is three pieces. First, a FastAPI service receives
> GitHub webhooks at `/webhooks/github`. It verifies the HMAC signature
> with the shared secret, filters for `issues.labeled` events on the
> `devin-fix` label, and dispatches a Devin session."

**[Highlight `build_prompt` function]**

> "The prompt builder is deliberate — it tells Devin which repo to clone,
> which issue to read, what branch to create, and most importantly: stop
> and ask if a step is ambiguous. We don't want a hallucinated PR; we
> want a careful, scoped diff."

**[Switch to `api/app/devin.py`]**

> "The Devin client is thin — twenty lines. Create session, get session.
> v1 API. I disable idempotency so each label event yields a fresh
> session — the dashboard treats every dispatch as a discrete event."

**[Switch to `api/app/poller.py`]**

> "The poller is a single background asyncio task. Every 30 seconds it
> walks all in-flight sessions, calls Devin's GET endpoint, and updates
> our SQLite row with the latest status and PR URL. Devin's v1 API
> doesn't push webhooks back, so we poll — easy migration when they do."

**[Switch to live Devin session tab]**

> "Now — this is the actual session running right now. You can watch
> Devin's terminal stream. It's cloning, running grep to count
> occurrences, editing files, running tests. This is the part you can't
> get from `sed`."

**[Switch back to dashboard, refresh]**

> "When Devin opens the PR, the poller picks up the URL on its next tick
> and the row flips to `finished`. The PR column becomes a clickable
> link straight to the diff."

**[If PR has landed, click it — show the diff]**

> "Here's the PR Devin opened. Clean diff, 27 call sites updated, tests
> passing, body links back to the issue with `Closes #1`."

---

## 3:40 — WHY: Why Devin specifically (60s)

**[Show: README.md "Why Devin" section]**

> "Now — why use an autonomous coding agent here instead of a script?
> Honest answer: the three issues in this demo could be done with sed.
> The point isn't this demo. The point is the next class of issues."

**[Read off the list, slowly]**

> "Things like: replace `flask.g` access patterns with the new
> request-scoped state helper. Add type annotations to all public
> functions in a 50-file module. Bump pandas to 2.x and fix the
> resulting type errors across the codebase."

> "These need code understanding, test running, iteration. Not text
> substitution. Devin handles them end-to-end and produces a PR a senior
> reviewer can merge. The webhook-to-session scaffolding I just showed
> doesn't change — only the issue spec does. That's the leverage."

---

## 4:40 — WHEN: Next steps (20s)

**[Show: README "Next steps" section]**

> "In a real engagement, four extensions. One: replace SQLite with
> Postgres and ship the metrics to the same BI surface engineering
> already uses. Two: skip the human triage step — pipe Dependabot and
> pip-audit findings directly into labeled issues. Three: per-issue ACU
> budgets driven by complexity labels. Four: switch from personal API
> keys to v3 organization endpoints for seat-level controls."

**[Brief pause]**

> "The repo and run instructions are in the description. Happy to walk
> through any piece of this in more detail. Thanks for watching."

**[End. Total: 5:00]**

---

## Pre-recording checklist

- [ ] Issue #1's PR has actually landed (or you're showing a different completed issue). Don't promise a PR you don't have.
- [ ] Dashboard shows at least one `finished` row with PR URL.
- [ ] Live Devin session URL still resolves (if it's been archived, point to a different session).
- [ ] Webhook secret is **not** visible anywhere on screen — check `.env` is closed.
- [ ] API key is **not** visible — check terminal scrollback.
- [ ] Browser zoom at 110-125% so the audience can read code without squinting.
- [ ] Editor font size: at least 16pt.
- [ ] One clean dry-run before the take. The 5-minute limit is real.

## Cuts if you're over time

In priority order (cut from the bottom):
1. The "Why Devin" examples list — collapse to one example.
2. The architecture file walkthrough — skip `poller.py`, keep `main.py` and `devin.py`.
3. The expired-row aside — only mention if it's still visible and you have time.

## Cuts if you're under time

In priority order:
1. Open the actual PR diff and walk through it for 20s.
2. Show the GitHub webhook delivery log in Settings → Webhooks → Recent Deliveries.
