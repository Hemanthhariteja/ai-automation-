# CLAUDE.md — AI-Powered Small Business Automation Platform

This file is read automatically by Claude Code at the start of every session in this repo. It is the persistent source of truth for constraints, architecture, and workflow. Keep it in sync as decisions are made — update it rather than re-explaining things in chat.

## Who this is for

Solo college student, major project, limited laptop (no dedicated GPU, limited RAM), **₹0 mandatory budget**. Built incrementally, phase by phase, with working software after every phase — never a single giant generation pass.

## Non-negotiable constraints

- **No paid API may ever be required.** Everything must run in Demo Mode with zero API keys configured.
- **CPU-only, low-RAM.** No large local models (no unprompted 7B+ downloads), no Docker/Kubernetes unless truly justified, no GPU-dependent packages.
- **Never crash on missing/invalid AI config.** Missing key → fallback chain → Demo Mode → friendly message. Never an unhandled exception.
- **Secrets never touch git or the frontend.** Use `.env` + `.env.example`; `.env` stays gitignored; never print, log, or ask me to paste a real key into a file.
- **No uncontrolled API loops.** Timeouts, retry caps, rate limits, max input/output length on every AI call path.
- Don't claim a feature "works" until it has been run and tested. Don't leave silent placeholder functions.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI |
| DB | SQLite via SQLAlchemy (schema kept Postgres-portable) |
| Frontend | React (or plain HTML/CSS/JS if simpler for a given screen) |
| Auth | JWT or secure server sessions |
| AI | Provider abstraction — Local (Ollama, small model) → Free-tier API → Demo/Mock. Paid APIs (OpenAI/Gemini/Claude) optional only. |
| Charts | Any lightweight JS chart lib |
| Workflow engine | Custom, Python-based (trigger → AI processor → condition → action) |

## Repo layout

```
backend/
  app/
    main.py
    config.py
    api/
    models/
    schemas/
    services/
    ai/            # provider abstraction lives here
    channels/       # Channel abstraction — Messenger/Mock intake (Phase 18)
    workflows/      # trigger/condition/action engine
    database/
    auth/
    utils/
    backup.py       # DB backup/restore CLI (Phase 20)
    seed.py
  alembic/          # schema migrations, wired to app's own models/DB URL (Phase 20)
frontend/
  src/
    components/
    pages/
    services/
    hooks/
    context/
tests/
docs/
.env.example
README.md
render.yaml       # deployment-ready, not currently activated (see Phase 15)
```

## AI provider abstraction

```
Application → AIProvider interface → { LocalProvider | FreeAPIProvider | OpenAIProvider | GeminiProvider | MockProvider }
```

- Swappable at runtime via config/settings page — no code changes elsewhere in the app to switch providers.
- Fallback chain on any failure (missing key, network down, rate limit, local model unavailable): configured provider → configured fallback → Demo Mode. Always surface *why* it fell back, never fail silently or crash.
- `.env.example` with placeholders only: `OPENAI_API_KEY=`, `GEMINI_API_KEY=`, `HUGGINGFACE_API_KEY=`. Never hardcode keys. Never commit `.env`.
- Settings/admin UI shows provider, model, connection status (✓/✗), and active fallback — never the raw key.
- Only claim an API is "free" if verifiably free-tier at time of writing; label everything FREE / FREE-TIER / PAID explicitly.
- **Status**: only the Demo/Mock provider has real classify/extract/score/generate/summarize logic. Local (Ollama), Hugging Face, Gemini, and OpenAI have real, working connection checks and correctly participate in the fallback chain, but their generation methods intentionally raise a clear "not wired up yet" error — a documented Phase 5 scoping decision, not an oversight. See `docs/ARCHITECTURE.md`.

## AI capabilities to implement

1. **Intent classification** → structured JSON (`intent`, `category`, `confidence`).
2. **Information extraction** — name, email, phone, product/service, budget, location, requirement, urgency, preferred date. Missing = `null`, never invented.
3. **Lead scoring**, 0–100 (0–30 low / 31–70 medium / 71–100 high), based on legible factors (intent, budget info, urgency, specificity, completeness). Explicitly not a validated statistical model — don't claim otherwise anywhere, including docs. **Since Phase 19**: two restaurant-vertical-specific signals added — party size (parsed from the message text, e.g. "table for 12") and category value (`private_events`/`catering` outweigh `reservations`/`delivery_takeout`) — configuration (`CATEGORY_VALUE_SCORES` in `mock_provider.py`), not a rewrite; see `docs/PROJECT_REPORT.md`'s Algorithms section.
4. **Response generation** — concise, polite, grounded only in business profile the owner configured (name, description, services, hours, contact, tone). Never invents prices, policies, or promises.
5. **Conversation summarization.**
6. **AI assistant** (optional) — answers questions like "show my high-priority leads" by querying the app's own DB. Never fabricates data that isn't there. **Not built** — optional per original scope, not picked up in Phases 1–15.

