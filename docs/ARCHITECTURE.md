# Architecture

## System overview

```
┌─────────────┐      HTTPS/JSON       ┌──────────────────┐        ┌────────────┐
│   React SPA │ ───────────────────►  │   FastAPI app     │ ─────► │   SQLite   │
│  (Vite dev  │  ◄───────────────────  │  (backend/app/)   │ ◄───── │  (1 file)  │
│   server)   │     JWT bearer token   └──────────────────┘        └────────────┘
└─────────────┘                                │
                                                │  (only when a non-demo
                                                ▼   provider is selected)
                                       ┌──────────────────┐
                                       │ Local Ollama /    │
                                       │ Hugging Face /    │
                                       │ Gemini / OpenAI   │
                                       └──────────────────┘
```

Everything is a single Python process and a single SQLite file. No message
queue, no Redis, no Docker, no separate worker process — deliberately, per the
"CPU-only, low-RAM, no unprompted infra" constraint this project is built
under. The one exception is the frontend, which is a separate Vite dev server
in development (and a static build in production) talking to the backend over
plain HTTP.

## Backend layers

```
backend/app/
├── main.py           FastAPI app, CORS, router wiring, lifespan (creates tables on boot)
├── config.py          pydantic-settings; every setting has a safe default
├── api/                route handlers — thin, no business logic
├── schemas/            Pydantic request/response contracts
├── models/             SQLAlchemy ORM (13 tables)
├── services/            business logic shared between routes and the workflow engine
├── ai/                  the provider abstraction (interface, providers, fallback orchestrator)
├── workflows/            the linear node executor + node handlers + templates
├── auth/                 JWT + bcrypt + the FastAPI dependency that guards routes
├── database/             engine/session setup
└── utils/                small shared helpers (currently just UTC time)
```

**Why `services/` exists separately from `api/`:** route handlers in `api/`
only do HTTP concerns (parse the request, check ownership, call a service,
shape the response). The actual logic — classify-and-score a lead, generate a
grounded response, get-or-create a customer — lives in `services/` so the
*same* logic can be called from an HTTP route **and** from a workflow action
node without duplicating it. `app/workflows/nodes.py`'s `generate_ai_response`
action, for example, calls the exact same `services/response_service.py`
function that `POST /api/leads/{id}/generate-response` calls.

## Multi-tenancy: business-scoping

Every table that holds business data has a `business_id` foreign key, and
every query in `api/` filters by it — resolved from the JWT via
`get_current_business_id`, **never** from the URL or request body. This is
what stops Business A from reading or modifying Business B's data even if they
guess an ID. It's tested explicitly (search test files for `_isolated` or
`_other_business` — nearly every resource has a cross-tenant test).

There's currently one business per registered user (`POST /api/auth/register`
creates both in one transaction); the data model supports multiple staff
users per business (`User.business_id`), but there's no "invite a teammate"
flow yet.

## The AI provider abstraction

```
Caller (a route or a workflow action)
        │
        ▼
   AIService  (app/ai/service.py)
        │  resolves the fallback chain: [primary, fallback, "demo"]
        │  tries each provider in order, catching *any* exception
        ▼
  AIProvider interface (app/ai/base.py)
        │
   ┌────┴─────┬──────────┬───────────┬─────────┐
   ▼           ▼          ▼           ▼         ▼
 Mock       Local      FreeAPI     OpenAI     Gemini
 (Demo)    (Ollama)   (HF free)    (paid)   (free-tier)
```

**The fallback chain never bubbles an exception to the caller.** `AIService._run`
wraps every provider attempt in `try/except Exception` (not just the typed
`AIProviderError`) — a provider bug can't crash the request. Every attempt,
success or failure, is written to the `ai_logs` table: which provider was
*requested*, which one *actually* served it, whether that was a fallback, and
why. This is what powers the "disable the provider, watch it fall back live"
demo moment and the Analytics provider-usage chart.

**Provider choice vs. provider keys are two different mechanisms, on purpose.**
API keys live only in `.env` (`OPENAI_API_KEY` etc.), loaded once at process
start — they never touch the database or the frontend. Which provider is
*active*, though, is a `Business.ai_provider` / `Business.ai_fallback_provider`
column, changeable at runtime via `PATCH /api/ai/settings` with no restart.
This is deliberate: CLAUDE.md's "secrets never touch git or the frontend"
constraint rules out a settings-page flow where someone pastes a real key into
the app, but "swappable at runtime via a settings page" (also required) still
needs *something* to be runtime-mutable — that something is the choice, not the secret.

