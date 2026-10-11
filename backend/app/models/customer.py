from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False)

    name: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    email: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    phone: Mapped[Optional[str]] = mapped_column(String(50), default=None)

    business: Mapped["Business"] = relationship(back_populates="customers")
    leads: Mapped[list["Lead"]] = relationship(back_populates="customer")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="customer")
