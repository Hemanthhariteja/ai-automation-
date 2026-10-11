# The 90-Second Demo

A scripted, timed walkthrough for a live demo (interview, recruiter call,
professor) or a screen recording. Not the full feature tour — that's
`docs/DEMO_GUIDE.md` (~10 minutes). This is the tight version: one clear
story, no dead air, no "let me just fix this real quick."

**The story in one sentence**: an enquiry comes in, AI classifies and scores
it, a workflow reacts automatically, and it all runs on zero AI API keys.

## Before you start (not part of the 90 seconds)

- [ ] `cd backend && python -m app.seed` — populated data beats an empty app.
- [ ] Both servers running, logged in as `owner@thecopperspoon.io` /
      `demo12345`, sitting on the **Dashboard**.
- [ ] Have this exact enquiry text ready to **paste**, not type live:
      `Complaint: the food arrived cold and the service was really slow, this is urgent`
- [ ] Browser window large enough that text is readable on a screen share;
      close unrelated tabs.
- [ ] Know the click path cold before you go live — rehearse once.

## The script

| Time | Action | Say |
|---|---|---|
| 0:00–0:10 | On Dashboard, already loaded | "This is a small-business CRM — enquiries come in, AI classifies and scores them, and a workflow engine reacts automatically. No manual triage." |
| 0:10–0:25 | Click **Leads** → **Submit new enquiry** → paste the complaint text → **Submit** | "Watch what happens the instant this lands — nothing else to configure." |
| 0:25–0:50 | Click into the new lead | "Classified as a complaint, scored, and priority already flipped to high — a workflow fired automatically the moment it was created." *(point at Intent, Score, Priority)* |
| 0:50–1:00 | Click **Generate AI response** | "Drafts a reply grounded only in the business profile I configured — never invents a price or a policy." |
| 1:00–1:20 | Click **Workflows** → open the workflow that just fired | "Here's the rule itself — trigger, condition, action — and the execution log showing exactly what just ran, in order." |
| 1:20–1:30 | Back to **Dashboard** | "And it updates live — new high-priority count, a notification, zero AI API keys required. This is Demo Mode; flip to a real provider and if it's unreachable, it falls back automatically." |

Total: 90 seconds if you don't pause. Rehearsed once, it's closer to 75 —
leaves room for a question mid-demo without blowing the budget.

## If you have 30 more seconds

Go to **AI Provider** settings, set primary provider to `local` (no Ollama
running), run the test pipeline again: `provider_used: "demo"`,
`fallback_used: true`, reason shown inline. This is the single most
technically interesting moment in the app — the fallback chain working live,
not simulated for the demo. Worth the extra 30 seconds if the room is technical.

## What makes this demo-safe

- Every step above has been run for real against the actual app (see the
  end-to-end walkthrough referenced in the project's build log) — this
  script isn't aspirational, it's a description of something that works.
- Demo Mode makes zero network calls, so the whole script works with no
  internet connection.
- If a step ever fails live: the honest move is naming it ("that's the one
  provider that isn't wired to real generation yet — here's why") rather
  than pretending. See `docs/ARCHITECTURE.md` for the exact, small list of
  things this project is upfront about not having finished.

## Recording tips, if making a video instead of demoing live

- 1080p minimum, cursor highlighting on if your recorder supports it.
- Record in one take against the script above rather than editing clips
  together — a single continuous take is more credible and there's little
  to cut given the tight timing.
- Do the "30 more seconds" fallback demo as a natural extension if the
  video's going out standalone (no live Q&A to fill that time otherwise).
