# API Documentation

Base URL (dev): `http://localhost:8000/api`. Interactive, always-current docs
are also live at `http://localhost:8000/docs` (Swagger UI) — this file is a
prose companion, not a replacement.

All endpoints except `POST /api/auth/register`, `POST /api/auth/login`, and
`GET /api/health` require `Authorization: Bearer <token>`. Every resource is
scoped to the caller's business — you cannot see or modify another business's
data; cross-tenant access returns `404`, not `403`, so existence isn't leaked either.

Standard error shape: `{"detail": "..."}` (or a list of Pydantic validation
errors for `422`). Status codes used throughout: `200`/`201` success, `204` no
content (deletes), `400` bad request, `401` unauthenticated, `404` not found
(includes "not yours"), `422` validation error, `502` every configured AI
provider failed (rare — Demo Mode is always the last link in the chain).

---

## Auth

### `POST /api/auth/register`
Creates a `Business` and an owner `User` in one transaction, returns a token.

```json
// request
{"email": "owner@example.io", "password": "supersecret123", "full_name": "Jane Doe", "business_name": "The Copper Spoon"}
// response · 201
{"access_token": "eyJ...", "token_type": "bearer"}
```
`409` if the email is already registered.

### `POST /api/auth/login`
```json
{"email": "owner@example.io", "password": "supersecret123"}
```
`401` on wrong password or unknown email.

### `GET /api/auth/me`
Returns the current user: `id, email, full_name, role, business_id`.

---

## Business profile

Grounds every AI-generated response — the AI never uses information beyond what's here.

### `GET /api/business/profile`
### `PATCH /api/business/profile`
```json
{"description": "...", "services": "Website development, digital marketing, mobile apps, AI automation",
 "hours": "Mon-Fri 9am-6pm", "contact_email": "hello@example.io", "contact_phone": "+91-...", "tone": "friendly"}
```
All fields optional; only send what changed.

---

## Leads

### `POST /api/leads`
Creates a lead. If `raw_message` is present, it's automatically classified,
extracted, and scored before the response is returned (AI fields stay `null`
if there's no message, or if every AI provider genuinely fails — this never
blocks lead creation). If no `customer` is given but an email/phone is
*extracted* from the message, a customer is linked automatically.

```json
// request — every field optional
{"raw_message": "I need a quote for catering, budget $2000 fairly urgent",
 "source": "web_form",
 "customer": {"name": "Jane", "email": "jane@example.io", "phone": "555-1234"}}
```
Response (`201`) is a full `LeadResponse` — see shape below.

### `GET /api/leads`
Query params: `status`, `priority`, `search` (matches message or intent),
`skip`, `limit` (default 50, max 200).
```json
{"total": 12, "items": [ /* LeadResponse[] */ ]}
```

### `GET /api/leads/{lead_id}` · `PATCH /api/leads/{lead_id}` · `DELETE /api/leads/{lead_id}`
`PATCH` accepts `raw_message`, `status` (`new|contacted|qualified|won|lost`),
`priority` (`low|normal|high`) — invalid values are rejected with `422` before
touching the DB.

**`LeadResponse` shape:**
```json
{
  "id": 1, "business_id": 1, "customer_id": 1, "customer": {"id":1,"name":"...","email":"...","phone":"..."},
  "source": "web_form", "raw_message": "...",
  "intent": "quote_request", "category": "catering", "confidence": 0.7,
  "extracted_data": {"name":null,"email":null,"phone":null,"product_or_service":"catering",
                      "budget":"$2000","location":null,"requirement":"...","urgency":"high","preferred_date":null},
  "score": 71, "score_breakdown": {"intent":20,"budget_mentioned":18,"urgency":17,"completeness":4,
                                    "specificity":4,"party_size":0,"category_value":8},
  "status": "new", "priority": "normal",
  "created_at": "...", "updated_at": "..."
}
```
`party_size` and `category_value` are the two restaurant-vertical-specific
scoring signals (Phase 19) — see `docs/PROJECT_REPORT.md`'s Algorithms
section for the full rationale. `party_size` reads a group size out of the
message text (`"table for 12"`, `"party of 8"`, `"20 guests"`); larger groups
score higher. `category_value` weights the classified category by how much
revenue it typically represents for a restaurant (`private_events` >
`catering` > `reservations` > `delivery_takeout`).

