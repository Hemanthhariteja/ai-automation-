from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_business_id
from app.database.session import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationListResponse, NotificationResponse, NotificationUpdate

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.business_id == business_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    total = query.count()
    unread_count = (
        db.query(Notification)
        .filter(Notification.business_id == business_id, Notification.is_read.is_(False))
        .count()
    )
    items = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    return NotificationListResponse(total=total, unread_count=unread_count, items=items)


@router.patch("/{notification_id}", response_model=NotificationResponse)
def update_notification(
    notification_id: int,
    payload: NotificationUpdate,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.business_id == business_id)
        .first()
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(notification, field, value)

    db.commit()
    db.refresh(notification)
    return notification
