from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_business_id
from app.database.session import get_db
from app.models.task import Task
from app.schemas.task import TaskListResponse, TaskResponse, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _get_owned_task(db: Session, business_id: int, task_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id, Task.business_id == business_id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    query = db.query(Task).filter(Task.business_id == business_id)
    if status_filter:
        query = query.filter(Task.status == status_filter)

    total = query.count()
    items = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    return TaskListResponse(total=total, items=items)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    business_id: int = Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(db, business_id, task_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task
