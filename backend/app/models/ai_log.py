from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.time import utcnow


class AILog(Base):
    """Audit trail for every AI provider call — which provider actually
    served the request, whether it fell back, and how long it took."""

    __tablename__ = "ai_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leads.id"), default=None)

    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    # classify | extract | score | generate_response | summarize | assistant_query
    requested_provider: Mapped[str] = mapped_column(String(30), nullable=False)
    actual_provider: Mapped[str] = mapped_column(String(30), nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_reason: Mapped[Optional[str]] = mapped_column(String(300), default=None)

    input_snippet: Mapped[Optional[str]] = mapped_column(Text, default=None)
    output: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, default=None)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    business: Mapped["Business"] = relationship(back_populates="ai_logs")
