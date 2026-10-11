# AI-Powered Small Business Automation Platform — Project Report

## Abstract

Small businesses that handle customer enquiries manually — a shared inbox, a
notebook, a spreadsheet — lose track of leads, respond inconsistently, and
have no visibility into which enquiries actually matter. This project builds
a small, self-contained CRM that automates the first stage of that workflow:
an enquiry comes in, an AI layer classifies it, extracts structured
information from it, scores it, and can draft a grounded reply; a rule-based
workflow engine reacts to the result (escalating priority, notifying the
owner, creating a follow-up task); and a dashboard gives the owner a single
place to see all of it. The system is built to run entirely offline with zero
paid dependencies — a rule-based "Demo Mode" AI provider is the guaranteed
default, with optional (never required) integration points for a local model
or free-tier cloud APIs, connected through a provider-abstraction layer with
an automatic fallback chain. The result is a working, tested, four-part system
(FastAPI backend, React frontend, SQLite database, and a custom workflow
engine) built incrementally across twenty phases — including committing to
a single vertical (restaurants), adding a real, non-web-form intake channel
(Instagram/Facebook Messenger) alongside the original public web form, and a
versioned Alembic migration path plus CSV export and DB backup/restore for
real data-lifecycle use — with 240 automated tests covering 94% of backend code.

## Problem statement

Small businesses — the kind with one owner and no dedicated sales or support
staff — typically handle customer enquiries through whatever channel is
easiest (a phone number, a contact form that emails them, a WhatsApp number)
and process them by hand. This has three recurring failure modes: enquiries
get lost or forgotten because there is no structured record of them; the
owner cannot tell, at a glance, which of ten enquiries needs urgent attention
and which is a low-priority information request; and responses, when they
happen, are inconsistent because nothing is tracking what has and hasn't been
said to a given customer. Existing CRM software solves parts of this, but
general-purpose CRMs (Salesforce, HubSpot, Zoho) are built for teams with
dedicated sales operations, carry subscription costs a single-owner business
may not want to pay, and require configuration effort disproportionate to a
business that receives a handful of enquiries a day. This project asks a
narrower question: what does the *minimum* useful version of "AI reads your
enquiries and helps you act on them" look like, built by one person, on one
laptop, for free?

## Existing system

The realistic baseline this project is compared against is not "no system" —
it's the informal combination of a contact form, an email inbox, and the
owner's memory. Enquiries arrive as unstructured text with no consistent
metadata (no lead score, no category, no linked customer history). Follow-up
is manual and easy to forget. There is no dashboard, no reporting, and no way
to see, in aggregate, what kinds of enquiries are actually coming in. General
CRM software (see above) addresses volume and team coordination but is
disproportionate — in cost, complexity, and setup time — for a business this size.

## Proposed system

A single web application, self-hosted or run locally, that:

1. Accepts a customer enquiry (a free-text message, optionally with contact
   details) through a simple form.
2. Runs it through an AI layer that classifies intent, extracts structured
   fields (name, email, phone, budget, urgency, etc. — leaving anything not
   actually present as `null`, never invented), and computes a legible
   0–100 priority score.
3. Evaluates a small set of owner-configured rules (a linear
   trigger → condition → action workflow) against the result — escalating
   priority, notifying the owner, creating a follow-up task, or drafting an
   AI reply, automatically.
4. Surfaces all of this through a dashboard and a set of analytics charts.
5. Runs this AI layer through a provider abstraction that defaults to a
   zero-dependency, zero-cost rule-based mode, with optional (never required)
   integration points for a local or free-tier cloud model — so the system
   never *requires* a paid API, and never crashes when one isn't configured.

## Objectives

- Build a lead-intake pipeline that goes from raw enquiry text to a
  classified, scored, structured record with no manual data entry.
- Build an AI provider abstraction where the active provider is swappable at
  runtime and failures degrade gracefully (documented fallback, never a crash).
- Build a workflow engine expressive enough to implement the two example
  rules given in the project brief (`score > 80 → notify`,
  `intent == complaint → high priority`) and demonstrably extensible without
  rewriting the engine.
- Build a usable frontend covering the full loop: submit an enquiry, see it
  classified, see a workflow react to it, see it on a dashboard, see it in
  aggregate analytics.
- Do all of the above at zero mandatory cost, on a CPU-only, low-RAM machine,
  incrementally, with a working and tested system after every phase.

## Scope

**In scope:** single-tenant-per-business lead management; AI
classification/extraction/scoring/response-generation/summarization; a
linear (non-branching) workflow engine with a fixed set of trigger/condition/
action types; a visual (non-canvas) workflow viewer/editor; a dashboard and
seven analytics charts; JWT authentication; a Demo Mode that requires no
external dependency.

