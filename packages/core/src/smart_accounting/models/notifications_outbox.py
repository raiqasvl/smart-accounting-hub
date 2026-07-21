# notifications_outbox — table-backed outbox (FinWave pattern). Schema lands now; drainer is v1.1.
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .fields import bigserial_pk


class NotificationOutbox(Base):
    __tablename__ = "notifications_outbox"
    __table_args__ = (
        Index(
            "ix_notifications_outbox_undelivered",
            "created_at",
            postgresql_where=text("delivered_at IS NULL"),
        ),
    )

    id: Mapped[bigserial_pk]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id"))
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
