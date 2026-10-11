from app.ai.base import ExtractedInfo
from app.ai.service import AIService
from app.models.business import Business
from app.models.lead import Lead
from app.models.message import Message
from app.services.conversation_service import get_or_create_conversation_for_lead


def _business_profile_dict(business: Business) -> dict:
    return {
        "name": business.name,
        "description": business.description,
        "services": business.services,
        "hours": business.hours,
        "contact_email": business.contact_email,
        "contact_phone": business.contact_phone,
        "tone": business.tone,
    }


def generate_ai_response_for_lead(db, business: Business, lead: Lead):
    """Grounds the reply only in whatever the owner actually configured on
    the business profile — never invents prices, policies, or promises. May
    raise AllProvidersFailedError (caught by the caller), but never crashes
    silently."""
    conversation = get_or_create_conversation_for_lead(db, lead)
    extracted = ExtractedInfo(**lead.extracted_data) if lead.extracted_data else ExtractedInfo()
    text = lead.raw_message or ""

    ai_service = AIService(db)
    generated, provider_used, fallback_used, fallback_reason = ai_service.generate_response(
        business, _business_profile_dict(business), text, extracted, lead_id=lead.id
    )

    message = Message(conversation_id=conversation.id, sender="ai", content=generated.text)
    db.add(message)
    db.flush()

    return conversation, message, provider_used, fallback_used, fallback_reason


def summarize_conversation(db, business: Business, lead: Lead):
    conversation = get_or_create_conversation_for_lead(db, lead)
    messages = (
        db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.id).all()
    )
    contents = [m.content for m in messages]

    ai_service = AIService(db)
    result, provider_used, fallback_used, fallback_reason = ai_service.summarize(
        business, contents, lead_id=lead.id
    )

    conversation.summary = result.summary
    db.flush()

    return conversation, provider_used, fallback_used, fallback_reason
