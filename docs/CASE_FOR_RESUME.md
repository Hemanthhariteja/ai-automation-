# The Case for the Resume Line

`docs/PROJECT_REPORT.md` is the exhaustive, college-report version of this
project. This file is the short one: three design decisions worth actually
talking about in an interview, why each one was a decision and not just "how
FastAPI/React work," and the trade-off each one consciously accepts. If you
only read one doc before a technical interview about this project, read this
one.

## 1. A provider abstraction with a real fallback chain

**The problem**: an AI feature that requires a paid API key is a feature that
breaks the moment the key is missing, wrong, rate-limited, or the provider is
down — and "requires a paid API key" directly violates this project's own
₹0-mandatory constraint.

**The decision**: every AI capability (classify, extract, score, generate,
summarize) is called through one interface, `AIProvider`
(`backend/app/ai/base.py`), with five interchangeable implementations (Demo,
Local/Ollama, Hugging Face, Gemini, OpenAI). Nothing in the application calls
a provider directly — every call goes through `AIService`
(`backend/app/ai/service.py`), which resolves a per-business ordered chain
`[primary, fallback, "demo"]` and tries each in turn, catching *every*
exception a provider raises — not just a typed `AIProviderError` — because
the failure mode that actually happens in the field is never the one you
typed a class for.

**The trade-off, stated honestly**: only Demo Mode has real generation logic
today. The other four providers have real, working connection checks (they
genuinely ping Ollama, genuinely validate a Hugging Face/Gemini/OpenAI key)
and correctly participate in the fallback chain, but their `generate_response`
methods intentionally raise a clear "not wired up yet" error rather than
silently doing nothing. That's a scoping decision made and written down in
Phase 5, not a bug discovered later — and it's exactly what the fallback chain
exists to handle gracefully.

**How to talk about it**: this is a strategy pattern plus a resilience
pattern, applied to a place most tutorials don't bother — most AI-feature
demos assume the API key works. The interesting part isn't "I called
OpenAI's SDK," it's "I built the system to keep working when I *didn't*."

## 2. Demo Mode as the default, not the fallback-of-last-resort

**The problem**: if "no API key configured" is treated as an edge case, it
gets tested last, understood least, and is the thing most likely to break in
front of an evaluator with no internet in the room.

**The decision**: flip the assumption. `MockProvider`
(`backend/app/ai/mock_provider.py`) — deterministic, rule-based, zero network
calls, zero dependencies — is what the *entire application* is built and
tested against by default. It's not a stub; it has real keyword-based intent
classification, regex-based structured extraction (email/phone/budget/
urgency/date), an additive 0–100 lead-scoring formula, and template-based
response generation grounded in the business's own configured profile. Every
other provider is optional and strictly additive on top of this guaranteed
path.

**Where this shows up concretely**: the scoring formula
(`MockProvider.score_lead`) is seven independently-computed, legible factors
summed and clamped to `[0, 100]` — intent, budget mention, urgency,
completeness, specificity, plus two vertical-specific signals added when the
project committed to a restaurant niche (party size parsed from the message,
category value weighted by typical revenue). Swapping the vertical is
swapping two lookup dictionaries (`CATEGORY_KEYWORDS`,
`CATEGORY_VALUE_SCORES`), not rewriting the scoring function — the
"configuration, not a fork" principle applied to the one part of the app most
tempting to special-case.

**How to talk about it**: most people build the happy path first and the
degraded path as an afterthought. This project inverted that on purpose,
because the guaranteed, zero-dependency path is the one that has to be
bulletproof — everything else is a bonus layered on top of something that
already works.

## 3. A workflow engine that stayed additive under real pressure

**The problem**: rule engines tend to either stay so simple they can't
express real business logic, or grow into an unmaintainable branching mess
the moment a second feature needs to touch them.

**The decision**: `TRIGGER → AI PROCESSOR → CONDITION → ACTION` as a linear
interpreter (`backend/app/workflows/engine.py`) over an ordered list of typed
nodes, each dispatched to a per-node-type handler
(`backend/app/workflows/nodes.py`), accumulating a structured execution log,
with the same guarantee as the AI layer: any handler exception is caught, so
a broken workflow can never break the request that triggered it. Deliberately
*not* a branching graph — a condition either lets execution continue or halts
everything after it. Two independent rules need two separate workflows, which
the engine already supports running independently.

**The actual evidence this design holds up**: two features were added after
the engine shipped, neither of which required touching `engine.py`. Compound
`AND`/`OR` condition clauses (Phase 9) were added as a new condition-node
shape the existing evaluator already knew how to walk. A second lead-intake
channel — Instagram/Facebook Messenger, alongside the original web form
(Phase 18) — was added as a new *trigger source* (`app/services/
channel_intake.py` calls the same `trigger_workflows(..., "new_enquiry")`
every other intake path calls) with zero changes to how a workflow itself
executes. That's the concrete test of "additive, not a rewrite" — not a claim
in a doc, a diff that touches zero lines of the engine.

**How to talk about it**: the interesting engineering decision here isn't
"I built a rule engine," it's "I deliberately under-built it" — chose a
linear interpreter over a branching graph *up front*, accepted the real
limitation that comes with that, and then had two later features prove the
trade-off was survivable instead of turning into a rewrite.

## One more pattern worth mentioning if there's time: the Channel abstraction

`app/channels/` looks structurally similar to the AI provider abstraction —
one interface, multiple implementations (`MessengerChannel`, `MockChannel`) —
but is a deliberately *different* shape, and knowing why is the actual point.
Providers form a fallback chain because they're mutually exclusive
alternatives for the same job (only one is "active" at a time). Channels
don't, because a business can have the web form and Messenger both receiving
real messages simultaneously — there's no "primary channel" setting. Every
channel funnels through one function (`ingest_channel_message`) into the
identical classify → extract → score → trigger-workflows pipeline every other
lead source uses, so a Messenger-sourced lead is indistinguishable downstream
from a web-form one. Recognizing when two abstractions that *look* alike
actually need different shapes is a smaller story than the three above, but
it's a real one.
