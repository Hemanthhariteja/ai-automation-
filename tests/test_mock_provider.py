import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.ai.base import ExtractedInfo, IntentClassification
from app.ai.mock_provider import MockProvider

provider = MockProvider()


def test_classify_unknown_text_defaults_to_general_inquiry():
    result = provider.classify_intent("asdlkfj random text with no keywords")
    assert result.intent == "general_inquiry"
    assert result.category is None


def test_classify_quote_request_with_category():
    result = provider.classify_intent("Can I get a quote for catering a corporate lunch?")
    assert result.intent == "quote_request"
    assert result.category == "catering"


def test_classify_booking_request_with_reservations_category():
    result = provider.classify_intent("I'd like to book a table for 4 this Saturday")
    assert result.intent == "booking_request"
    assert result.category == "reservations"


def test_classify_does_not_match_keywords_inside_other_words():
    # "facebook" contains "book", "comfortable" contains "table"
    result = provider.classify_intent("Saw you on facebook, the seats looked comfortable")
    assert result.intent == "general_inquiry"
    assert result.category is None


def test_classify_still_matches_word_variants():
    result = provider.classify_intent("Interested in booking, do you do catered lunches?")
    assert result.intent == "booking_request"
    assert result.category == "catering"


def test_extract_information_never_invents_missing_fields():
    result = provider.extract_information("hello")
    assert result.email is None
    assert result.phone is None
    assert result.budget is None
    assert result.location is None
    assert result.preferred_date is None


def test_extract_email_and_urgency():
    result = provider.extract_information("Contact me at jane@example.io, this is urgent")
    assert result.email == "jane@example.io"
    assert result.urgency == "high"


def test_score_band_boundaries_match_claude_md_spec():
    # 0-30 low / 31-70 medium / 71-100 high
    low_classification = IntentClassification(intent="general_inquiry", category=None, confidence=0.4)
    low_extracted = ExtractedInfo()
    low_result = provider.score_lead(low_classification, low_extracted, "hi")
    assert low_result.score <= 30

    high_classification = IntentClassification(intent="quote_request", category="catering", confidence=0.9)
    high_extracted = ExtractedInfo(budget="$5000", urgency="high", email="a@b.io", phone="555-1234", preferred_date="tomorrow")
    high_result = provider.score_lead(
        high_classification, high_extracted, "I urgently need a catering quote for a wedding with budget $5000"
    )
    assert high_result.score >= 71


def test_score_is_always_within_0_to_100():
    classification = IntentClassification(intent="quote_request", category="private_events", confidence=0.9)
    extracted = ExtractedInfo(budget="$999999", urgency="high", email="a@b.io", phone="555-1234", preferred_date="today")
    result = provider.score_lead(classification, extracted, "x " * 200)
    assert 0 <= result.score <= 100


def test_score_large_party_size_scores_higher_than_small_party():
    classification = IntentClassification(intent="booking_request", category="reservations", confidence=0.9)
    small = provider.score_lead(classification, ExtractedInfo(), "table for 2 tonight")
    large = provider.score_lead(classification, ExtractedInfo(), "table for 12 tonight")
    assert large.breakdown["party_size"] > small.breakdown["party_size"]
    assert large.score > small.score


def test_score_private_events_category_outweighs_delivery_takeout():
    extracted = ExtractedInfo()
    private_event = provider.score_lead(
        IntentClassification(intent="quote_request", category="private_events", confidence=0.9), extracted, "hi"
    )
    delivery = provider.score_lead(
        IntentClassification(intent="quote_request", category="delivery_takeout", confidence=0.9), extracted, "hi"
    )
    assert private_event.breakdown["category_value"] > delivery.breakdown["category_value"]
    assert private_event.score > delivery.score


def test_generate_response_includes_contact_info_when_configured():
    profile = {
        "name": "The Copper Spoon",
        "services": None,
        "hours": None,
        "contact_email": "hello@thecopperspoon.io",
        "contact_phone": "555-0100",
        "tone": "friendly",
    }
    response = provider.generate_response(profile, "hi", ExtractedInfo())
    assert "hello@thecopperspoon.io" in response.text
    assert "555-0100" in response.text


def test_generate_response_omits_unconfigured_fields():
    profile = {"name": "The Copper Spoon", "services": None, "hours": None, "contact_email": None, "contact_phone": None, "tone": "professional"}
    response = provider.generate_response(profile, "hi", ExtractedInfo())
    assert "reach us directly" not in response.text.lower()


def test_summarize_empty_conversation():
    result = provider.summarize([])
    assert result.summary == "No conversation content to summarize."


def test_summarize_whitespace_only_messages():
    result = provider.summarize(["   ", ""])
    assert result.summary == "No conversation content to summarize."


def test_summarize_single_message():
    result = provider.summarize(["Just one message here"])
    assert result.summary == "Just one message here"


def test_summarize_multiple_messages():
    result = provider.summarize(["First message", "Second message", "Third message"])
    assert "3 messages exchanged" in result.summary
    assert "First message" in result.summary
    assert "Third message" in result.summary