### `POST /api/leads/{lead_id}/classify`
Re-runs classify/extract/score on the lead's current `raw_message` — useful
after editing it. `400` if there's no message; `502` if every provider failed.

### `GET /api/leads/{lead_id}/conversation`
Returns (creating if needed) the lead's single conversation thread and its messages.

### `POST /api/leads/{lead_id}/generate-response`
Drafts an AI reply grounded in the business profile, appends it as a message.
```json
// response
{"conversation_id": 1, "message": {"id":2,"sender":"ai","content":"..."},
 "provider_used": "demo", "fallback_used": false, "fallback_reason": null}
```

### `POST /api/leads/{lead_id}/summarize`
Summarizes the conversation's message history, stores it on the conversation.

### `GET /api/leads/import/template`
Downloads a starter CSV (`message,name,email,phone`), no auth required.

### `POST /api/leads/import`
`multipart/form-data`, field name `file`. Accepts a CSV with a `message`
column (aliases: `raw_message`, `enquiry`, `notes`) plus optional
`name`/`email`/`phone` (or `customer_name`/`customer_email`/`customer_phone`).
Each row runs through the same AI pipeline and workflow triggers as any other
lead. Row-level failures (missing message) are skipped and reported, not
fatal to the whole import. `400` if the file has no message column or exceeds
500 rows.
```json
{"total_rows": 20, "imported": 19, "skipped": 1, "errors": [{"row": 7, "reason": "Missing message"}]}
```

---

## Public (unauthenticated)

The actual customer-facing intake channel — no login, scoped by a business's
public `slug` (shown on the Business Profile page) rather than a JWT.
Rate-limited to 5 submissions per 10 minutes per (business, IP) pair.

### `GET /api/public/{slug}/business`
```json
{"name": "The Copper Spoon", "description": "...", "services": "...", "hours": "...", "contact_email": "...", "contact_phone": "..."}
```
`404` for an unknown slug.