**What's actually implemented per provider, honestly:**

| Provider | `check_connection()` | classify/extract/score/generate/summarize |
|---|---|---|
| Demo (Mock) | always `True` | fully implemented — rule-based, real logic |
| Local (Ollama) | real: pings `OLLAMA_BASE_URL/api/tags` | raises `AIProviderError("not wired up yet")` |
| Free-tier (Hugging Face) | real: checks key presence | same |
| Gemini | real: checks key presence | same |
| OpenAI | real: checks key presence | same |

The four non-demo providers were built with real connection-checking and a
correct place in the fallback chain, but their generation methods are
intentionally not connected to real prompts yet — building that out is listed
under Future work. This was a scoping call made explicitly (see Phase 5 of the
build log) rather than something that silently didn't get finished: pretending
they worked would violate the "no silent placeholder functions" rule this
project holds itself to.

## The workflow engine

```
TRIGGER → AI_PROCESSOR → CONDITION → ACTION/NOTIFICATION/DB → END
```

A `Workflow` is an ordered list of `WorkflowNode` rows (`order_index` decides
execution order). `WorkflowEngine.execute()` (`app/workflows/engine.py`) walks
them in order:

- Each node type has a handler in `app/workflows/nodes.py` returning one of
  three outcomes: `ok` (continue), `halt` (a condition wasn't met — stop
  quietly, not an error), or `failed` (stop, mark the whole execution failed).
- A handler that raises a raw Python exception is caught by the engine itself
  and converted to a `failed` step — the same "never crash the caller"
  guarantee as the AI layer, at the workflow level.
- Every step (node, status, human-readable detail) is appended to a JSON log
  on `WorkflowExecution.log`, which is what both the API and the visual
  builder's "run and watch" panel render.

**The engine is deliberately linear — no branching.** A `condition` node either
lets execution continue or halts everything after it; there's no `if/else`
graph. This is a real, acknowledged limitation, not an oversight: it keeps the
node model representable as a simple vertical list in the UI (no canvas
library, no edge-drawing, no layout algorithm) and keeps execution
trivially easy to reason about and test. If two independent rules are needed
on the same trigger, that's expressed as **two separate workflows** — the
engine already runs every matching active workflow independently
(`app/services/workflow_trigger.py`), so this is a real, working alternative
to branching, not a workaround.

**Auto-triggering.** `POST /api/leads` fires every active `new_enquiry`
workflow after the lead is created and classified; it also fires
`new_customer` workflows, but only when the linked customer was genuinely new
this request (a `(customer, was_newly_created)` tuple threads through
`get_or_create_customer` → `run_ai_pipeline_on_lead` → the route, specifically
so a *repeat* lead from an existing customer doesn't re-fire "new customer"
rules). `manual` and `scheduled` are valid `trigger_type` values, but only
`manual` actually has a caller today (`POST /api/workflows/{id}/run`) —
`scheduled` has no background scheduler wired to it (see Future work in the README).

**Conditions** support both a simple shape (`{field, operator, value}`) and a
compound shape (`{logic: "all"|"any", clauses: [...]}`) — the simple shape was
Phase 8's original design; the compound shape was added in Phase 9 by
extending `evaluate_condition()` alone, with zero changes to the engine or any
other node handler. That's the concrete proof behind the "additive, not a
rewrite" requirement in CLAUDE.md.

**Rule templates** (`app/workflows/templates.py`) are plain data — a
name/description/trigger_type plus a list of node definitions. Instantiating
one (`POST /api/workflows/templates/{id}`) just inserts a normal `Workflow` +
`WorkflowNode` rows; the engine has no idea templates exist as a concept. Two
of the four match CLAUDE.md's example rules literally
(`if lead_score > 80 → notify_owner`, `if intent == "complaint" → priority = high`).

## Request lifecycle — a concrete example

Submitting a new enquiry (`POST /api/leads` with a `raw_message`):

