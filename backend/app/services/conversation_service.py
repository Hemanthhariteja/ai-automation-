from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.lead import Lead
from app.models.message import Message


def get_or_create_conversation_for_lead(db: Session, lead: Lead) -> Conversation:
    """Every lead has exactly one conversation thread for the MVP — enough
    for the single-message enquiry flow this app targets. Multi-conversation
    leads would need a real selection UI, out of scope for now."""
    conversation = db.query(Conversation).filter(Conversation.lead_id == lead.id).first()
    if conversation is not None:
        return conversation

    conversation = Conversation(
        business_id=lead.business_id,
        customer_id=lead.customer_id,
        lead_id=lead.id,
        channel="whatsapp_mock" if lead.source == "whatsapp_mock" else "web",
    )
    db.add(conversation)
    db.flush()

    if lead.raw_message:
        db.add(Message(conversation_id=conversation.id, sender="customer", content=lead.raw_message))
        db.flush()

    return conversation
