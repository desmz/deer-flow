"""ORM model for run events."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from deerflow.persistence.base import Base


class RunEventRow(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # Owner of the conversation this event belongs to. Nullable for data
    # created before auth was introduced; populated by auth middleware on
    # new writes and by the boot-time orphan migration on existing rows.
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # [DL-INSIGHT] category is the partition key that splits one physical table into two logical
    # stores: "message" = frontend display log, "trace"/"lifecycle" = debug/audit. db.py filters
    # on it (list_messages → category=="message") and truncates ONLY trace content. See events/store/base.py.
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    # "message" | "trace" | "lifecycle"
    content: Mapped[str] = mapped_column(Text, default="")
    # [DL-NOTE] Named event_metadata, NOT metadata — "metadata" is reserved on DeclarativeBase
    # (Base.metadata holds the table registry). db.py's _row_to_dict() remaps it back to "metadata".
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    # [DL-INSIGHT] seq is thread-scoped (not global, not run-scoped): the monotonic ordering key.
    # db.py assigns it as max(seq)+1 under a per-thread lock; the uq constraint below is the DB-level
    # backstop guaranteeing no two events in a thread collide even if two writers race.
    seq: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # [DL-INSIGHT] The three table_args mirror the three read paths in db.py exactly:
    # uq(thread,seq) backs seq assignment; ix(thread,cat,seq) serves list_messages (filter by
    # category, order by seq); ix(thread,run,seq) serves list_events / per-run message queries.
    # All three lead with thread_id because every query is thread-scoped first.
    __table_args__ = (
        UniqueConstraint("thread_id", "seq", name="uq_events_thread_seq"),
        Index("ix_events_thread_cat_seq", "thread_id", "category", "seq"),
        Index("ix_events_run", "thread_id", "run_id", "seq"),
    )
