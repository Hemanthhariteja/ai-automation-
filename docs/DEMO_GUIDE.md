# Demo Guide

A step-by-step walkthrough of the platform, in the order CLAUDE.md's demo
script specifies. Every step here has been run for real against the actual
running app during development (not just written up) — see the phase-by-phase
build log for the exact commands and outputs. Total time: ~10 minutes.

**Two ways to run this**: seed ~23 leads instantly and skip to step 8
(`cd backend && python -m app.seed`, login `owner@thecopperspoon.io` /
`demo12345`), or build the data live by following every step below — this is
exactly how the app has been verified throughout development, so either path
is a faithful demo. The steps below assume you're building it live; if you
seeded instead, the data already reflects what steps 1–7 describe.

## 0. Start everything

```bash
# terminal 1
cd backend && python -m uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend && npm run dev
```

Open `http://localhost:5173` in a browser. **If you're restarting a dev server
mid-demo and a tab was already open, close it and open a fresh one** — Vite
occasionally serves a stale `504` after a restart otherwise (a known dev-server
quirk, not an app bug — see `README.md` Troubleshooting).

Demoing from a public URL instead of your laptop? See `docs/DEPLOYMENT.md` —
the deployed version auto-seeds the same demo data on boot.

## 1. Register a business (this is "login" for a fresh install)

Go to `/register`. Fill in your name, a business name (e.g. "The Copper
Spoon"), an email, and a password (8+ characters). Submitting logs you in
immediately and lands on the Dashboard.

*(Already registered? `/login` instead.)*

## 2. Dashboard

You'll see six stat cards (total leads, new, high priority, last 7 days,
unread notifications, open tasks) — all zero on a fresh business — plus three
empty "Recent" panels. This is the home base you'll return to after each step below.

## 3. Configure the business profile (grounds everything AI generates)

Go to **Business Profile**. Fill in services, hours, and contact info, e.g.:

- Services: `Dine-in, takeout & delivery, private event catering, group reservations`
- Hours: `Tue-Sun 11am-10pm, closed Mondays`
- Contact email: `hello@thecopperspoon.io`

Save. This matters for step 6 — the AI will only ever mention what's here.

## 4. Set up a workflow (so step 5 has something to fire)

Go to **Workflows** → **Use this template** on **"Escalate complaints"** (or
build your own — see `docs/API_DOCUMENTATION.md`/the Workflows page for node
types). This creates a `new_enquiry`-triggered workflow: if the AI classifies
a lead as a complaint, set its priority to high and post a notification.

Click into it to see the **visual pipeline** — colored node cards connected
top to bottom (trigger → condition → action → notification → end), each
showing a human-readable summary of what it does, not raw JSON.

## 5. View leads, then submit a new enquiry

Go to **Leads** (empty for now). Click **Submit new enquiry** and enter a
message a real prospective customer might send:

> "Complaint: the food arrived cold and the service was really slow last night"

Leave the customer fields blank (the real-world flow: no structured form, just
a message) and submit.

## 6. Watch it happen: classify → extract → score → respond → workflow fires

Click into the new lead. You'll see, all populated automatically:

- **Intent**: `complaint`, with a confidence score
- **Extracted info**: whatever the message actually contained (missing fields
  show as `null` — nothing is invented)
- **Score**: 0–100, with a visible breakdown by factor
- **Priority**: already **`high`** — the workflow from step 4 fired automatically
  the instant the lead was created, no manual action taken

Click **Generate AI response** — a reply appears in the conversation thread,
using only the business profile info from step 3. Click **Summarize
conversation** to see that work too.

## 7. Notification appeared, follow-up task exists

Go back to **Dashboard**. The "Unread notifications" stat is now ≥1, and the
notification from the workflow ("A complaint just came in...") appears in the
Notifications panel. (This particular template doesn't add a task — try the
**"Auto-respond and schedule follow-up"** template on a second lead if you
want to see the Tasks panel populate too.)

## 8. Channels — the second real intake path

Go to **Channels**. The web form (steps 5–7) is always on; this page is about
the *other* way customer messages arrive: Instagram/Facebook Messenger.

- Under **Messenger / Instagram**, status reads "Not configured" — expected
  with no real Meta credentials, and the rest of the app is completely
  unaffected either way.
- Under **Try it without any real setup**, type a message (e.g. "Can I book a
  table for 2 this Friday?") and click **Simulate inbound message** — it runs
  through the *exact same* pipeline a real Messenger message would: classify,
  extract, score, trigger workflows. Click through to the created lead to see
  it's indistinguishable from a web-form one, just tagged `source: messenger`.

This is the zero-setup way to demo "customers can message the business
directly and the AI/CRM handles it" without a live Meta Page.

## 9. AI Provider Settings — the fallback demo

This is the moment CLAUDE.md's demo script is really about. Go to **AI
Provider**. You'll see all 5 providers listed with live status:

- **demo** — always `Connected` (it's the guaranteed path)
- **local** — `Unavailable` unless you have Ollama running
- **free_api / gemini / openai** — `Unavailable` unless a key is set in `.env`

Currently `demo` is marked **primary**. Click **Set primary** on **local**
(leave `demo` as the fallback, already the default). Now:

1. Go back to **Leads**, submit another enquiry.
2. It still gets classified, extracted, scored, and (if you generate one) a
   response — **with no internet required**, because `local` isn't
   reachable, so the chain fell through to `demo` transparently.
3. Scroll down to **Test the pipeline** on the AI Provider page, run any
   sample text, and look at the result: `provider_used: "demo"`,
   `fallback_used: true`, with the exact reason ("local: ... not wired up yet"
   or "could not reach Ollama").

Every one of these attempts is in the audit trail — see the **Analytics**
page's "AI provider usage" chart, which will now show a stacked bar for
`demo` with a visible fallback segment.

## 10. Analytics

Go to **Analytics**. With a few leads submitted, you'll see all seven charts
populated: leads over time, by status/priority/intent, score distribution,
and the two "outcome" charts (AI provider usage, workflow performance). Toggle
your OS dark mode to see the charts re-validate against the dark palette.

## What this demo does *not* claim

- The lead score is a transparent heuristic (documented on the Analytics page
  itself), not a validated statistical model.
- "Local"/"Free-tier"/"Gemini"/"OpenAI" providers report real connection
  status but don't yet run real generation — the fallback to Demo Mode you saw
  in step 9 is the actual, correct, tested behavior today, not a placeholder.
- No real email or Messenger reply is ever sent by the `send_email` /
  `send_messenger_reply` workflow actions — both are explicitly simulated and
  logged as such. The Messenger channel ships with real *receiving*;
  automated replying is documented future work, not silently pretended to work.
