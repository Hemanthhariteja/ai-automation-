import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

LeadStatus = Literal["new", "contacted", "qualified", "won", "lost"]
LeadPriority = Literal["low", "normal", "high"]


class LeadCustomerInfo(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)


class LeadCreate(BaseModel):
    raw_message: Optional[str] = Field(default=None, max_length=4000)
    source: str = Field(default="manual", max_length=50)
    customer: Optional[LeadCustomerInfo] = None


class LeadUpdate(BaseModel):
    raw_message: Optional[str] = Field(default=None, max_length=4000)
    status: Optional[LeadStatus] = None
    priority: Optional[LeadPriority] = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    customer_id: Optional[int]
    customer: Optional[CustomerResponse] = None

    source: str
    raw_message: Optional[str]

    intent: Optional[str]
    category: Optional[str]
    confidence: Optional[float]
    extracted_data: Optional[dict]
    score: Optional[int]
    score_breakdown: Optional[dict]

    status: str
    priority: str
    tracking_data: Optional[dict]

    created_at: datetime.datetime
    updated_at: datetime.datetime


class LeadListResponse(BaseModel):
    total: int
    items: list[LeadResponse]


class LeadImportRowError(BaseModel):
    row: int
    reason: str


class LeadImportSummary(BaseModel):
    total_rows: int
    imported: int
    skipped: int
    errors: list[LeadImportRowError]
