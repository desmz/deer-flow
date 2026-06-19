"""ORM model for run metadata."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from deerflow.persistence.base import Base


class RunRow(Base):
    __tablename__ = "runs"

    # [DL-INSIGHT] Natural PK again (externally-issued run_id), same pattern as thread_meta. thread_id
    # is the belongs-to FK-by-convention (nullable=False, indexed): every run has a parent thread.
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    assistant_id: Mapped[str | None] = mapped_column(String(128))
    # [DL-NOTE] Same nullable+indexed owner column as thread_meta/run_event; sql.py applies the
    # WHERE user_id == resolved owner filter on get/list/delete.
    user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # "pending" | "running" | "success" | "error" | "timeout" | "interrupted"

    model_name: Mapped[str | None] = mapped_column(String(128))
    # [DL-NOTE] LangGraph concurrency policy: what to do if a run is already active on the thread.
    multitask_strategy: Mapped[str] = mapped_column(String(20), default="reject")
    # [DL-NOTE] Two distinct JSON blobs: metadata_json = arbitrary tags; kwargs_json = run invocation
    # args. Both *_json to dodge the DeclarativeBase.metadata collision; remapped in sql.py _row_to_dict.
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    kwargs_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)

    # [DL-INSIGHT] Deliberate denormalization: these summary fields are copied OUT of run_events so the
    # run-listing page renders without querying RunEventStore per row. Trade write-time duplication for
    # read-time speed on the hot list path. Populated once via update_run_completion (truncated to 2000).
    # Convenience fields (for listing pages without querying RunEventStore)
    message_count: Mapped[int] = mapped_column(default=0)
    first_human_message: Mapped[str | None] = mapped_column(Text)
    last_ai_message: Mapped[str | None] = mapped_column(Text)

    # [DL-INSIGHT] Token rollups are write-once-on-completion, not incremental: RunJournal accumulates
    # in memory during the run and update_run_completion flushes the totals in one UPDATE. A run that
    # crashes mid-flight leaves these at 0 — the totals are a completion artifact, not live counters.
    # Token usage (accumulated in-memory by RunJournal, written on run completion)
    total_input_tokens: Mapped[int] = mapped_column(default=0)
    total_output_tokens: Mapped[int] = mapped_column(default=0)
    total_tokens: Mapped[int] = mapped_column(default=0)
    llm_call_count: Mapped[int] = mapped_column(default=0)
    lead_agent_tokens: Mapped[int] = mapped_column(default=0)
    subagent_tokens: Mapped[int] = mapped_column(default=0)
    middleware_tokens: Mapped[int] = mapped_column(default=0)

    # [DL-NOTE] Self-reference by convention, NOT a SQL ForeignKey — a plain String column pointing
    # at another runs.run_id. No DB-level cascade/integrity; the link is enforced (or not) in app code.
    # Follow-up association
    follow_up_to_run_id: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # [DL-INSIGHT] (thread_id, status) is tuned for aggregate_tokens_by_thread, the only query that
    # filters on BOTH columns (WHERE thread_id AND status IN ('success','error')). list_by_thread rides
    # the thread_id prefix; list_pending (status only, no thread_id) can't use it — leading column absent.
    __table_args__ = (Index("ix_runs_thread_status", "thread_id", "status"),)
