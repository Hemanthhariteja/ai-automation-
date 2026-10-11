from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), default=None)
    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leads.id"), default=None)

    channel: Mapped[str] = mapped_column(String(50), default="web")  # web | whatsapp_mock | email
    summary: Mapped[Optional[str]] = mapped_column(Text, default=None)  # AI summarization (Phase 6/7)

    business: Mapped["Business"] = relationship(back_populates="conversations")
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="conversations")
    lead: Mapped[Optional["Lead"]] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
