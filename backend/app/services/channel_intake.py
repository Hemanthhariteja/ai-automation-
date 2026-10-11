from sqlalchemy.orm import Session

from app.channels.base import InboundMessage
from app.models.business import Business
from app.models.customer import Customer
from app.models.lead import Lead
from app.services.lead_ai import run_ai_pipeline_on_lead
from app.services.workflow_trigger import trigger_workflows


def ingest_channel_message(db: Session, business: Business, channel_name: str, message: InboundMessage) -> Lead:
    """The one entry point every inbound channel funnels through — same
    classify/extract/score pipeline and the same new_enquiry workflow
    trigger as a web-form or CSV-imported lead. No email/phone is available
    from a chat platform, so unlike get_or_create_customer this doesn't
    dedupe across messages from the same sender yet (a known, documented
    simplification — see docs/ARCHITECTURE.md); the sender's platform id is
    kept on the lead itself via tracking_data so it's not lost."""
    customer = Customer(business_id=business.id, name=message.sender_name)
    db.add(customer)
    db.flush()

    lead = Lead(
        business_id=business.id,
        customer_id=customer.id,
        raw_message=message.text,
        source=channel_name,
        tracking_data={"channel": channel_name, "sender_external_id": message.sender_external_id},
    )
    db.add(lead)
    db.flush()

    run_ai_pipeline_on_lead(db, business, lead)
    trigger_workflows(db, business, lead, "new_enquiry")

    db.commit()
    return lead
