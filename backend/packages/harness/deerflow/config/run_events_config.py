"""Run event storage configuration.

Controls where run events (messages + execution traces) are persisted.

Backends:
- memory: In-memory storage, data lost on restart. Suitable for
  development and testing.
- db: SQL database via SQLAlchemy ORM. Provides full query capability.
  Suitable for production deployments.
- jsonl: Append-only JSONL files. Lightweight alternative for
  single-node deployments that need persistence without a database.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# [DL-INSIGHT] Unlike CheckpointerConfig, this class has no module-level singleton —
# AppConfig holds it directly as `run_events: RunEventsConfig` with default_factory.
# The factory (make_run_event_store) reads this config once at Gateway startup via deps.py.
class RunEventsConfig(BaseModel):
    # [DL-NOTE] Default "memory" means no run history survives a restart. "db" requires
    # database.backend != "memory" (an ORM engine must exist); "jsonl" needs no DB at all.
    backend: Literal["memory", "db", "jsonl"] = Field(
        default="memory",
        description="Storage backend for run events. 'memory' for development (no persistence), 'db' for production (SQL queries), 'jsonl' for lightweight single-node persistence.",
    )
    # [DL-NOTE] max_trace_content is consumed only by DbRunEventStore — JSONL and memory
    # backends store traces without truncation (or don't persist them at all).
    max_trace_content: int = Field(
        default=10240,
        description="Maximum trace content size in bytes before truncation (db backend only).",
    )
    track_token_usage: bool = Field(
        default=True,
        description="Whether RunJournal should accumulate token counts to RunRow.",
    )
