from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.ai.service import AllProvidersFailedError
from app.auth.dependencies import get_current_business_id
from app.database.session import get_db
from app.models.business import Business
from app.models.lead import Lead
from app.schemas.conversation import ConversationResponse, GenerateResponseResult, SummarizeResult
from app.schemas.lead import LeadCreate, LeadImportSummary, LeadListResponse, LeadResponse, LeadUpdate
from app.services.conversation_service import get_or_create_conversation_for_lead
from app.services.customer_service import get_or_create_customer
from app.services.lead_ai import run_ai_pipeline_on_lead
from app.services.lead_export import export_customers_to_csv, export_leads_to_csv
from app.services.lead_import import ImportFormatError, ImportTooLargeError, import_leads_from_csv
from app.services.response_service import generate_ai_response_for_lead, summarize_conversation
from app.services.workflow_trigger import trigger_workflows

router = APIRouter(prefix="/api/leads", tags=["leads"])


def _get_owned_lead(db: Session, business_id: int, lead_id: int) -> Lead:
    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id, Lead.business_id == business_id)
        .first()
    )
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


def _get_business(db: Session, business_id: int) -> Business:
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    business = _get_business(db, business_id)
    customer, customer_is_new = get_or_create_customer(db, business_id, payload.customer)

    lead = Lead(
        business_id=business_id,
        customer_id=customer.id if customer else None,
        raw_message=payload.raw_message,
        source=payload.source,
    )
    db.add(lead)
    db.flush()  # assign lead.id so AI calls can be attributed to it in ai_logs

    _, extraction_created_customer = run_ai_pipeline_on_lead(db, business, lead)
    customer_is_new = customer_is_new or extraction_created_customer

    trigger_workflows(db, business, lead, "new_enquiry")
    if customer_is_new:
        trigger_workflows(db, business, lead, "new_customer")

    db.commit()
    db.refresh(lead)
    return lead


IMPORT_TEMPLATE_CSV = "message,name,email,phone\n" '"I need a quote for a website, budget $2000",Jane Doe,jane@example.com,555-1234\n'


@router.get("/import/template")
def download_import_template():
    return PlainTextResponse(
        content=IMPORT_TEMPLATE_CSV,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_import_template.csv"},
    )


@router.post("/import", response_model=LeadImportSummary)
def import_leads(
    file: UploadFile = File(...),
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    """Bulk-creates leads from a CSV (e.g. exported from a spreadsheet).
    Each row runs through the same AI pipeline and workflow triggers as a
    normal enquiry. Row-level failures (missing message) are skipped and
    reported rather than failing the whole import."""
    business = _get_business(db, business_id)
    raw_bytes = file.file.read()

    try:
        return import_leads_from_csv(db, business, raw_bytes)
    except ImportTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ImportFormatError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/export")
def export_leads(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, max_length=200),
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    """CSV export of leads, honoring the same filters as GET /api/leads
    (unlike the list endpoint, not paginated — every matching row is included)."""
    csv_text = export_leads_to_csv(db, business_id, status_filter, priority, search)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"},
    )


@router.get("/export/customers")
def export_customers(
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    """CSV export of every customer record for the business."""
    csv_text = export_customers_to_csv(db, business_id)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers_export.csv"},
    )


@router.post("/{lead_id}/classify", response_model=LeadResponse)
def classify_lead(
    lead_id: int,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    """Re-runs AI classification/extraction/scoring on a lead's current
    raw_message — useful after editing the message, or for leads created
    without one having a message added later."""
    lead = _get_owned_lead(db, business_id, lead_id)
    if not lead.raw_message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead has no message to classify")

    business = _get_business(db, business_id)
    ran, _ = run_ai_pipeline_on_lead(db, business, lead)
    if not ran:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI classification failed on every configured provider, including Demo Mode",
        )

    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}/conversation", response_model=ConversationResponse)
def get_lead_conversation(
    lead_id: int,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    lead = _get_owned_lead(db, business_id, lead_id)
    conversation = get_or_create_conversation_for_lead(db, lead)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/{lead_id}/generate-response", response_model=GenerateResponseResult)
def generate_response(
    lead_id: int,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    """Drafts an AI reply grounded only in the business profile the owner
    configured (name, description, services, hours, contact, tone) — never
    invents prices, policies, or promises. Persists the reply as a message
    in the lead's conversation thread."""
    lead = _get_owned_lead(db, business_id, lead_id)
    if not lead.raw_message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead has no message to respond to")

    business = _get_business(db, business_id)
    try:
        conversation, message, provider_used, fallback_used, fallback_reason = generate_ai_response_for_lead(
            db, business, lead
        )
    except AllProvidersFailedError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI response generation failed on every configured provider, including Demo Mode",
        )

    db.commit()
    db.refresh(message)
    return GenerateResponseResult(
        conversation_id=conversation.id,
        message=message,
        provider_used=provider_used,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
    )


@router.post("/{lead_id}/summarize", response_model=SummarizeResult)
def summarize_lead_conversation(
    lead_id: int,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    lead = _get_owned_lead(db, business_id, lead_id)
    business = _get_business(db, business_id)
    try:
        conversation, provider_used, fallback_used, fallback_reason = summarize_conversation(db, business, lead)
    except AllProvidersFailedError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI summarization failed on every configured provider, including Demo Mode",
        )

    db.commit()
    return SummarizeResult(
        conversation_id=conversation.id,
        summary=conversation.summary,
        provider_used=provider_used,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
    )


@router.get("", response_model=LeadListResponse)
def list_leads(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, max_length=200),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    query = db.query(Lead).filter(Lead.business_id == business_id)

    if status_filter:
        query = query.filter(Lead.status == status_filter)
    if priority:
        query = query.filter(Lead.priority == priority)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Lead.raw_message.ilike(like), Lead.intent.ilike(like)))

    total = query.count()
    items = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()
    return LeadListResponse(total=total, items=items)


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    return _get_owned_lead(db, business_id, lead_id)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    lead = _get_owned_lead(db, business_id, lead_id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    lead = _get_owned_lead(db, business_id, lead_id)
    db.delete(lead)
    db.commit()