## Workflow engine

`TRIGGER → AI PROCESSOR → CONDITION → ACTION`

- Triggers: new enquiry, new customer, manual, scheduled. External triggers (WhatsApp etc.) are mocked, never mandatory. **`scheduled` accepted as a valid value but nothing fires it yet — no background scheduler exists.**
- Actions: generate AI response, save lead, update lead status, send email, create notification, generate summary, add task, log execution. External actions (real email/SMS) need a **simulation mode** that shows "Email would be sent to X" in the UI when no provider is configured. **Implemented and tested — `send_email` is fully simulated, never sends real email. Since Phase 18: `send_messenger_reply` added, same simulation pattern.**
- Conditions: simple rule engine (`if lead_score > 80 → notify_owner`, `if intent == "complaint" → priority = high`, etc.), designed so new rules are additive, not a rewrite. **Implemented, including compound AND/OR clauses (Phase 9) added without modifying the engine — the concrete proof of "additive."**
- Include a simple visual workflow builder (trigger/AI-analysis/condition/action/notification/DB/end nodes) — reliability and a clean demo over Zapier-level polish. **Implemented as a linear vertical pipeline, deliberately not a branching canvas — the engine itself is linear by design, see `docs/ARCHITECTURE.md`.**

## Data model (SQLite)

`users, businesses, customers, leads, conversations, messages, workflows, workflow_nodes, workflow_executions, tasks, notifications, ai_logs, refresh_tokens`

Every business-owned table carries `business_id`, enforced at the query layer from the JWT — this is the multi-tenancy boundary and has been true since Phase 2, tested extensively for cross-tenant isolation across every resource (leads, workflows, notifications, tasks, ai_logs, analytics, dashboard).

**Since Phase 15**: `businesses.slug` (public, URL-safe identifier for the unauthenticated enquiry form) and `leads.tracking_data` (JSON — UTM params, ad click IDs, referrer, landing page, user agent, captured from the public enquiry form).

**Since Phase 18**: `businesses.messenger_page_id` (the Meta Page ID a business connects to receive Messenger leads) and `leads.tracking_data.channel`/`sender_external_id` for channel-sourced leads (`leads.source` is `"messenger"` instead of `"web_form"`/`"csv_import"`).

## Explicitly out of scope

Full WhatsApp clone, Salesforce-level CRM, Zapier-level builder, custom LLM training, large-scale model training, local video generation, Kubernetes, microservices unless clearly justified. If a request drifts toward these, flag it instead of building it.

