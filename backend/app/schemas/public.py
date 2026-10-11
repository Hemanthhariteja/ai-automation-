from typing import Optional

from pydantic import BaseModel, Field


class PublicBusinessInfo(BaseModel):
    name: str
    description: Optional[str]
    services: Optional[str]
    hours: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]


class TrackingData(BaseModel):
    """Ad/campaign attribution read from the enquiry page's own URL at the
    moment the visitor landed on it — the standard way marketing forms
    capture which ad or campaign actually drove a lead."""

    utm_source: Optional[str] = Field(default=None, max_length=200)
    utm_medium: Optional[str] = Field(default=None, max_length=200)
    utm_campaign: Optional[str] = Field(default=None, max_length=200)
    utm_term: Optional[str] = Field(default=None, max_length=200)
    utm_content: Optional[str] = Field(default=None, max_length=200)
    gclid: Optional[str] = Field(default=None, max_length=300)  # Google Ads click id
    fbclid: Optional[str] = Field(default=None, max_length=300)  # Meta Ads click id
    referrer: Optional[str] = Field(default=None, max_length=500)
    landing_page: Optional[str] = Field(default=None, max_length=500)


class PublicLeadCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    name: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    tracking: Optional[TrackingData] = None


class PublicLeadCreateResponse(BaseModel):
    received: bool = True
