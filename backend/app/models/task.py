from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leads.id"), default=None)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    due_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, default=None)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | done | cancelled

    business: Mapped["Business"] = relationship(back_populates="tasks")
    lead: Mapped[Optional["Lead"]] = relationship(back_populates="tasks")
