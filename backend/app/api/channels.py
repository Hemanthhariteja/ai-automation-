import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_business_id
from app.channels.base import ChannelError
from app.channels.messenger import MessengerChannel
from app.channels.mock import MockChannel
from app.config import get_settings
from app.database.session import get_db
from app.models.business import Business
from app.schemas.channels import ChannelsStatusResponse, ChannelStatus, SimulateMessengerMessage
from app.schemas.lead import LeadResponse
from app.services.channel_intake import ingest_channel_message
from app.utils.rate_limit import is_rate_limited

router = APIRouter(prefix="/api/channels", tags=["channels"])
settings = get_settings()
messenger_channel = MessengerChannel()
mock_channel = MockChannel()

WEBHOOK_RATE_LIMIT_MAX = 60
WEBHOOK_RATE_LIMIT_WINDOW_SECONDS = 60


def _get_business(db: Session, business_id: int) -> Business:
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


@router.get("/status", response_model=ChannelsStatusResponse)
def get_channels_status(business_id: int = Depends(get_current_business_id), db: Session = Depends(get_db)):
    business = _get_business(db, business_id)
    configured = bool(settings.facebook_verify_token and settings.facebook_page_access_token)
    return ChannelsStatusResponse(
        channels=[
            ChannelStatus(
                name="messenger",
                configured=configured,
                message=(
                    "Meta credentials configured" if configured else "FACEBOOK_VERIFY_TOKEN / FACEBOOK_PAGE_ACCESS_TOKEN not set"
                ),
                business_connected=business.messenger_page_id is not None,
            ),
            ChannelStatus(
                name="mock",
                configured=True,
                message="Always available — no setup needed. Use /simulate to demo the Messenger flow.",
                business_connected=True,
            ),
        ]
    )


@router.get("/messenger/webhook")
def verify_messenger_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Meta's one-time webhook verification handshake, run when you register
    the webhook URL in the Meta developer console."""
    if hub_mode == "subscribe" and settings.facebook_verify_token and hub_verify_token == settings.facebook_verify_token:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch")


@router.post("/messenger/webhook", status_code=status.HTTP_200_OK)
async def receive_messenger_webhook(request: Request, db: Session = Depends(get_db)):
    """The real inbound channel — Meta calls this directly, unauthenticated
    by necessity. Always acks with 200 (even when a message can't be
    matched to a business) to avoid Meta's retry storms on a delivery it
    considers failed; problems are logged server-side instead."""
    raw_body = await request.body()
    signature = request.headers.get("x-hub-signature-256")
    if not MessengerChannel.verify_signature(raw_body, signature, settings.facebook_app_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature")

    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(f"messenger_webhook:{client_ip}", WEBHOOK_RATE_LIMIT_MAX, WEBHOOK_RATE_LIMIT_WINDOW_SECONDS):
        return {"status": "rate_limited"}

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return {"status": "ignored", "reason": "invalid JSON"}

    page_id = MessengerChannel.page_id_from_payload(payload)
    business = db.query(Business).filter(Business.messenger_page_id == page_id).first() if page_id else None
    if business is None:
        return {"status": "ignored", "reason": "no business connected to this page"}

    try:
        messages = messenger_channel.parse_webhook_payload(payload)
    except ChannelError:
        return {"status": "ignored", "reason": "unrecognized payload shape"}

    for message in messages:
        ingest_channel_message(db, business, "messenger", message)

    return {"status": "ok", "leads_created": len(messages)}


@router.post("/messenger/simulate", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def simulate_messenger_message(
    payload: SimulateMessengerMessage,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    """Demos/tests the Messenger flow with zero real Meta setup — the same
    intake pipeline the real webhook uses, just fed by MockChannel instead."""
    business = _get_business(db, business_id)
    try:
        messages = mock_channel.parse_webhook_payload(payload.model_dump())
    except ChannelError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return ingest_channel_message(db, business, "messenger", messages[0])
