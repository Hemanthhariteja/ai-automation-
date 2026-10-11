from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), default=None)

    source: Mapped[str] = mapped_column(String(50), default="manual")  # manual | web_form | whatsapp_mock | scheduled
    raw_message: Mapped[Optional[str]] = mapped_column(Text, default=None)

    # AI classification (Phase 6)
    intent: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    category: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    confidence: Mapped[Optional[float]] = mapped_column(default=None)

    # AI extraction (Phase 6) — missing fields stay null, never invented
    extracted_data: Mapped[Optional[dict]] = mapped_column(JSON, default=None)

    # AI lead scoring (Phase 6) — 0-30 low / 31-70 medium / 71-100 high, not a validated statistical model
    score: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    score_breakdown: Mapped[Optional[dict]] = mapped_column(JSON, default=None)

    status: Mapped[str] = mapped_column(String(30), default="new")  # new | contacted | qualified | won | lost
    priority: Mapped[str] = mapped_column(String(20), default="normal")  # low | normal | high

    # Ad/campaign attribution, captured client-side from the public enquiry
    # page's own URL at submit time (utm_*, gclid, fbclid, referrer, landing
    # page) — never AI-derived, so it's kept separate from extracted_data.
    tracking_data: Mapped[Optional[dict]] = mapped_column(JSON, default=None)

    business: Mapped["Business"] = relationship(back_populates="leads")
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="leads")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="lead")
    tasks: Mapped[list["Task"]] = relationship(back_populates="lead")
    workflow_executions: Mapped[list["WorkflowExecution"]] = relationship(back_populates="lead")
