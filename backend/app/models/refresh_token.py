from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.utils.time import utcnow


class RefreshToken(Base):
    """Stores only a hash of the token, never the raw value — same
    reasoning as password hashing: if the DB leaks, the tokens themselves
    shouldn't be recoverable. Revocation (`revoked_at`) is what makes
    logout actually invalidate a session, since a short-lived access JWT
    is stateless and can't be revoked on its own."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
