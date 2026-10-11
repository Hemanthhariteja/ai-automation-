from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin
from app.utils.time import utcnow


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    trigger_type: Mapped[str] = mapped_column(String(50), default="new_enquiry")
    # new_enquiry | new_customer | manual | scheduled
    is_active: Mapped[bool] = mapped_column(default=True)

    business: Mapped["Business"] = relationship(back_populates="workflows")
    nodes: Mapped[list["WorkflowNode"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowNode.order_index"
    )
    executions: Mapped[list["WorkflowExecution"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )


class WorkflowNode(Base):
    """One node in the visual workflow builder graph."""

    __tablename__ = "workflow_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), nullable=False)

    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # trigger | ai_processor | condition | action | notification | db | end
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    position_x: Mapped[float] = mapped_column(Float, default=0)
    position_y: Mapped[float] = mapped_column(Float, default=0)

    workflow: Mapped["Workflow"] = relationship(back_populates="nodes")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leads.id"), default=None)

    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | running | success | failed
    log: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, default=None)

    workflow: Mapped["Workflow"] = relationship(back_populates="executions")
    lead: Mapped[Optional["Lead"]] = relationship(back_populates="workflow_executions")