1. `get_current_business_id` resolves the caller's business from the JWT.
2. `get_or_create_customer` finds/creates a `Customer` from any explicit
   contact info in the payload.
3. The `Lead` row is inserted and flushed (so it has an `id`).
4. `run_ai_pipeline_on_lead` calls `AIService` three times (classify, extract,
   score), each going through the fallback chain and logging to `ai_logs`. If
   no explicit customer was given but an email/phone was *extracted* from the
   message, a customer gets linked here instead.
5. `trigger_workflows` runs every active `new_enquiry` (and, if applicable,
   `new_customer`) workflow against the now-classified lead, in the same DB
   transaction — so a workflow's status/priority changes, notifications, and
   tasks all commit atomically with the lead itself.
6. One `db.commit()` at the end. If any workflow blew up unexpectedly, it's
   caught and logged (`workflow_trigger.py`) — the lead is still returned `201`.

## Data model

13 tables: `users`, `businesses`, `customers`, `leads`, `conversations`,
`messages`, `workflows`, `workflow_nodes`, `workflow_executions`, `tasks`,
`notifications`, `ai_logs`, `refresh_tokens`. See `docs/PROJECT_REPORT.md` for
the full entity-relationship writeup and field-by-field rationale — this file
stays focused on *why* things are shaped the way they are, not a schema dump.

For local/demo use, tables are still created automatically via
`Base.metadata.create_all()` on startup — that path is unchanged and remains
zero-setup. **Since Phase 20**: Alembic (`backend/alembic/`) is also wired up,
pointed at the app's own `DATABASE_URL` setting rather than a second config
that could drift, with `target_metadata = Base.metadata` so
`alembic revision --autogenerate` reflects real model changes. This is the
path for anything `create_all()` can't do — a real schema change against
data you want to keep, or the SQLite→Postgres move the schema's Postgres-
portable types were chosen to support. One gotcha, discovered by actually
testing the sequence rather than assuming it: an existing DB created the
zero-config way has no `alembic_version` row, so `alembic upgrade head`
against it fails with "table already exists" — the fix is `alembic stamp
head` once, which tells Alembic that DB is already at the initial migration
without re-running it. See `docs/OPERATIONS.md`'s Database migrations section
for the full command reference.

## The public/authenticated boundary

Every route in `api/` except three requires a JWT: `POST /api/auth/register`,
`POST /api/auth/login`, and — the one that matters architecturally —
`app/api/public.py`, which is the actual customer-facing lead intake channel.
A business gets a public, URL-safe `slug` at registration
(`app/utils/slug.py`); `POST /api/public/{slug}/leads` accepts an enquiry with
no auth at all, resolving the business from the slug instead of a JWT, then
runs the exact same `run_ai_pipeline_on_lead` + `trigger_workflows` code path
as the authenticated `POST /api/leads`. Two things matter about how this is
guarded, since it's the only unauthenticated *write* endpoint in the app:

- **Rate limiting** (`app/utils/rate_limit.py`) — a simple in-memory sliding
  window keyed by `(business_id, client_ip)`, deliberately not backed by
  Redis or any external store, matching the single-process constraint this
  project holds itself to elsewhere. It resets on restart; that's an accepted
  tradeoff for basic spam protection on a college project, not a
  billing-grade rate limiter.
- **No internal data leaks back to the public caller.** The response to a
  public submission is `{"received": true}` — never the lead's id, AI score,
  or classification. Only the authenticated business owner can see what the
  AI actually did with an enquiry, via the normal `/api/leads` endpoints.

CSV import (`app/services/lead_import.py`) is the other lead-intake path —
authenticated, for a business owner bulk-loading leads they already have in a
spreadsheet. It reuses the same per-row pipeline as both other entry points,
capped at 500 rows per file and reporting row-level failures instead of
failing the whole import, since real spreadsheet data is rarely uniformly clean.

## The Channel abstraction

`app/channels/` (`base.py`, `messenger.py`, `mock.py`) generalizes "a message
arrived from somewhere that isn't the web form" behind one interface,
`Channel.parse_webhook_payload(payload) -> list[InboundMessage]`. It looks
structurally similar to the AI provider abstraction, but is a deliberately
different shape: **providers form a fallback chain because they're mutually
exclusive alternatives for the same job** (only one is "active" at a time,
with the rest as backup); **channels don't**, because a business can have web
form, Messenger, and (in principle) other channels all receiving real
messages simultaneously. There's no "primary channel" setting — every
configured channel just runs.