### `POST /api/public/{slug}/leads`
```json
{"message": "I need a quote for catering a corporate lunch", "name": "Jane", "email": "jane@example.io", "phone": null,
 "tracking": {"utm_source": "facebook", "utm_medium": "cpc", "utm_campaign": "summer_sale",
              "fbclid": "IwAR...", "referrer": "https://facebook.com/", "landing_page": "https://.../enquiry/the-copper-spoon?utm_source=facebook..."}}
// response · 201
{"received": true}
```
`tracking` is optional and entirely client-supplied (`utm_source`,
`utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `gclid`, `fbclid`,
`referrer`, `landing_page`) — the frontend reads these off the enquiry page's
own URL at submit time, the standard way a marketing form attributes a lead
back to the ad/campaign that drove it. `user_agent` is captured server-side
regardless (not trustworthy from the client). Stored on `Lead.tracking_data`
and visible to the business via `GET /api/leads/{id}`, never to the public caller.

Runs the full AI pipeline and triggers `new_enquiry` workflows exactly like
an authenticated lead submission — but deliberately returns no lead detail
(id, score, classification) to the public caller; only the business sees that,
via the normal authenticated endpoints. `429` once the rate limit is hit.

---

## AI provider

### `GET /api/ai/status`
```json
{"active_provider": "demo", "active_fallback": "demo",
 "providers": [{"name":"demo","label":"FREE","connection_ok":true,"message":"...",
                "is_active_primary":true,"is_active_fallback":true}, /* ...4 more */]}
```
`label` is `FREE` / `FREE-TIER` / `PAID`. Never exposes raw keys.

### `PATCH /api/ai/settings`
```json
{"ai_provider": "local", "ai_fallback_provider": "demo"}
```
Changes take effect immediately for this business — no restart. `400` on an
unrecognized provider name. Returns the same shape as `GET /api/ai/status`.

### `POST /api/ai/test`
Runs one piece of text through the full pipeline (classify → extract → score →
generate) without needing a real lead — the fastest way to see the fallback
chain in action.
```json
{"text": "I urgently need catering for a corporate lunch, budget $1000"}
// response
{"intent":"general_inquiry","category":"catering","confidence":0.4,
 "extracted":{...},"score":63,"score_breakdown":{...},
 "response_text":"...", "provider_used":"demo","fallback_used":false,"fallback_reason":null}
```

---

## Channels

Non-web-form ways for a customer message to become a `Lead`. Unlike the AI
provider abstraction, channels don't form a fallback chain — they're
independent and can be active simultaneously (a business might take web-form
enquiries and Messenger messages at the same time). Every channel funnels
through the same `ingest_channel_message()` service, so a lead created via
Messenger runs through the identical classify → extract → score →
trigger-workflows pipeline as one submitted through the dashboard or the
public enquiry form — it's tagged `source: "messenger"` (or `"mock"`) and
`tracking_data: {"channel": ..., "sender_external_id": ...}` for traceability,
but otherwise indistinguishable.

### `GET /api/channels/status` *(authenticated)*
```json
{"channels": [
  {"name": "messenger", "configured": false, "business_connected": false},
  {"name": "mock", "configured": true, "business_connected": true}
]}
```
`configured` reflects whether the server-wide Facebook app credentials
(`FACEBOOK_VERIFY_TOKEN`/`FACEBOOK_PAGE_ACCESS_TOKEN`) are set at all;
`business_connected` reflects whether *this* business has set a
`messenger_page_id` on its profile. Both can be `false` with zero impact on
the rest of the app.

### `GET /api/channels/messenger/webhook` *(unauthenticated — Meta verification handshake)*
Query params: `hub.mode`, `hub.verify_token`, `hub.challenge`. Returns
`hub.challenge` as plain text (`200`) if `hub.verify_token` matches
`FACEBOOK_VERIFY_TOKEN`, else `403`. Called once by Meta when you register the
webhook URL in the Meta App dashboard — not something the frontend ever calls.

### `POST /api/channels/messenger/webhook` *(unauthenticated — real inbound receiver)*
Accepts the raw Meta Messenger payload shape:
```json
{"object": "page", "entry": [{"id": "<page_id>",
  "messaging": [{"sender": {"id": "<psid>"}, "message": {"text": "Can I book a table for 2?"}}]}]}
```
Verifies `X-Hub-Signature-256` against `FACEBOOK_APP_SECRET` if that's set
(skipped gracefully if it isn't — the zero-setup local path), looks up the
`Business` by `messenger_page_id` matching `entry[].id`, and ignores the event
silently if no business has connected that page. Rate-limited (60/min per IP).
**Always returns `200`**, even when the event is ignored or malformed — Meta
retries aggressively on non-200 responses, so this endpoint never uses status
codes to signal application-level outcomes.

### `POST /api/channels/messenger/simulate` *(authenticated)*
```json
{"sender_id": "demo-psid-1", "sender_name": "Priya", "text": "Can I book a table for 2 this Friday?"}
// response · 201 — a full LeadResponse, same shape as POST /api/leads
{"id": 42, "source": "messenger", "intent": "booking_request", "category": "reservations", ...}
```
`sender_id` is a stand-in for the PSID (page-scoped user id) a real Messenger
webhook would provide — any non-empty string works for the simulate path.
The zero-Meta-setup way to demo the channel: runs the exact same
`ingest_channel_message()` path as a real webhook call, just via
`MockChannel` instead of `MessengerChannel`. This is what the frontend's
Channels page uses under "Try it without any real setup."

---

## Workflows

### `POST /api/workflows` · `GET /api/workflows` · `GET/PATCH/DELETE /api/workflows/{id}`
```json
// create
{"name": "Escalate complaints", "trigger_type": "new_enquiry", "is_active": true, "description": "..."}
```
`trigger_type`: `new_enquiry | new_customer | manual | scheduled` (see
`docs/ARCHITECTURE.md` for which ones actually fire today). A `WorkflowResponse`
always includes its `nodes`, ordered by `order_index`. Deleting a workflow
cascades to its nodes and execution history.

### `POST /api/workflows/{id}/nodes` · `PATCH/DELETE /api/workflows/{id}/nodes/{node_id}`
```json
{"node_type": "condition", "order_index": 1, "config": {"field": "score", "operator": "gt", "value": 80}}
```
`node_type`: `trigger | ai_processor | condition | action | notification | db | end`.

**Condition `config` — two shapes:**
```json
{"field": "score", "operator": "gt", "value": 80}
// or, compound:
{"logic": "all", "clauses": [{"field": "extracted_data.urgency", "operator": "eq", "value": "high"},
                              {"field": "extracted_data.budget", "operator": "neq", "value": null}]}
```
Operators: `eq neq gt gte lt lte contains`. Fields: any `Lead` column
(`score, intent, category, confidence, priority, status`) or `extracted_data.<key>`.

**Action `config`** (`action` and `db` nodes share the same dispatcher):
```json
{"action_type": "update_lead_status", "value": "qualified"}
{"action_type": "set_priority", "value": "high"}
{"action_type": "save_lead"}
{"action_type": "create_notification", "message": "...", "notification_type": "high_priority_lead"}
{"action_type": "add_task", "title": "...", "description": "..."}
{"action_type": "generate_ai_response"}
{"action_type": "generate_summary"}
{"action_type": "send_email", "recipient": "...", "subject": "..."}  // SIMULATED — no real email is ever sent
{"action_type": "log_execution", "message": "..."}
```
`notification` nodes take `{"message": "...", "notification_type": "..."}` directly (no `action_type`).

### `POST /api/workflows/{id}/run`
```json
{"lead_id": 3}
// response
{"id":1,"workflow_id":1,"lead_id":3,"status":"success",
 "log":{"steps":[{"node_id":1,"node_type":"trigger","status":"ok","detail":"..."}, ...]},
 "started_at":"...","completed_at":"..."}
```
`status`: `success` (including a condition that halted — that's not a
failure) or `failed`. Always `200` — an engine-level failure never becomes an
HTTP error.

### `GET /api/workflows/{id}/executions`
Execution history, newest first.

### `GET /api/workflows/templates`
```json
[{"id":"high_score_alert","name":"High-score lead alert","description":"...","trigger_type":"new_enquiry"}, ...]
```
Four templates ship today: `high_score_alert`, `complaint_priority`,
`auto_respond_and_followup`, `urgent_and_high_budget`.

### `POST /api/workflows/templates/{template_id}`
Instantiates a template as a normal, fully-editable `Workflow` + nodes. `404` for an unknown id.

### `POST /api/workflows/evaluate-condition`
Tests a condition against a real lead without running a workflow or mutating anything.
```json
{"lead_id": 3, "config": {"field": "status", "operator": "eq", "value": "new"}}
// response
{"passed": true, "detail": "status eq 'new' (actual='new')"}
```

---

## Notifications & Tasks

### `GET /api/notifications` — query: `unread_only`, `skip`, `limit`
```json
{"total": 5, "unread_count": 2, "items": [{"id":1,"type":"high_priority_lead","message":"...","is_read":false,"created_at":"..."}]}
```
### `PATCH /api/notifications/{id}` — `{"is_read": true}`

### `GET /api/tasks` — query: `status`, `skip`, `limit`
```json
{"total": 3, "items": [{"id":1,"lead_id":5,"title":"...","description":null,"due_date":null,"status":"open","created_at":"..."}]}
```
### `PATCH /api/tasks/{id}` — `{"status": "done"}` (also accepts `title`, `description`, `due_date`)

---

## Dashboard & Analytics

### `GET /api/dashboard/summary`
```json
{"total_leads":12,"new_leads":8,"high_priority_leads":2,"leads_last_7_days":5,
 "unread_notifications":3,"open_tasks":4,
 "recent_leads":[...5 max...], "recent_notifications":[...5 max...], "recent_tasks":[...5 max, open only...]}
```

### `GET /api/analytics/overview`
Last 30 days, this business only.
```json
{"leads_over_time":[{"date":"2026-08-15","count":3}],
 "leads_by_status":[{"label":"new","count":8}],
 "leads_by_priority":[{"label":"high","count":2}],
 "leads_by_intent":[{"label":"quote_request","count":4}],
 "score_distribution":{"low":3,"medium":5,"high":4},
 "provider_usage":[{"provider":"demo","total_calls":36,"fallback_calls":0}],
 "workflow_performance":[{"workflow_id":1,"workflow_name":"...","total_executions":10,"success_count":9,"failed_count":1}]}
```

---

## Health

### `GET /api/health` — no auth
```json
{"status": "ok", "app_name": "AI Small Business Automation Platform", "environment": "development"}
```
