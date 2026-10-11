import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["open", "done", "cancelled"]


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: Optional[int]
    title: str
    description: Optional[str]
    due_date: Optional[datetime.datetime]
    status: str
    created_at: datetime.datetime


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = None
    due_date: Optional[datetime.datetime] = None
    status: Optional[TaskStatus] = None


class TaskListResponse(BaseModel):
    total: int
    items: list[TaskResponse]