**Explicitly out of scope** (stated up front, not discovered as a limitation
later): automated replying on any messaging channel (Messenger receiving is
real; replying is explicitly simulated/logged, never sent), Salesforce-level
CRM feature parity, Zapier-level workflow branching and third-party
connectors, training a custom or fine-tuned model, Kubernetes or
microservices, and any workflow that would require paying for infrastructure
by default.

## Requirements

**Functional** — user registration and login; business profile
configuration; lead CRUD with filtering and search; AI classification,
extraction, scoring, response generation, and summarization; a workflow
engine supporting the trigger/AI-processor/condition/action/notification/DB/end
node vocabulary; four ready-made rule templates; notifications and tasks;
a dashboard summary; analytics aggregation and visualization.

**Non-functional** — must run with zero paid API keys configured (Demo Mode);
must not crash on missing or invalid AI configuration; must run on a CPU-only,
low-RAM machine; must not perform uncontrolled/unbounded external API calls
(explicit timeouts, retry caps, input/output length limits); secrets must
never be committed to source control or exposed to the frontend; every phase
of development must leave the system in a working, tested state.

## System architecture

```
        React SPA (Vite)
              │  HTTPS/JSON, JWT bearer
              ▼
        FastAPI application
   ┌──────────┼──────────────┐
   ▼          ▼              ▼
 api/       services/       workflows/
 (routes)   (business       (linear node
            logic)          executor)
              │                 │
              ▼                 ▼
            ai/ (provider abstraction + fallback orchestrator)
              │
      ┌───────┼────────┬─────────┬─────────┐
      ▼       ▼         ▼         ▼         ▼
    Demo    Local     HF free   Gemini    OpenAI
   (Mock)  (Ollama)    tier
              │
              ▼
           SQLite (13 tables, via SQLAlchemy ORM)
```

Layering rationale: `api/` handles only HTTP concerns (auth, ownership
checks, request/response shaping); `services/` holds logic reused by both API
routes and workflow action nodes (so, for example, "generate an AI response"
is implemented exactly once and called from two different entry points);
`ai/` is a strict interface (`AIProvider`) with one required implementation
per provider and a single orchestrator (`AIService`) that owns the fallback
chain and the audit log. This separation is what let the workflow engine
(Phase 8) reuse the AI pipeline (Phase 6/7) without duplicating any classification
or generation logic.

## Data flow

1. A client submits `POST /api/leads` with a free-text message.
2. The request is authenticated (JWT) and scoped to a business.
3. A `Customer` is found or created from explicit or AI-extracted contact info.
4. A `Lead` row is inserted.
5. The AI pipeline runs (classify → extract → score), each step going through
   the provider fallback chain and writing an audit row to `ai_logs`.
6. Every active workflow matching the `new_enquiry` (and, if applicable,
   `new_customer`) trigger is executed against the lead — each node in the
   workflow reads and/or writes lead/notification/task state.
7. One transaction commits the lead, its AI fields, and every workflow
   side-effect together.
8. The frontend dashboard and analytics pages poll the resulting aggregate
   endpoints (`/api/dashboard/summary`, `/api/analytics/overview`) to reflect
   the new state.

## Database design

Thirteen tables, SQLite via SQLAlchemy 2.0 ORM (types chosen to remain
Postgres-portable; as of Phase 20 this is backed by an actual Alembic
migration, not just an aspiration — see Algorithms/Architecture notes below):

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | login credentials, role | belongs to one `business` |
| `businesses` | the tenant boundary; profile fields the AI is grounded in; AI provider choice | has many of everything below |
| `customers` | contact info, deduped by email within a business | has many `leads`, `conversations` |
| `leads` | the core record — raw message, AI classification/extraction/score, status, priority | belongs to `business`, optionally `customer` |
| `conversations` | one per lead (current scope) | has many `messages` |
| `messages` | individual turns (customer/ai/owner) | belongs to `conversation` |
| `workflows` | name, trigger type, active flag | has many `workflow_nodes`, `workflow_executions` (cascade delete) |
| `workflow_nodes` | ordered graph nodes, JSON `config` | belongs to `workflow` |
| `workflow_executions` | one row per run, JSON step log | belongs to `workflow`, optionally `lead` |
| `tasks` | follow-up items | belongs to `business`, optionally `lead` |
| `notifications` | owner-facing alerts | belongs to `business` |
| `ai_logs` | audit trail: requested vs. actual provider, fallback reason, latency, success | belongs to `business`, optionally `lead` |
| `refresh_tokens` | hashed refresh tokens, revocation timestamp | belongs to `user` |

