"""ORM model for thread metadata."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from deerflow.persistence.base import Base


class ThreadMetaRow(Base):
    __tablename__ = "threads_meta"

    # [DL-INSIGHT] Natural primary key — the LangGraph-issued thread_id IS the PK (no synthetic
    # autoincrement id). Contrast run_event, which is an append-only log keyed by (id, seq). This row
    # is a single mutable record per thread, so the externally-owned id maps cleanly to the PK.
    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assistant_id: Mapped[str | None] = mapped_column(String(128), index=True)
    # [DL-INSIGHT] Nullable user_id encodes "shared / pre-auth" ownership: sql.py check_access treats
    # row.user_id is None as accessible to everyone (the real orphan-tolerance path). index=True backs
    # the per-owner filter in search() (WHERE user_id == resolved). See thread_meta/sql.py.
    user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    display_name: Mapped[str | None] = mapped_column(String(256))
    # [DL-NOTE] status is filterable in search() (WHERE status == ...); "idle" is the post-create default.
    status: Mapped[str] = mapped_column(String(20), default="idle")
    # [DL-NOTE] Named metadata_json, NOT metadata — "metadata" is reserved on DeclarativeBase.
    # Same collision dodge as run_event's event_metadata; sql.py _row_to_dict remaps it to "metadata".
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    # [DL-NOTE] onupdate is a safety net: it auto-stamps updated_at on any UPDATE that omits the column.
    # sql.py also sets it explicitly in each .values(...), so onupdate only matters for paths that forget.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
