from app.schemas.lead import LeadResponse
from app.schemas.notification import NotificationResponse
from app.schemas.task import TaskResponse
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_leads: int
    new_leads: int
    high_priority_leads: int
    leads_last_7_days: int
    unread_notifications: int
    open_tasks: int
    recent_leads: list[LeadResponse]
    recent_notifications: list[NotificationResponse]
    recent_tasks: list[TaskResponse]
