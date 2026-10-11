# Operations Guide

The practical runbook: how to start it, stop it, understand what's running,
and keep it working. `docs/ARCHITECTURE.md` explains *why* things are built
the way they are; this file is about *running* it day to day.

## Starting the app

Two processes, two terminals. Nothing else needs to be running — no
database server, no queue, no external service, unless you've deliberately
turned on an optional AI provider.

```bash
# terminal 1 — backend (FastAPI, port 8000)
cd backend
python -m uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend (Vite dev server, port 5173)
cd frontend
npm run dev
```

Open `http://localhost:5173`. First time, register a business at `/register`;
after that, `/login`.

**Want demo data instead of starting from empty?**
```bash
cd backend
python -m app.seed
```
Run this *before* starting uvicorn, or any time after — it's idempotent
(safe to run repeatedly; does nothing if the demo business already exists).
Login afterward: `owner@thecopperspoon.io` / `demo12345`.

**No `.env` needed.** The app runs fully in Demo Mode with zero configuration.
If you do want to override something (a real AI provider key, a different
port, etc.), copy `.env.example` to `.env` **at the repo root** — see
`README.md`'s Environment variables section for the full list.

## Stopping the app

`Ctrl+C` in each terminal. There's no background process, no daemon, nothing
left running afterward — `backend/app.db` (the SQLite file) persists on disk
until you delete it.

If a terminal got closed without `Ctrl+C` and a process is still holding the
port or the DB file:
```bash
# Windows
taskkill /F /IM python.exe
taskkill /F /IM node.exe
```

## How it works, briefly

```
Browser (React SPA, :5173) → FastAPI (:8000) → SQLite (backend/app.db)
                                    │
                                    └─ only if a non-demo AI provider is
                                       selected → Ollama / Hugging Face /
                                       Gemini / OpenAI
```

- **Everything is one Python process and one SQLite file.** No separate
  worker, no cache, no queue.
- **Demo Mode is the default and the floor.** Every AI capability
  (classify/extract/score/generate/summarize) has a real, working,
  zero-dependency implementation that never fails — it's what the whole app
  is tested against. Other providers are optional and layer on top via a
  fallback chain; if one fails or isn't configured, it falls back to Demo
  Mode automatically and says why (visible in the AI Provider settings page
  and in `ai_logs`).
- **A lead's lifecycle**: submitted (via the dashboard form, the public
  `/enquiry/<slug>` page, or CSV import) → classified/extracted/scored
  automatically → any matching active workflow fires → the result (status,
  priority, notifications, tasks) lands in the same database transaction.
- **Auth**: JWT access token (30 min) + a revocable refresh token (7 days).
  The frontend refreshes silently in the background; you don't need to
  re-login every 30 minutes. Logging out revokes the refresh token
  server-side — see `docs/ARCHITECTURE.md`'s Auth section for the full model.
- **Multi-tenant from the ground up**: every business's data is isolated by
  `business_id`, resolved from the JWT, never from anything in the URL or
  request body.

Full detail, including the exact request lifecycle and every design
decision's rationale: `docs/ARCHITECTURE.md`.

## Day-to-day maintenance

### Resetting the database
```bash
rm backend/app.db   # or just delete the file however you like
```
It's recreated automatically (empty) the next time the backend starts — this
zero-setup path is unchanged and doesn't involve Alembic at all.

### Database migrations (Alembic)

Only needed for a real schema change against data you want to keep, or the
SQLite→Postgres move — day-to-day local/demo use never touches this (see
"Resetting the database" above). Run from `backend/`:

```bash
alembic upgrade head              # apply every migration up to the latest
alembic revision --autogenerate -m "add loyalty_tier to customers"   # after changing a model
alembic downgrade -1              # undo the most recent migration
alembic current                   # what revision is this DB actually at
alembic check                     # "no new upgrade operations" = models and migrations agree
```

`backend/alembic/env.py` reads the DB URL from the app's own `DATABASE_URL`
setting (not a separate hardcoded one) and points `target_metadata` at
`Base.metadata`, so autogenerate reflects real model changes, not a stale copy.

**The one gotcha**: a database created the normal zero-setup way
(`create_all()` on server startup, still the default) has no `alembic_version`
row, so `alembic upgrade head` against it fails with `table already exists`.
Fix it once with:
```bash
alembic stamp head
```
This tells Alembic "this DB is already at the initial migration" without
re-running the `CREATE TABLE` statements. After that, `alembic upgrade head`
and `alembic revision --autogenerate` work normally. A brand-new, empty
database doesn't need this — `alembic upgrade head` on its own creates
everything.

