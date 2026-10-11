from app.ai.service import AIService, AllProvidersFailedError
from app.models.business import Business
from app.models.lead import Lead
from app.schemas.lead import LeadCustomerInfo
from app.services.customer_service import get_or_create_customer


def run_ai_pipeline_on_lead(db, business: Business, lead: Lead) -> tuple[bool, bool]:
    """Classifies, extracts, and scores a lead's raw_message in place, and
    links/backfills a customer from the extracted contact info if the lead
    didn't already have one. Returns (ai_ran, customer_created) — ai_ran is
    False (leaving AI fields null) if every provider in the fallback chain
    failed; this must never raise, since lead creation has to succeed even
    when AI classification can't run."""
    if not lead.raw_message:
        return False, False

    ai_service = AIService(db)
    try:
        classification, *_ = ai_service.classify_intent(business, lead.raw_message, lead_id=lead.id)
        extracted, *_ = ai_service.extract_information(business, lead.raw_message, lead_id=lead.id)
        score_result, *_ = ai_service.score_lead(
            business, classification, extracted, lead.raw_message, lead_id=lead.id
        )
    except AllProvidersFailedError:
        return False, False

    lead.intent = classification.intent
    lead.category = classification.category
    lead.confidence = classification.confidence
    lead.extracted_data = extracted.to_dict()
    lead.score = score_result.score
    lead.score_breakdown = score_result.breakdown

    customer_created = False
    if lead.customer_id is None and (extracted.email or extracted.phone):
        info = LeadCustomerInfo(name=extracted.name, email=extracted.email, phone=extracted.phone)
        customer, is_new = get_or_create_customer(db, lead.business_id, info)
        if customer:
            lead.customer_id = customer.id
            customer_created = is_new

    return True, customer_created
