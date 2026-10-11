import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    message: str
    is_read: bool
    created_at: datetime.datetime


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    items: list[NotificationResponse]
