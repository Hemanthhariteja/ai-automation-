from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.business import Business
from app.models.lead import Lead
from app.schemas.lead import LeadCustomerInfo
from app.schemas.public import PublicBusinessInfo, PublicLeadCreate, PublicLeadCreateResponse
from app.services.customer_service import get_or_create_customer
from app.services.lead_ai import run_ai_pipeline_on_lead
from app.services.workflow_trigger import trigger_workflows
from app.utils.rate_limit import is_rate_limited

router = APIRouter(prefix="/api/public", tags=["public"])

RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW_SECONDS = 600  # 10 minutes


def _get_business_by_slug(db: Session, slug: str) -> Business:
    business = db.query(Business).filter(Business.slug == slug).first()
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


@router.get("/{slug}/business", response_model=PublicBusinessInfo)
def get_public_business_info(slug: str, db: Session = Depends(get_db)):
    return _get_business_by_slug(db, slug)


@router.post("/{slug}/leads", response_model=PublicLeadCreateResponse, status_code=status.HTTP_201_CREATED)
def submit_public_enquiry(slug: str, payload: PublicLeadCreate, request: Request, db: Session = Depends(get_db)):
    """Unauthenticated by design — this is the actual customer-facing intake
    channel a business links from their own website. Deliberately returns no
    lead detail (id, AI score, classification) to the public caller; only the
    business owner sees that, via the normal authenticated lead endpoints."""
    business = _get_business_by_slug(db, slug)

    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(f"{business.id}:{client_ip}", RATE_LIMIT_MAX, RATE_LIMIT_WINDOW_SECONDS):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions — please try again later.",
        )

    customer_info = None
    if payload.name or payload.email or payload.phone:
        customer_info = LeadCustomerInfo(name=payload.name, email=payload.email, phone=payload.phone)
    customer, _ = get_or_create_customer(db, business.id, customer_info)

    # Client-supplied UTM/click-id/landing-page data (only the browser knows
    # the URL the visitor actually landed on) merged with server-observed
    # context (user agent — not trustworthy from the client).
    tracking_data = payload.tracking.model_dump(exclude_none=True) if payload.tracking else {}
    user_agent = request.headers.get("user-agent")
    if user_agent:
        tracking_data["user_agent"] = user_agent
    tracking_data = tracking_data or None

    lead = Lead(
        business_id=business.id,
        customer_id=customer.id if customer else None,
        raw_message=payload.message,
        source="web_form",
        tracking_data=tracking_data,
    )
    db.add(lead)
    db.flush()

    run_ai_pipeline_on_lead(db, business, lead)
    trigger_workflows(db, business, lead, "new_enquiry")

    db.commit()
    return PublicLeadCreateResponse()
