import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_business_id
from app.database.session import get_db
from app.models.lead import Lead
from app.models.notification import Notification
from app.models.task import Task
from app.schemas.dashboard import DashboardSummary
from app.utils.time import utcnow

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(business_id: int = Depends(get_current_business_id), db: Session = Depends(get_db)):
    leads_query = db.query(Lead).filter(Lead.business_id == business_id)
    week_ago = utcnow().replace(tzinfo=None) - datetime.timedelta(days=7)

    total_leads = leads_query.count()
    new_leads = leads_query.filter(Lead.status == "new").count()
    high_priority_leads = leads_query.filter(Lead.priority == "high").count()
    leads_last_7_days = leads_query.filter(Lead.created_at >= week_ago).count()

    unread_notifications = (
        db.query(Notification)
        .filter(Notification.business_id == business_id, Notification.is_read.is_(False))
        .count()
    )
    open_tasks = db.query(Task).filter(Task.business_id == business_id, Task.status == "open").count()

    recent_leads = leads_query.order_by(Lead.created_at.desc()).limit(5).all()
    recent_notifications = (
        db.query(Notification)
        .filter(Notification.business_id == business_id)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )
    recent_tasks = (
        db.query(Task)
        .filter(Task.business_id == business_id, Task.status == "open")
        .order_by(Task.created_at.desc())
        .limit(5)
        .all()
    )

    return DashboardSummary(
        total_leads=total_leads,
        new_leads=new_leads,
        high_priority_leads=high_priority_leads,
        leads_last_7_days=leads_last_7_days,
        unread_notifications=unread_notifications,
        open_tasks=open_tasks,
        recent_leads=recent_leads,
        recent_notifications=recent_notifications,
        recent_tasks=recent_tasks,
    )
