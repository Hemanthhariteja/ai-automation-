import re

from app.ai.base import (
    AIProvider,
    ExtractedInfo,
    GeneratedResponse,
    IntentClassification,
    LeadScoreResult,
    SummaryResult,
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\-\s]{5,14}\d)")
BUDGET_RE = re.compile(r"(?:₹|rs\.?|inr|\$|usd)\s?[\d,]+(?:\.\d+)?|\b\d{4,}\s?(?:rupees|dollars)\b", re.IGNORECASE)
DATE_HINT_RE = re.compile(
    r"\b(today|tomorrow|next week|next month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
PARTY_SIZE_RE = re.compile(
    r"(?:party of|table for|group of|reservation for)\s*(\d{1,3})|\b(\d{1,3})\s*(?:people|guests|pax)\b",
    re.IGNORECASE,
)

INTENT_KEYWORDS = {
    "quote_request": ["quote", "price", "cost", "estimate", "how much", "pricing"],
    "complaint": ["complaint", "unhappy", "not working", "broken", "issue with", "problem with", "disappointed"],
    "support_request": ["help", "support", "not able to", "trouble", "error", "issue", "hasn't arrived", "missing"],
    "booking_request": ["book", "schedule", "reserve", "table for", "party of", "appointment"],
    "information_request": ["information", "info about", "tell me about", "what do you offer", "learn more"],
}

# Restaurant vertical (see docs/PROJECT_REPORT.md — this default configuration
# is deliberately committed to one business type, per the niche-pivot phase,
# rather than staying generic). Swapping this dict is the whole surface area
# needed to re-target Demo Mode at a different vertical.
CATEGORY_KEYWORDS = {
    "reservations": ["table", "reservation", "party of", "seating", "walk-in", "walk-ins"],
    "catering": ["catering", "cater", "corporate lunch", "buffet", "drop-off lunch", "office lunch"],
    "private_events": ["private event", "private dining", "birthday party", "anniversary", "venue hire", "engagement party", "wedding"],
    "delivery_takeout": ["delivery", "takeout", "takeaway", "online order", "pickup", "takeout containers"],
}

URGENCY_KEYWORDS = {
    "high": ["urgent", "asap", "immediately", "right away", "critical"],
    "medium": ["soon", "this week", "quickly"],
}

# Restaurant vertical-specific scoring signal: private events and catering
# leads represent a much larger average ticket than a routine reservation or
# a takeout order, so they're weighted higher — see CLAUDE.md's Phase 19 note
# and docs/PROJECT_REPORT.md's Algorithms section.
CATEGORY_VALUE_SCORES = {
    "private_events": 10,
    "catering": 8,
    "reservations": 3,
    "delivery_takeout": 1,
}


def _keyword_hits(text: str, keywords: list[str]) -> int:
    # Anchored to the start of a word so "book" doesn't match "facebook" and
    # "table" doesn't match "comfortable". Deliberately not anchored at the
    # end, so "book" still matches "booking" and "cater" matches "catered".
    return sum(1 for kw in keywords if re.search(rf"\b{re.escape(kw)}", text))


def _extract_party_size(text: str) -> int | None:
    match = PARTY_SIZE_RE.search(text)
    if not match:
        return None
    value = match.group(1) or match.group(2)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class MockProvider(AIProvider):
    """Demo Mode — deterministic, rule-based, zero dependencies and zero
    network calls. This is the guaranteed fallback: it never fails, so the
    app always has a working AI layer even with no API keys and no internet."""

    name = "demo"
    label = "FREE"

    def check_connection(self) -> tuple[bool, str]:
        return True, "Demo Mode is always available"

    def classify_intent(self, text: str) -> IntentClassification:
        lowered = text.lower()
        best_intent = "general_inquiry"
        best_hits = 0
        for intent, keywords in INTENT_KEYWORDS.items():
            hits = _keyword_hits(lowered, keywords)
            if hits > best_hits:
                best_intent = intent
                best_hits = hits

        best_category = None
        best_cat_hits = 0
        for category, keywords in CATEGORY_KEYWORDS.items():
            hits = _keyword_hits(lowered, keywords)
            if hits > best_cat_hits:
                best_category = category
                best_cat_hits = hits

        confidence = 0.9 if best_hits >= 2 else 0.7 if best_hits == 1 else 0.4
        return IntentClassification(intent=best_intent, category=best_category, confidence=confidence)

    def extract_information(self, text: str) -> ExtractedInfo:
        email_match = EMAIL_RE.search(text)
        phone_match = PHONE_RE.search(text)
        budget_match = BUDGET_RE.search(text)
        date_match = DATE_HINT_RE.search(text)

        lowered = text.lower()
        urgency = None
        for level, keywords in URGENCY_KEYWORDS.items():
            if _keyword_hits(lowered, keywords):
                urgency = level
                break

        product_or_service = None
        for category, keywords in CATEGORY_KEYWORDS.items():
            if _keyword_hits(lowered, keywords):
                product_or_service = category
                break

        return ExtractedInfo(
            name=None,  # not reliably inferable from free text without real NLP — stays null
            email=email_match.group(0) if email_match else None,
            phone=phone_match.group(0).strip() if phone_match else None,
            product_or_service=product_or_service,
            budget=budget_match.group(0) if budget_match else None,
            location=None,  # same reasoning as name
            requirement=text.strip()[:500] if text.strip() else None,
            urgency=urgency,
            preferred_date=date_match.group(0) if date_match else None,
        )

    def score_lead(
        self, classification: IntentClassification, extracted: ExtractedInfo, text: str
    ) -> LeadScoreResult:
        breakdown = {}

        intent_scores = {
            "quote_request": 20,
            "booking_request": 20,
            "complaint": 8,
            "support_request": 6,
            "information_request": 10,
            "general_inquiry": 8,
        }
        breakdown["intent"] = intent_scores.get(classification.intent, 8)

        breakdown["budget_mentioned"] = 18 if extracted.budget else 0

        urgency_scores = {"high": 17, "medium": 8, None: 0}
        breakdown["urgency"] = urgency_scores.get(extracted.urgency, 0)

        filled = sum(
            1
            for v in [extracted.email, extracted.phone, extracted.product_or_service, extracted.preferred_date]
            if v
        )
        breakdown["completeness"] = min(filled * 4, 12)

        word_count = len(text.split())
        breakdown["specificity"] = 8 if word_count >= 25 else 4 if word_count >= 10 else 1

        # Restaurant-specific signals (Phase 19) — not part of the generic
        # factor set above, deliberately vertical-specific: how many people
        # the enquiry is for, and how inherently valuable its category is to
        # a restaurant's bottom line.
        party_size = _extract_party_size(text)
        if party_size is None:
            breakdown["party_size"] = 0
        elif party_size >= 8:
            breakdown["party_size"] = 15
        elif party_size >= 4:
            breakdown["party_size"] = 8
        else:
            breakdown["party_size"] = 3

        breakdown["category_value"] = CATEGORY_VALUE_SCORES.get(classification.category, 0)

        total = sum(breakdown.values())
        score = max(0, min(100, total))
        return LeadScoreResult(score=score, breakdown=breakdown)

    def generate_response(
        self, business_profile: dict, text: str, extracted: ExtractedInfo
    ) -> GeneratedResponse:
        name = business_profile.get("name") or "our team"
        hours = business_profile.get("hours")
        contact_email = business_profile.get("contact_email")
        contact_phone = business_profile.get("contact_phone")
        services = business_profile.get("services")

        lines = [f"Thanks for reaching out to {name}!"]
        if services:
            lines.append(f"We help with: {services}.")
        lines.append("We've received your message and a team member will follow up shortly.")

        contact_bits = [c for c in [contact_email, contact_phone] if c]
        if contact_bits:
            lines.append(f"You can also reach us directly at {' or '.join(contact_bits)}.")
        if hours:
            lines.append(f"Our hours: {hours}.")

        return GeneratedResponse(text=" ".join(lines))

    def summarize(self, messages: list[str]) -> SummaryResult:
        non_empty = [m.strip() for m in messages if m and m.strip()]
        if not non_empty:
            return SummaryResult(summary="No conversation content to summarize.")
        if len(non_empty) == 1:
            return SummaryResult(summary=non_empty[0][:300])

        first = non_empty[0][:150]
        last = non_empty[-1][:150]
        return SummaryResult(
            summary=f"{len(non_empty)} messages exchanged. Started with: \"{first}\". Most recent: \"{last}\"."
        )