*(Phase 18+ revisits a WhatsApp/Messenger **channel abstraction** — this is scoped as one additional, optional, gracefully-degrading input source into the existing lead pipeline, not a "clone." If it starts looking like a messaging platform rebuild, that's the line to flag.)*

## Build process (how Claude Code should operate here)

Work one phase at a time from the table below. **After every phase:** run the app, run the tests, fix any errors, give me a short plain-English summary of what now works, and stop — don't start the next phase until I confirm this one is good.

| Phase | Scope | Status |
|---|---|---|
| 1 | Project setup / scaffolding | Done |
| 2 | Database & models | Done |
| 3 | Authentication | Done |
| 4 | Lead management (CRUD) | Done |
| 5 | AI provider abstraction + Demo Mode | Done |
| 6 | AI classification & extraction | Done |
| 7 | AI response generation | Done |
| 8 | Workflow engine core | Done |
| 9 | Conditions & actions | Done |
| 10 | Dashboard | Done |
| 11 | Visual workflow builder | Done |
| 12 | Analytics | Done |
| 13 | Testing pass | Done |
| 14 | Documentation | Done |
| 15 | Demo prep / deployment | Done — seed script, deployment-ready code (`render.yaml`, auto-seed, multi-origin CORS) prepared but **not activated** (no public hosting per instruction); plus, added mid-phase per follow-up: public unauthenticated enquiry form (`/enquiry/<slug>`), CSV lead import, and ad/campaign attribution capture (UTM params, `gclid`/`fbclid`, referrer) on the public form |
| 16 | Production readiness I — error handling, structured logging, auth/rate-limit hardening (Track A.1–A.2 of `UPGRADE.md`) | Done — global exception handler + request-logging middleware + richer `/api/health` (db_connected, uptime); rate limiting on register/login; access+refresh token model (30 min access, 7 day refresh, hashed refresh tokens, real logout revocation, silent auto-refresh on 401 in the frontend); owner-vs-staff role enforcement (`require_owner`) on AI settings, business profile, and staff management, with a full staff account CRUD + frontend UI; security audit confirmed no raw SQL and no `dangerouslySetInnerHTML` anywhere. 191 tests, 95%+ coverage. |
| 17 | Portfolio polish — UI pass, empty/loading states, a scripted 90-second demo path (Track B.1–B.2) | Done — real loading states (spinner component, `PageLoading`) replacing plain "Loading..." text everywhere, including two list pages (Leads, Workflows) that previously had none at all and flashed an empty state before data arrived; a shared `EmptyState` component with icons used consistently across every page instead of ad-hoc plain-text messages; scattered inline `style={{marginTop:20}}`-style spacing consolidated into named utility classes (`.mt-section`, `.section-intro`, `.page-intro`, `.header-actions`, `.panel-header`, `.mb-form`, `.fieldset-reset`) for visual consistency; `docs/90_SECOND_DEMO.md` — a scripted, timed demo path with every claim individually re-verified against the real running app (not just written up) before being included. |
| 18 | Niche pivot + one real channel — commit sample data/copy to one vertical, build a `Channel` abstraction (WebForm / Messenger / Mock) parallel to the AI provider abstraction (Track C.1–C.2) | Done — committed to the restaurant vertical: sample business renamed "The Copper Spoon", `mock_provider.py`'s `CATEGORY_KEYWORDS` replaced with restaurant categories (reservations, catering, private_events, delivery_takeout), seed data rewritten to 23 restaurant-appropriate leads (20 web-form + 3 Messenger); new `Channel` abstraction (`app/channels/base.py`) — deliberately no fallback chain, since channels run simultaneously rather than as alternatives — with `MessengerChannel` (real Meta payload parsing, HMAC-SHA256 webhook signature verification, graceful skip when no app secret configured) and `MockChannel` (zero-setup demo path); `app/services/channel_intake.py` funnels every channel through the same classify/extract/score/workflow pipeline as web-form leads; new `/api/channels/*` routes (status, Meta verification handshake, real webhook receiver, authenticated simulate endpoint) and a new Channels frontend page (connect a Meta Page ID, simulate an inbound message with no real setup). 21 new channel tests + existing suite updated for the vertical change, all passing. |
| 19 | Niche scoring tweaks + resume-facing docs — vertical-specific scoring signals, README-as-pitch, technical writeup, coverage visibility, niche landing page (Track B.3–B.5, C.3–C.4) | Done — two restaurant-vertical scoring signals added to `mock_provider.py::score_lead` (party size parsed from message text, e.g. "table for 12"; category value weighting `private_events`/`catering` above `reservations`/`delivery_takeout`), existing five factors reweighted so the total still clamps to 100 — configuration (`CATEGORY_VALUE_SCORES`) not a rewrite; one stale off-vertical test caught and fixed in the process (`test_score_distribution_buckets` still said "quote for a website"). README given a marketing pass — elevator pitch, static test/coverage/cost badges, a "why this is technically interesting" section, an up-front Limitations section, a screenshots placeholder with honest instructions (no fabricated images). New `docs/CASE_FOR_RESUME.md` — the three design decisions worth an interview conversation (provider fallback chain, Demo-Mode-as-default, the workflow engine staying additive under Phase 9 and Phase 18 pressure) plus the Channel-vs-Provider abstraction contrast. New `docs/landing/index.html` — a self-contained, no-build static outreach page for the restaurant vertical (Track C.4), also published as a shareable preview. All doc claims (API examples, score breakdown keys/values) re-verified against the live server, not just written up; 216 backend tests passing (2 new scoring tests added), seed script re-verified. |
| 20 | Deployment & data lifecycle — actually exercise the Phase 15 deployment prep if/when wanted, Alembic migrations, CSV export, DB backup/restore (Track A.4–A.5) | Done — asked first: live hosting (Render/Vercel) declined again, same as Phase 15, so this stayed local-only. Alembic wired up (`backend/alembic/`, `env.py` reads the app's own `DATABASE_URL` and points `target_metadata` at `Base.metadata` instead of a second config that could drift); one real initial migration autogenerated from the actual models (13 tables) and verified both directions (`upgrade head` / `downgrade base` / re-upgrade / `alembic check` reports no drift). Found and documented the one real gotcha by actually testing it: a DB created the zero-setup `create_all()` way has no `alembic_version` row, so `alembic upgrade head` against it fails until `alembic stamp head` runs once — not a hypothetical, reproduced and fixed live. CSV export (`GET /api/leads/export`, filter-parity with the list endpoint; `GET /api/leads/export/customers`) plus a frontend download button using a Blob + object URL, since the auth header can't ride along on a plain `<a href>` browser navigation. `backend/app/backup.py` — `python -m app.backup backup`/`restore`, using SQLite's own backup API (not a raw file copy) so it's safe against a DB the server is using; proven end-to-end against real seeded data (backup → deleted all 23 leads → restored → all 23 back, verified by row count). 11 new tests (6 export, 5 backup/restore). Docs swept for two now-false claims this phase itself made true: "no migration tool" (README, ARCHITECTURE, OPERATIONS) and a stale "eleven tables" / "214 tests" count in multiple docs — all corrected to 13 tables / 227 tests, 94% coverage unchanged. |

**Note on Track A.3 (multi-tenancy) from `UPGRADE.md`**: already done, not a Phase 20 item. The upgrade doc's premise ("right now the app assumes one business") doesn't match this codebase — every table has been `business_id`-scoped since Phase 2, enforced at the query layer from the JWT, with explicit cross-tenant isolation tests on every resource. Flagged instead of silently reimplemented or silently skipped.

Before writing large amounts of code at project start, Claude Code should: confirm the architecture above, confirm the MVP cut, list dependencies and mark each free/local vs. optional-paid, then begin Phase 1. *(Historical — applied to Phase 1, kept for context.)*

## Explaining things as you go

I'm still learning. Whenever a non-trivial technology or pattern is introduced (e.g. JWT, SQLAlchemy relationships, the provider pattern, workflow engines), briefly cover: what it is, why it's needed here, where it lives in the codebase, how it works, and how to test it. Keep it tight — no unnecessary theory.

## Sample data

Fictional business "The Copper Spoon" (a restaurant — dine-in, takeout & delivery, private event catering, group reservations) with ~23 synthetic leads/customers for demo purposes (20 web-form + 3 Messenger). No real personal data. **Implemented**: `backend/app/seed.py` (`python -m app.seed`), idempotent, spreads leads over 30 days, seeds 3 workflows. Login: `owner@thecopperspoon.io` / `demo12345`.

*(Committed to the restaurant vertical in Phase 18 per the niche pivot — this superseded the earlier "TechFix Solutions, any business" generic-services identity used through Phase 17. See the Phase 18 entry in the phase table below.)*

## Testing

Cover: auth, lead creation, AI classification, lead scoring, workflow execution, conditions, DB operations, provider fallback, API-failure handling, Demo Mode. Basic suite is required, not optional — part of "done" for each phase that touches these areas.

**Status**: 240 backend tests, 94%+ line coverage on `backend/app` (`pytest tests/ --cov=backend/app --cov-report=term-missing`). No frontend automated test suite yet — verified manually in-browser each phase; Vitest/RTL noted as future work.

## Docs to produce (Phase 14)

`README.md` (overview, features, architecture, stack, install, env vars, local AI setup, free API setup, demo mode, DB setup, run frontend/backend, testing, troubleshooting, future work), plus `ARCHITECTURE.md`, `API_DOCUMENTATION.md`, `DEMO_GUIDE.md`, and a college-report-style doc (abstract, problem statement, existing/proposed system, objectives, scope, requirements, architecture, data flow, DB design, AI/workflow architecture, algorithms, implementation, testing, results, limitations, future scope, conclusion). No inflated accuracy or business-impact claims anywhere in these.

**Status**: all done — `README.md`, `docs/ARCHITECTURE.md`, `docs/API_DOCUMENTATION.md`, `docs/DEMO_GUIDE.md`, `docs/PROJECT_REPORT.md`, `docs/DEPLOYMENT.md`.

## Final demo script (what "done" looks like)

Login → dashboard → view leads → submit new enquiry → AI classifies/extracts/scores/responds → workflow fires → lead lands in CRM → notification appears → follow-up task created → dashboard updates → view workflow visually → open AI provider settings → disable the provider → show it fall back to Demo Mode automatically, live, with no internet.

**Status**: implemented and verified end-to-end; full walkthrough in `docs/DEMO_GUIDE.md`.

---

# UPGRADE.md — Phase 16+: Production, Polish & Niche Pivot

Appended per user instruction. Assumes Phases 1–15 above are done and working. Same rule as before: **one phase at a time, run + test + summarize before moving on.**

## Context

The core platform (AI classification, lead scoring, workflow engine, CRM, dashboard, demo mode) is built and working. This round is not "add more features" — it's three specific upgrades: make it trustworthy enough to actually run for a real business, make it look and read like a serious product for a portfolio/resume, and give it one concrete edge (a real channel + a narrow niche) instead of staying a generic multi-purpose platform. Don't reopen finished phases unless a bug is found; build on top.

## Constraints carried over (still apply)

- Still ₹0-mandatory. Any new paid integration (WhatsApp Cloud API, hosting, etc.) must be clearly optional and the app must degrade gracefully without it.
- Still CPU-friendly, still no crash-on-missing-config, still no secrets in git.
- New features get the same fallback discipline as the original AI layer: if a new integration isn't configured, simulate it and say so in the UI — never break the app.

## Track A — Production readiness

Goal: could a real, non-technical business owner actually run this on their own data without you standing next to them.

1. **Real reliability, not demo reliability.** Structured error handling and logging across all API routes (not just AI calls) — every failure path returns a clean message, never a stack trace. Health-check endpoint + a simple uptime/status view in settings. Basic request validation and rate limiting on all public-facing endpoints, not just AI ones.
2. **Security hardening pass.** Auth review: password hashing strength, JWT expiry + refresh, session invalidation on logout. HTTPS-ready config notes, CORS locked to real origins, input sanitization against XSS/SQL injection (check raw queries if any). Role separation: owner vs staff, staff with reduced permissions (can't change AI provider, billing, etc.).
3. **Multi-tenancy.** *(Already done — see note in the phase table above.)*
4. **Real deployment path.** Document and test a free/cheap deployment. Confirm the app survives a cold start, a restart, a DB migration. Add Alembic now, before it's painful — also the SQLite→Postgres path the schema was designed for.
5. **Data export & backup.** Owner can export leads/customers as CSV. Simple DB backup/restore script.

## Track B — Portfolio / resume polish

Goal: this is the thing you link in a resume, show in an interview, or demo to a professor or recruiter in 5 minutes and it reads as clearly competent.

1. **UI polish pass.** Consistent spacing, typography, empty states, loading states, coherent visual identity.
2. **A killer 90-second demo path.** Guided walkthrough: seed data loads, submit one enquiry live, show AI reasoning happen, show workflow fire, show dashboard update — under 2 minutes, no dead air.
3. **README as a marketing document.** GIF/screenshot walkthrough at the top, one-line elevator pitch, "why this is technically interesting" section (provider abstraction, fallback chain, workflow engine design), honest limitations section.
4. **Case for the resume line.** Short `docs/` writeup: the provider-abstraction pattern, fallback-to-demo-mode design, workflow engine's trigger/condition/action model.
5. **Test coverage visibility.** Coverage report / badge.

## Track C — Niche pivot + real channel

Goal: stop being a generic "small business platform" and become a specific, credible tool for one type of business, reachable where that business's customers already are.

1. **Pick one vertical, commit to it in UI copy and sample data.** Recommend: restaurants, salons/clinics, or home-services. Don't build separate versions — just make the default configuration, sample data, and onboarding copy speak to one type of business.
2. **One real channel integration, optional and gracefully degrading.** WhatsApp Cloud API sandbox or Instagram/Messenger webhook. Build as a `Channel` interface → `WebFormChannel` (existing) | `WhatsAppChannel` | `MockChannel`, parallel to the AI provider abstraction. Not configured → app behaves exactly as today. Additive, not a rewrite.
3. **Niche-specific lead scoring tweaks.** 2–3 vertical-specific signals once a vertical is picked (e.g. salons: preferred date/time; home services: location/service-area match). Configuration, not a fork.
4. **A one-page landing/pitch for that niche.** Not part of the app — a simple static page for outreach, with the Track B demo video/GIF.

## Suggested order

Track A.1–2 and Track B.1–2 first (prerequisites for everything else looking credible). Then Track C.1–2 (the real differentiator). Multi-tenancy and deployment (Track A.3–4) last — matters most only when actually onboarding a second real client. *(Track A.3 already done — see note above.)*
