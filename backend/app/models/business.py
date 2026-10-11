from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin


class Business(Base, TimestampMixin):
    """A single small business profile. AI response generation is grounded
    only in these fields — never in invented prices, policies, or promises."""

    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Public, URL-safe identifier for the unauthenticated enquiry form
    # (/enquiry/<slug>) — safe to share publicly, unlike the numeric id
    # which isn't secret either but a slug reads better in a shared link.
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    services: Mapped[Optional[str]] = mapped_column(Text, default=None)
    hours: Mapped[Optional[str]] = mapped_column(String(300), default=None)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    tone: Mapped[str] = mapped_column(String(50), default="professional")

    # Runtime-swappable AI provider selection. Null = fall back to the
    # server-wide default in app/config.py (env-configured). Actual API keys
    # always stay in .env — only the *choice* of provider lives here, so the
    # settings page can flip providers without touching secrets or code.
    ai_provider: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    ai_fallback_provider: Mapped[Optional[str]] = mapped_column(String(30), default=None)

    # Which Meta Page's messages route to this business — set once in the
    # Messenger channel settings. Null = this business hasn't connected a
    # Page, so the real webhook has nothing to match it against (the rest of
    # the app is entirely unaffected either way).
    messenger_page_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, default=None)

    users: Mapped[list["User"]] = relationship(back_populates="business")
    customers: Mapped[list["Customer"]] = relationship(back_populates="business")
    leads: Mapped[list["Lead"]] = relationship(back_populates="business")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="business")
    workflows: Mapped[list["Workflow"]] = relationship(back_populates="business")
    tasks: Mapped[list["Task"]] = relationship(back_populates="business")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="business")
    ai_logs: Mapped[list["AILog"]] = relationship(back_populates="business")