### Backing up and restoring the database
```bash
cd backend
python -m app.backup backup                 # writes backend/backups/app_backup_<timestamp>.db
python -m app.backup restore <path-to-file>  # overwrites the live DB (auto-saves a safety copy first)
```
Uses SQLite's own backup API (`sqlite3.Connection.backup`), not a raw file
copy, so it's safe to run while the server is using the database. SQLite-only
— a Postgres deployment should use `pg_dump`/`pg_restore` instead. `restore`
always copies the current live DB to `app.before_restore.db` first, so a
restore-into-the-wrong-file mistake is itself recoverable.

### Exporting leads and customers as CSV
From the Leads page: **Export leads CSV** (respects the current status
filter) and **Export customers CSV**. Same data via the API:
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/leads/export -o leads.csv
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/leads/export/customers -o customers.csv
```

### Checking the app is healthy
```bash
curl http://localhost:8000/api/health
```
Returns `db_connected` and `uptime_seconds` — useful for a quick sanity check
without opening a browser.

### Viewing logs
The backend logs to stdout in the terminal you launched it from — every
request (method, path, status, duration, a request id) and every unhandled
error (with full traceback) goes there. There's no separate log file; redirect
to one yourself if you want persistence: `python -m uvicorn app.main:app --port 8000 >> server.log 2>&1`.

### Running the tests
```bash
python -m pytest tests/                                  # full suite (~240 tests, ~1 min)
python -m pytest tests/test_workflows.py -v               # one file, verbose
python -m pytest tests/ --cov=backend/app --cov-report=term-missing   # with coverage
```
Run these before committing any backend change — see `docs/PROJECT_REPORT.md`
Testing section for what's covered and the one deliberate, documented gap
(`app/seed.py` and the real-DB bootstrap path, verified manually instead).

### Updating dependencies
```bash
cd backend && pip install -r requirements.txt --upgrade   # review changes before committing
cd frontend && npm update                                  # same
```
Re-run the full test suite and a manual smoke test after any dependency
bump — this project has already hit one real breakage this way (`passlib`
vs. modern `bcrypt`, see `docs/ARCHITECTURE.md`'s Auth section) that's worth
remembering as a cautionary example.

### Common extension points
| I want to... | Start here |
|---|---|
| Add a new AI provider | `app/ai/base.py` (interface) → implement a new class like `app/ai/local_provider.py` → register it in `app/ai/factory.py` |
| Add a new workflow action type | `app/workflows/nodes.py`'s `_action_handler` — add one more `if action_type == "...":` branch |
| Add a new API endpoint | Pick the right router in `app/api/`, add the route, add/extend a Pydantic schema in `app/schemas/`, put any real logic in `app/services/` if it's reusable |
| Add a new lead field | `app/models/lead.py` (column) → `app/schemas/lead.py` (expose it) → either delete `backend/app.db` (local/demo, loses data) or `alembic revision --autogenerate` + `alembic upgrade head` (keeps data — see Database migrations above) |
| Change how leads are scored | `app/ai/mock_provider.py`'s `score_lead` — the factor weights are plain Python, not configuration |

### Rotating `SECRET_KEY`
Changing it (in `.env`) invalidates every currently-issued access and refresh
token immediately — every logged-in user gets logged out. Fine for a college
project; worth knowing before doing it against anything you care about.

### Deploying publicly
Not done by default (a deliberate choice — see Phase 15 in `CLAUDE.md`). If
you want to, `render.yaml` and `docs/DEPLOYMENT.md` are ready to go; nothing
else needs to change first.

## Troubleshooting

- **"No such table" errors** → delete `backend/app.db`, restart.
- **CORS errors in the browser console** → confirm the frontend's actual port
  is in `FRONTEND_ORIGIN` (comma-separated if you need more than one).
- **Frontend looks stale / a `504` right after I restart the dev server** →
  close the browser tab and open a fresh one (or clear
  `frontend/node_modules/.vite`). A known Vite dev-server quirk after a
  restart, not an app bug — hit repeatedly during development, see the
  Phase 11/12 build log.
- **AI Provider Settings shows a provider "Unavailable"** → expected for
  `local` without Ollama running, or `openai`/`gemini`/`free_api` without a
  key set. The app still works — that's the fallback chain doing its job.
- **Getting logged out unexpectedly** → access tokens expire after 30
  minutes; the frontend should silently refresh using the refresh token. If
  you're calling the API directly (curl/Postman) rather than through the
  frontend, you need to call `/api/auth/refresh` yourself once the access
  token expires.
- **A public enquiry submission returns 429** → the rate limiter (5 per 10
  min per IP) kicked in — expected spam protection, not a bug. It's in-memory
  and resets when the backend restarts.
