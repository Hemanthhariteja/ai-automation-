from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.factory import available_provider_names, get_provider
from app.ai.service import AIService
from app.auth.dependencies import get_current_business_id, get_owner_business_id
from app.database.session import get_db
from app.models.business import Business
from app.schemas.ai import (
    AISettingsUpdate,
    AIStatusResponse,
    AITestRequest,
    AITestResponse,
    ProviderStatus,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _get_business(db: Session, business_id: int) -> Business:
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


def _compute_status(db: Session, business: Business) -> AIStatusResponse:
    ai_service = AIService(db)
    chain = ai_service.resolve_provider_chain(business)
    active_primary = chain[0]
    active_fallback = chain[1] if len(chain) > 1 else chain[0]

    providers = []
    for name in available_provider_names():
        provider = get_provider(name)
        ok, message = provider.check_connection()
        providers.append(
            ProviderStatus(
                name=name,
                label=provider.label,
                connection_ok=ok,
                message=message,
                is_active_primary=(name == active_primary),
                is_active_fallback=(name == active_fallback),
            )
        )

    return AIStatusResponse(active_provider=active_primary, active_fallback=active_fallback, providers=providers)


@router.get("/status", response_model=AIStatusResponse)
def get_status(business_id: int = Depends(get_current_business_id), db: Session = Depends(get_db)):
    business = _get_business(db, business_id)
    return _compute_status(db, business)


@router.patch("/settings", response_model=AIStatusResponse)
def update_settings(
    payload: AISettingsUpdate,
    business_id: int = Depends(get_owner_business_id),
    db: Session = Depends(get_db),
):
    business = _get_business(db, business_id)
    valid_names = available_provider_names()

    if payload.ai_provider is not None:
        if payload.ai_provider not in valid_names:
            raise HTTPException(status_code=400, detail=f"Unknown provider '{payload.ai_provider}'")
        business.ai_provider = payload.ai_provider

    if payload.ai_fallback_provider is not None:
        if payload.ai_fallback_provider not in valid_names:
            raise HTTPException(status_code=400, detail=f"Unknown provider '{payload.ai_fallback_provider}'")
        business.ai_fallback_provider = payload.ai_fallback_provider

    db.commit()
    db.refresh(business)
    return _compute_status(db, business)


@router.post("/test", response_model=AITestResponse)
def test_pipeline(
    payload: AITestRequest,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    """Runs one piece of text through the full AI pipeline (classify, extract,
    score, generate) so the provider abstraction and fallback chain can be
    demonstrated end-to-end without needing a real lead."""
    business = _get_business(db, business_id)
    ai_service = AIService(db)

    classification, provider_used, fallback_used, fallback_reason = ai_service.classify_intent(
        business, payload.text
    )
    extracted, _, _, _ = ai_service.extract_information(business, payload.text)
    score_result, _, _, _ = ai_service.score_lead(business, classification, extracted, payload.text)

    business_profile = {
        "name": business.name,
        "description": business.description,
        "services": business.services,
        "hours": business.hours,
        "contact_email": business.contact_email,
        "contact_phone": business.contact_phone,
        "tone": business.tone,
    }
    generated, _, _, _ = ai_service.generate_response(business, business_profile, payload.text, extracted)

    return AITestResponse(
        intent=classification.intent,
        category=classification.category,
        confidence=classification.confidence,
        extracted=extracted.to_dict(),
        score=score_result.score,
        score_breakdown=score_result.breakdown,
        response_text=generated.text,
        provider_used=provider_used,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
    )
