from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BusinessProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    services: Optional[str] = Field(default=None, max_length=1000)
    hours: Optional[str] = Field(default=None, max_length=300)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    tone: Optional[str] = Field(default=None, max_length=50)
    messenger_page_id: Optional[str] = Field(default=None, max_length=100)


class BusinessProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str]
    services: Optional[str]
    hours: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    tone: str
    messenger_page_id: Optional[str]