Every business-owned table carries a `business_id` foreign key, enforced at
the query layer (every route filters by the caller's business, resolved from
the JWT) rather than at the database constraint layer — a pragmatic choice
for a single-process SQLite application where the application is the only
writer.

## AI / workflow architecture

Described in full in `docs/ARCHITECTURE.md`; summarized here for the report
format. The AI layer is a strategy-pattern abstraction: one interface
(`AIProvider`, five methods — classify, extract, score, generate response,
summarize), five implementations, and one orchestrator (`AIService`) that
resolves a per-business fallback chain (`[primary, fallback, "demo"]`) and
tries each in order, catching every exception (not only the typed
`AIProviderError`), so a provider bug can never propagate to the caller. The
workflow engine is a linear interpreter: a `Workflow` is an ordered list of
typed nodes; `WorkflowEngine.execute()` walks them, dispatching to a
per-node-type handler function, accumulating a structured log, and — the same
guarantee as the AI layer — catching any handler exception so a broken
workflow can never break the request that triggered it.

## Algorithms

**Lead scoring** (`app/ai/mock_provider.py::score_lead`) is an additive
formula over seven legible, independently-computed factors — five generic
ones (the classified intent, weighted by how strongly it signals a real
transaction: quote/booking request scores higher than a general inquiry;
whether a budget was mentioned; urgency level; completeness of extracted
fields; message specificity, word count as a proxy) plus two restaurant-
vertical-specific signals added in Phase 19: **party size** (a group size
parsed out of the message text — `"table for 12"`, `"party of 8"`, `"20
guests"` — since a larger party is worth more to a restaurant) and
**category value** (the classified category weighted by typical revenue —
`private_events` and `catering` outrank a routine `reservations` or
`delivery_takeout` enquiry). All seven are summed and clamped to `[0, 100]`,
then read as low (0–30) / medium (31–70) / high (71–100). Swapping the vertical
means swapping `CATEGORY_KEYWORDS` (already vertical-specific since Phase 18)
and `CATEGORY_VALUE_SCORES` — configuration, not a rewrite of the scoring
function. This is explicitly a heuristic scoring rule, not a trained or
statistically validated model, and is documented as such everywhere it's
surfaced (API responses, the Analytics page, this report).

**Intent classification and information extraction** in Demo Mode are
keyword/regex matching (a fixed vocabulary of intents and categories matched
against the message text; regex for email, phone, budget mentions, and
urgency keywords). This is a deliberate, honestly-labeled limitation: a
message that doesn't contain a matched keyword falls back to a generic
`general_inquiry` classification even when a human reader would infer more —
see Limitations.

**Condition evaluation** (`app/workflows/nodes.py::evaluate_condition`)
supports a simple `{field, operator, value}` clause or a compound
`{logic: all|any, clauses: [...]}` structure, evaluated via a small operator
table (`eq, neq, gt, gte, lt, lte, contains`) against either a direct `Lead`
column or a dotted path into the AI-extracted JSON (`extracted_data.<key>`).

## Implementation

Built in fifteen incremental phases (see the project's build log / commit
history for the full detail per phase): scaffolding; database models; JWT
auth; lead CRUD; the AI provider abstraction and Demo Mode; AI classification
wired into lead intake; response generation and business profile; the
workflow engine core; compound conditions and rule templates; the dashboard
and its supporting notification/task/summary endpoints; a visual workflow
builder; analytics with a validated color palette; a dedicated testing pass;
documentation (this report); demo preparation. Each phase produced a working,
manually-verified (and, from the auth phase onward, automatically tested)
increment before the next began — no phase depended on unfinished work from a
later one.

Backend: Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic v2, `python-jose` +
`bcrypt` for auth, `httpx` for outbound provider calls. Frontend: React 19 via
Vite, `react-router-dom`, `axios`, `recharts`. No message queue, cache, or
container orchestration — a single process and a single SQLite file, matching
the project's own low-resource constraint.

## Testing