Every channel, regardless of source, funnels through one function:
`app/services/channel_intake.py`'s `ingest_channel_message(db, business,
channel_name, message)`. It creates a `Customer` (name only — a chat platform
gives no email/phone to dedupe against, a documented simplification, not a
silent gap), creates a `Lead` with `source=channel_name` and
`tracking_data={"channel": ..., "sender_external_id": ...}` for traceability,
then runs the identical `run_ai_pipeline_on_lead` + `trigger_workflows(...,
"new_enquiry")` path that every other intake route uses. A Messenger-sourced
lead is indistinguishable from a web-form one anywhere downstream — same
classification, same scoring, same workflow triggers.

`MessengerChannel` (`app/channels/messenger.py`) parses the real Meta
Messenger webhook payload shape and verifies `X-Hub-Signature-256` via
HMAC-SHA256 against `FACEBOOK_APP_SECRET` — skipped gracefully (not failed
closed) when no app secret is configured, preserving the zero-setup local
path while still being secure once a real secret is present. The webhook
route (`POST /api/channels/messenger/webhook`) always returns `200`, even
when an event is ignored or malformed, because Meta retries aggressively on
non-200 responses — using a status code to signal an application-level
outcome would just trigger a retry storm.

`MockChannel` (`app/channels/mock.py`) is the zero-Meta-setup demo path — it
parses a flat `{sender_id, sender_name, text}` payload and is what
`POST /api/channels/messenger/simulate` (authenticated) and the Channels
frontend page's "Try it without any real setup" form use. It's not a stub
that gets deleted later; it's the channel the actual demo script relies on,
since no session should require a live Meta Page to show that channel-based
intake works end-to-end.

## Auth

JWT (HS256, `python-jose`), password hashing via `bcrypt` directly (not
`passlib` — see the Phase 3 build log for why: the `passlib[bcrypt]` combo is
broken against current `bcrypt` releases, since `passlib` hasn't been updated
since 2020). `get_current_user` decodes the token, loads the user, and
rejects on any of: missing header, invalid signature, expired token, no `sub`
claim, deleted user, deactivated user — all folding to the same generic `401`
so a caller can't distinguish *why* a token failed (standard practice; don't
leak which check failed).

**Access + refresh tokens (since Phase 16).** The access JWT is short-lived
(30 min default) and stateless — it can't be revoked once issued, only
allowed to expire. That's exactly why it's short: a `refresh_tokens` table
(`app/models/refresh_token.py`, storing a SHA-256 hash of the token, never
the raw value — same reasoning as password hashing) is what actually gets
revoked on logout. `POST /api/auth/refresh` exchanges a valid, unrevoked
refresh token for a new access token; the frontend does this automatically
on a 401 (`services/api.js`), so the shorter access-token lifetime doesn't
mean logging in every 30 minutes. `POST /api/auth/logout` revokes the
refresh token — the old access token remains technically valid until its own
(short) expiry, since revoking a stateless JWT isn't possible without a
denylist, which this app doesn't add given how small that exposure window
already is.

**Rate limiting on auth endpoints.** `register` (5/hour) and `login`
(10/10 min) are rate-limited per client IP using the same
`app/utils/rate_limit.py` sliding window as the public enquiry form — brute
force and registration-spam protection, not just AI-call protection.

**Owner vs. staff.** `User.role` (`owner` | `staff`) is enforced via a
`require_owner` dependency layered on top of `get_current_user` — a
logged-in staff account is fully authenticated, just not authorized for
owner-only routes: changing AI provider settings (`PATCH /api/ai/settings`),
editing the business profile (`PATCH /api/business/profile`), and managing
staff accounts themselves (`/api/business/staff/*`). Everything
operational — leads, workflows, notifications, tasks, dashboard, analytics —
stays open to both roles; the restriction is specifically the small set of
settings that affect the whole business, matching the "staff can't change
AI provider, billing, etc." framing from the Phase 16 brief. Only the
business owner can create staff accounts (`POST /api/business/staff`) — there's
no self-service staff signup.
