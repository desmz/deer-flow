"""ORM model for user feedback on runs."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from deerflow.persistence.base import Base


class FeedbackRow(Base):
    __tablename__ = "feedback"

    # [DL-INSIGHT] Natural unique key (thread,run,user) enforces "one rating per user per run" at the DB
    # level — it's the backstop that makes upsert() correct: sql.py selects on this exact triple, and
    # this constraint turns a concurrent double-upsert (both see no row, both insert) into an
    # IntegrityError instead of two duplicate rows.
    __table_args__ = (UniqueConstraint("thread_id", "run_id", "user_id", name="uq_feedback_thread_run_user"),)

    # [DL-INSIGHT] Surrogate PK: feedback_id is a server-minted uuid4 (sql.py), unlike run_id/thread_id
    # which are externally issued. Classic dual-key design — surrogate for stable identity (get/delete by
    # feedback_id), natural unique key above for the business rule (upsert by thread+run+user).
    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    message_id: Mapped[str | None] = mapped_column(String(64))
    # message_id is an optional RunEventStore event identifier —
    # allows feedback to target a specific message or the entire run

    # [DL-WARN] The +1/-1 invariant lives ONLY in Python (sql.py raises ValueError); there is no DB CHECK.
    # A direct DB/migration write of e.g. rating=5 would persist, and aggregate_by_run's case() counts it
    # as neither positive nor negative — silently skewing totals (sum != positive+negative).
    rating: Mapped[int] = mapped_column(nullable=False)
    # +1 (thumbs-up) or -1 (thumbs-down)

    comment: Mapped[str | None] = mapped_column(Text)
    # Optional text feedback from the user

    # [DL-NOTE] No updated_at here — but upsert() re-stamps created_at on every update (sql.py), so for
    # an edited rating this field is effectively "last modified", not "first created".
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
