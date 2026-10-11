# AI-Powered Small Business Automation Platform

**An enquiry comes in; AI reads it, scores it, and a workflow engine reacts —
all with zero API keys and zero mandatory cost.**

![tests](https://img.shields.io/badge/tests-240%20passing-brightgreen)
![coverage](https://img.shields.io/badge/coverage-94%25-brightgreen)
![cost](https://img.shields.io/badge/mandatory%20cost-%E2%82%B90-blue)
![python](https://img.shields.io/badge/python-3.13-blue)
![react](https://img.shields.io/badge/react-19-61dafb)

A small CRM for a small business: leads come in, AI classifies and scores them, a
workflow engine reacts to the results, and an owner watches it all from a
dashboard. Built as a solo college major project — **runs entirely offline in
Demo Mode with zero API keys**, and can optionally be pointed at a local Ollama
model or a free-tier cloud API without any code changes.

Sample data throughout this README and the demo guide uses a fictional restaurant,
**The Copper Spoon** — reservations, catering quotes, private events, delivery
issues, and complaints. The platform itself isn't restaurant-only (any small
business can register), but the default configuration and sample data commit
to one vertical rather than staying generic — see `docs/PROJECT_REPORT.md`
Scope section for why.

## Screenshots

_Not yet added — see `docs/90_SECOND_DEMO.md`'s recording tips for capturing a
GIF of the full flow (dashboard → new enquiry → AI classification → workflow
fire → dashboard update). Suggested stills: Dashboard, Lead detail (AI
classification + score breakdown), the visual Workflow builder, and the
Channels page._

## Why this is technically interesting

Three design decisions this project treats as its actual engineering content
— not the CRUD around them. Full writeup: [`docs/CASE_FOR_RESUME.md`](docs/CASE_FOR_RESUME.md).

- **A provider abstraction with a real fallback chain.** AI calls never touch
  the caller directly — every classify/extract/score/generate/summarize call
  goes through `AIService`, which resolves `[primary, fallback, "demo"]` and
  tries each in order, catching every exception (not just the typed one), so
  a broken provider can never crash a request. The system is built to *always*
  have a working AI layer, not to assume one.
- **Demo Mode as a first-class citizen, not a stub.** The zero-dependency
  rule-based provider is what the whole app is developed and tested against —
  every other provider is optional and additive. Most projects treat "no API
  key" as an error path; this one treats it as the default path.
- **A workflow engine that stayed additive.** `TRIGGER → AI PROCESSOR →
  CONDITION → ACTION` is a linear interpreter over typed nodes. Compound
  AND/OR conditions (Phase 9) and a second intake channel (Phase 18) were both
  added without touching the engine itself — the concrete test of whether an
  architecture decision actually holds up under real feature pressure.

## Limitations (stated up front, not discovered later)

- The lead score is a legible heuristic, not a trained or statistically
  validated model.
- Only Demo Mode has real AI generation logic; Local/Hugging Face/Gemini/OpenAI
  have real connection checks but their generation methods intentionally raise
  a "not wired up yet" error, caught by the fallback chain — a documented
  Phase 5 scoping decision.
- The workflow engine doesn't branch — two independent rules on one trigger
  need two workflows, not one with a fork.
- Messenger *receiving* is real; replying (`send_email`, `send_messenger_reply`)
  is always simulated, never sent.
- No automated frontend test suite yet (manual verification each phase).
- No scheduled trigger execution — `scheduled` is a valid trigger type with no
  background scheduler wired to fire it.

Full, honest limitations list: `docs/PROJECT_REPORT.md`'s Limitations section.

## Features

- **Auth** — JWT-based register/login; registering a business owner also creates
  their business profile in the same call.
- **Lead intake, for real customers** — three channels into the same pipeline:
  a public, unauthenticated enquiry form at `/enquiry/<business-slug>` a
  business can link from their own website or an ad campaign (captures UTM
  parameters and ad click IDs from the landing URL, so a lead can be traced
  back to the campaign that drove it); an Instagram/Facebook Messenger webhook
  (optional, gracefully degrading — see Channels below); and CSV bulk import
  for leads already tracked in a spreadsheet. Rate-limited to prevent spam.
- **Lead management** — CRUD, status/priority filters, search, and a lead detail
  view showing everything the AI extracted.
- **Data export & lifecycle** — CSV export of leads (respects the current
  filter) and customers from the Leads page; a DB backup/restore script using
  SQLite's own backup API; Alembic migrations wired to the app's own models
  and DB URL for real schema changes and the SQLite→Postgres path.
- **AI provider abstraction** — a swappable `AIProvider` interface with a
  built-in Demo Mode (rule-based, zero dependencies, never fails) plus optional
  Local (Ollama), Hugging Face free-tier, Gemini, and OpenAI providers. A
  fallback chain (configured provider → configured fallback → Demo Mode) means
  the app **never** crashes on a missing key or a down provider — it degrades
  visibly instead, and every attempt is logged to an audit trail.
- **AI classification, extraction & scoring** — every new lead with a message is
  automatically classified (intent/category/confidence), has structured info
  extracted (name/email/phone/budget/urgency/etc — missing fields stay `null`,
  never invented), and gets a 0–100 score across legible factors. The score is
  explicitly a heuristic, not a validated statistical model.
- **AI response generation & summarization** — drafts a reply grounded *only* in
  the business profile you configure (services, hours, contact, tone); never
  invents prices or policies. Conversations can also be summarized.
- **Workflow engine** — `TRIGGER → AI PROCESSOR → CONDITION → ACTION`, executed
  as a linear node chain (no branching, by design — see `docs/ARCHITECTURE.md`).
  Conditions support AND/OR of multiple clauses; actions cover status/priority
  updates, notifications, tasks, AI response/summary generation, and a
  **simulated** email send (no real email is ever sent). Four ready-made rule
  templates are included.
- **Visual workflow builder** — a vertical pipeline view (not a canvas — the
  engine is linear, so the UI doesn't pretend otherwise), with per-node-type
  config forms, reordering, and a run-and-watch execution log.
- **Channels** — a `Channel` interface (`app/channels/`) parallel to the AI
  provider abstraction: the web form is always on; an Instagram/Facebook
  Messenger webhook is optional and requires zero real Meta setup to try —
  a built-in simulate endpoint runs a fake inbound message through the exact
  same pipeline a real one would use. Connecting a real Meta Page is a config
  change, not a rewrite; the rest of the app is identical either way.
- **Dashboard & Analytics** — live stats, recent activity, and seven charts
  (leads over time, by status/priority/intent, score distribution, AI provider
  usage, workflow success/failure) built with a validated, colorblind-safe
  palette.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full picture. In short:

```
frontend/ (React + Vite)  →  backend/ (FastAPI)  →  SQLite
                                  │
                                  ├── app/ai/         AIProvider interface + fallback orchestrator
                                  ├── app/workflows/   linear node executor
                                  ├── app/api/         route handlers
                                  ├── app/services/    business logic shared by routes/workflows
                                  ├── app/models/       SQLAlchemy ORM
                                  └── app/schemas/      Pydantic request/response contracts
```

## Tech stack

| Layer | Choice | Cost |
|---|---|---|
| Backend | Python 3.13 + FastAPI | free/local |
| DB | SQLite via SQLAlchemy 2.0 (Postgres-portable types) | free/local |
| Frontend | React 19 (Vite), react-router-dom, axios, recharts | free/local |
| Auth | JWT (python-jose) + bcrypt | free/local |
| AI — Demo Mode | Rule-based, built in | free/local, always available |
| AI — Local | Ollama (you install separately) | free/local, optional |
| AI — Free-tier | Hugging Face Inference API | free-tier, optional |
| AI — Gemini | Google Gemini API | free-tier, optional |
| AI — OpenAI | OpenAI API | **paid**, optional, never required |

## Install

Prerequisites: Python 3.11+ and Node 18+.

```bash
# backend
cd backend
pip install -r requirements.txt

# frontend (separate terminal)
cd frontend
npm install
```

## Environment variables

Copy `.env.example` (repo root) to `.env` **at the repo root** — `backend/app/config.py`
resolves it relative to its own file location, so it finds the repo root
regardless of which directory you launch the server from.

```bash
cp .env.example .env
```

The app runs fully in Demo Mode with **no `.env` file and no keys set at all**.
Every variable below is optional:

| Variable | Purpose | Default |
|---|---|---|
| `ENVIRONMENT`, `DEBUG` | app metadata | `development`, `true` |
| `SECRET_KEY` | JWT signing key — change this for any real deployment | dev placeholder |
| `DATABASE_URL` | SQLAlchemy URL | `sqlite:///./app.db` |
| `AI_PROVIDER` | `demo` \| `local` \| `free_api` \| `openai` \| `gemini` | `demo` |
| `AI_FALLBACK_PROVIDER` | same options | `demo` |
| `OPENAI_API_KEY` | optional, **paid** | blank |
| `GEMINI_API_KEY` | optional, free-tier | blank |
| `HUGGINGFACE_API_KEY` | optional, free-tier | blank |
| `OLLAMA_BASE_URL` | where your local Ollama server listens | `http://localhost:11434` |
| `FRONTEND_ORIGIN` | comma-separated CORS allow-origins | `http://localhost:5173` |
| `AUTO_SEED_DEMO_DATA` | seed demo data on boot if the DB is empty — for deployments with ephemeral disk, see `docs/DEPLOYMENT.md` | `false` |
| `FACEBOOK_VERIFY_TOKEN` | optional — arbitrary string you choose, entered in Meta's webhook setup | blank |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | optional — from the Meta Business/Developer console | blank |
| `FACEBOOK_APP_SECRET` | optional — verifies real webhook deliveries; skipped (not required) if blank | blank |

Provider *choice* can also be changed per-business at runtime from the AI
Provider Settings page — no restart, no code change, no editing `.env`. See
`docs/ARCHITECTURE.md` for why that's a separate mechanism from the keys above.

## Demo Mode (the guaranteed path)

With no `.env` and no keys, `AI_PROVIDER` defaults to `demo`. The Demo/Mock
provider is a small rule-based engine (keyword matching, regex extraction, an
additive scoring formula, template responses grounded in your business
profile) — zero network calls, zero dependencies, and it structurally cannot
fail, since it's the last link in every fallback chain. This is what the whole
app is built and tested against by default.

## Optional: local AI setup (Ollama)

1. Install [Ollama](https://ollama.com) and pull a small model (e.g. `ollama pull llama3.2`).
2. Confirm it's running: `curl http://localhost:11434/api/tags`.
3. Set `AI_PROVIDER=local` in `.env`, or switch it live from the AI Provider Settings page.

**Current limitation:** the `local` provider's connection check is real (it
pings Ollama), but its actual classify/extract/generate calls are not yet
wired to real prompts — see `docs/ARCHITECTURE.md` for the honest breakdown of
what's implemented per provider. Selecting it with no fallback configured
still works safely: it falls back to Demo Mode and says why.

## Optional: free-tier API setup

- **Hugging Face**: get a free API token at huggingface.co, set `HUGGINGFACE_API_KEY`, `AI_PROVIDER=free_api`.
- **Gemini**: get a free-tier key from Google AI Studio, set `GEMINI_API_KEY`, `AI_PROVIDER=gemini`.

Both currently report their connection status honestly (key present or not) but
share the same "not wired up to real generation yet" limitation as `local` — see
`docs/ARCHITECTURE.md`.

## Database setup

Zero-setup default: tables are created automatically via
`Base.metadata.create_all()` on server startup (`app/database/session.py`).
Delete `backend/app.db` at any time to reset to a clean database; it's
recreated on the next boot. Nothing below is required for local/demo use.

**Alembic** (`backend/alembic/`) is available for real schema changes and for
the SQLite→Postgres path the schema was designed for — see
`docs/OPERATIONS.md`'s Database migrations section for commands and the one
gotcha (an existing `create_all()`-created DB needs `alembic stamp head`
once before `alembic upgrade head` will work against it).

## Sample data

```bash
cd backend
python -m app.seed
```

Seeds the fictional **The Copper Spoon** restaurant with ~23 synthetic leads
(20 via the web form, 3 via the Messenger channel) spread over the last 30
days, three active workflows, and populated conversations — all created
through the real service layer (real classification/scoring/workflow
side-effects, not hand-faked rows), so every page has something realistic to
show immediately. Idempotent — running it again is a no-op if the demo
business already exists. Login after seeding:
`owner@thecopperspoon.io` / `demo12345`. No real personal data.

## Run it

```bash
# terminal 1
cd backend
python -m uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
npm run dev
```

- Backend: `http://localhost:8000` — health check at `/api/health`, interactive
  API docs (Swagger UI) at `/docs`.
- Frontend: `http://localhost:5173`

Register a business at `/register`, or see `docs/DEMO_GUIDE.md` for a full walkthrough.

## Testing

```bash
python -m pytest tests/
```

240 tests, 94% line coverage on `backend/app`. Run with a coverage report:

```bash
python -m pytest tests/ --cov=backend/app --cov-report=term-missing
```

Frontend has no automated test suite — it's been verified manually in-browser
at the end of every phase that touched it (see commit history / phase
summaries). Adding Vitest/RTL coverage is listed under Future work.

## Troubleshooting

- **"No such table" errors** — delete `backend/app.db` and restart the server.
- **CORS errors in the browser console** — confirm the frontend is running on
  the port in `FRONTEND_ORIGIN` (default `5173`); Vite will pick a different
  port if 5173 is busy, and the backend won't allow it until you update the env var.
- **A code change to `.env` isn't taking effect** — `.env` must be at the
  **repo root**, not inside `backend/`. Settings are also cached per-process
  (`lru_cache`), so restart the server after editing it.
- **Stale-looking frontend after a dev-server restart** — Vite occasionally
  serves a `504` on an old dependency-optimizer chunk after a restart if a
  browser tab was already open. Close the tab and open a fresh one (or clear
  `frontend/node_modules/.vite`).
- **AI Provider Settings shows a provider as "unavailable"** — expected for
  `local` without Ollama running, or for `openai`/`gemini`/`free_api` without a
  key set. This is not a bug; it's the fallback chain doing its job.

## Future work

- Wire real prompt-based generation into the Local/Hugging Face/Gemini/OpenAI
  providers (currently: honest connection checks, but generation methods raise
  a clear "not implemented yet" error that the fallback chain catches).
- Branching workflows (the engine is deliberately linear — see `docs/ARCHITECTURE.md`).
- A real background scheduler for the `scheduled` trigger type (accepted as a
  valid value today, but nothing fires it yet).
- Frontend automated tests (Vitest + React Testing Library).
- Multi-user businesses (the data model supports it — `User.business_id` — but
  there's no "invite a teammate" flow yet; every registration creates a new business).

## More docs

- [`docs/CASE_FOR_RESUME.md`](docs/CASE_FOR_RESUME.md) — the three design decisions worth talking about in an interview
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design, data flow, key decisions
- [`docs/API_DOCUMENTATION.md`](docs/API_DOCUMENTATION.md) — full endpoint reference
- [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md) — step-by-step walkthrough (~10 min)
- [`docs/90_SECOND_DEMO.md`](docs/90_SECOND_DEMO.md) — the tight, timed, rehearsable version for an interview or recruiter call
- [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md) — college-report-style writeup
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — deploying to Render (backend) + Vercel (frontend), both free
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — the day-to-day runbook: start/stop, logs, tests, resetting the DB, common maintenance tasks, troubleshooting