240 automated tests (`pytest`), 94% line coverage on the backend
(`backend/app`), covering: authentication (including edge cases unreachable
through normal API flows — a token missing its subject claim, a deactivated
account, a deleted user — tested by calling the auth dependency functions
directly); lead CRUD and cross-business isolation; AI classification,
extraction, and the exact scoring band boundaries this report describes above;
provider fallback under both "not configured" and genuinely unexpected
exceptions (verified via monkeypatching to force a real crash inside a
provider and confirming the system still returns a clean result); workflow
execution, including every action type, compound conditions, cascade deletes,
and a node handler that raises a raw exception; the `Channel` abstraction
(Messenger payload parsing, webhook signature verification, the simulate
endpoint, cross-business isolation on the same webhook); CSV export
(filter parity with the list endpoint, cross-business isolation) and the
Alembic-managed migration/backup path (a real backup→data-loss→restore
round trip against a live SQLite file, not just mocked calls); and Demo
Mode's complete, zero-configuration operation. The remaining uncovered lines
are almost entirely the application's real-database bootstrap path
(`init_db`/`get_db`), which is deliberately exercised by manual live-server
verification at the end of every phase rather than by the automated suite,
since covering it would mean touching a real database file during CI runs.
The frontend has no automated test suite; it was verified manually in-browser
at the end of each phase that touched it.

## Results

The system implements the full loop described in the proposed system section
and matches the demo script in `docs/DEMO_GUIDE.md` end-to-end: a submitted
enquiry is classified, scored, and (optionally) responded to automatically; a
configured workflow reacts to the result without manual intervention;
notifications and tasks appear; the dashboard and analytics reflect the new
state; and switching the active AI provider to an unreachable one, live,
demonstrably falls back to Demo Mode with the reason surfaced in the API
response and the audit log — with no internet connection required for that
fallback to work correctly, since Demo Mode makes zero network calls. All of
the above was exercised against the running application (not only inferred
from code) during development, with request/response pairs captured in the
phase-by-phase build log.

No claims are made here about business impact, conversion rates, or time
saved — no field trial with a real business was conducted; this is a
functional prototype evaluated on correctness and coverage, not a validated
business outcome.

## Limitations

- **The workflow engine does not support branching.** A condition node either
  lets execution continue or halts everything after it — there is no
  `if/else` graph. Two independent rules on the same trigger require two
  separate workflows (which the engine does support, running each
  independently), not one workflow with a fork.
- **Only the Demo Mode AI provider has real classification/extraction/
  generation logic.** The Local (Ollama), Hugging Face free-tier, Gemini, and
  OpenAI providers have real, working connection-status checks and correctly
  participate in the fallback chain, but their generation methods intentionally
  raise a clear "not implemented yet" error rather than pretending to call a
  real model — this is a scoping decision made and documented during
  development (Phase 5), not a defect discovered after the fact.
- **Demo Mode's classification is keyword-based**, not a trained language
  model — a message that doesn't contain an expected keyword can be
  under-classified (e.g. an urgent, high-budget message that never uses the
  words "quote," "price," or "cost" may be classified as a generic inquiry).
  This was observed directly during development and is reported honestly
  rather than smoothed over.
- **The lead score is a heuristic**, not a statistically validated predictive
  model; it should be read as a legible summary of a few signals, not a
  probability of conversion.
- **No real outbound side effects.** Email sending and Messenger replying are
  both explicitly simulated (logged, never actually sent). Inbound Messenger
  *receiving* is real (a real Meta webhook, real signature verification), but
  the system never sends a message back on its own.
- **Single conversation per lead.** The data model supports multiple, but the
  current implementation always finds-or-creates exactly one thread per lead,
  matching the single-message-enquiry use case this project targets.
- **No scheduled trigger execution.** `scheduled` is a valid `trigger_type`
  value with no background scheduler wired to fire it.
- **No automated frontend test suite.**
- **Single business per registered user**, with no "invite a teammate" flow
  yet, though the data model (`User.business_id`) supports multiple staff per business.

## Future scope

Wire real prompt-based generation into the four non-demo AI providers;
introduce branching or parallel-path workflows if a real use case demands it;
build a lightweight background scheduler for the `scheduled` trigger type;
add a frontend automated test suite (Vitest + React Testing Library); support
multiple staff users per business with an invite flow and role-based
permissions; consider a real-time channel (WebSockets) for notifications
instead of polling; evaluate whether a trained or fine-tuned classification
model would meaningfully outperform the current keyword-based approach for
this project's actual message volume, before adopting one.

## Conclusion

This project set out to build the smallest useful version of an AI-assisted
small-business CRM, under a strict zero-mandatory-cost, low-resource
constraint, incrementally and verifiably. The resulting system implements a
complete lead-intake-to-action loop — classification, extraction, scoring,
response generation, and a rule-based workflow engine — behind a provider
abstraction that degrades safely rather than failing, backed by a tested
(240 tests, 94% backend coverage) and honestly-documented implementation.
Its limitations — a linear workflow engine, a heuristic (not statistical)
scoring model, and only one AI provider with real generation logic — are
scoping decisions made and stated during development, not gaps discovered
after the fact, and are recorded here as a concrete basis for future work
rather than as unexamined shortcomings.
