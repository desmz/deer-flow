"""Abstract interface for run metadata storage.

RunManager depends on this interface. Implementations:
- MemoryRunStore: in-memory dict (development, tests)
- Future: RunRepository backed by SQLAlchemy ORM

All methods accept an optional user_id for user isolation.
When user_id is None, no user filtering is applied (single-user mode).
"""

from __future__ import annotations

import abc
from typing import Any


# [DL-INSIGHT] RunStore is separate from RunManager by design: RunManager holds live mutable state
# (asyncio.Task, asyncio.Event, abort flags) while RunStore persists only serializable metadata.
# This split lets the in-memory registry stay fast while persistence is optional and swappable.
class RunStore(abc.ABC):
    @abc.abstractmethod
    async def put(
        self,
        run_id: str,
        *,
        thread_id: str,
        assistant_id: str | None = None,
        user_id: str | None = None,
        model_name: str | None = None,
        # [DL-NOTE] `status` is a raw str here, not RunStatus enum — intentional decoupling so
        # the store layer has no dependency on runtime.runs.schemas.
        status: str = "pending",
        multitask_strategy: str = "reject",
        metadata: dict[str, Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        error: str | None = None,
        created_at: str | None = None,
    ) -> None:
        pass

    @abc.abstractmethod
    async def get(self, run_id: str) -> dict[str, Any] | None:
        pass

    @abc.abstractmethod
    async def list_by_thread(
        self,
        thread_id: str,
        *,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        pass

    @abc.abstractmethod
    async def update_status(
        self,
        run_id: str,
        status: str,
        *,
        error: str | None = None,
    ) -> None:
        pass

    @abc.abstractmethod
    async def delete(self, run_id: str) -> None:
        pass

    # [DL-INSIGHT] update_run_completion is the run's final write — called once by worker.py when a run ends.
    # Token accounting is split by caller (lead_agent / subagent / middleware) to enable per-caller analytics.
    # first_human_message / last_ai_message enable a thread "preview" in the UI without re-querying messages.
    @abc.abstractmethod
    async def update_run_completion(
        self,
        run_id: str,
        *,
        status: str,
        total_input_tokens: int = 0,
        total_output_tokens: int = 0,
        total_tokens: int = 0,
        llm_call_count: int = 0,
        lead_agent_tokens: int = 0,
        subagent_tokens: int = 0,
        middleware_tokens: int = 0,
        message_count: int = 0,
        last_ai_message: str | None = None,
        first_human_message: str | None = None,
        error: str | None = None,
    ) -> None:
        pass

    # [DL-NOTE] `before` is an ISO timestamp for crash-recovery: "give me all pending runs before time X."
    # Currently untriggered in production code — only exercised by tests. Crash-recovery path is not yet wired.
    @abc.abstractmethod
    async def list_pending(self, *, before: str | None = None) -> list[dict[str, Any]]:
        pass

    # [DL-NOTE] Powers GET /api/threads/{id}/token-usage. Breaks down by model and by caller (lead/subagent/middleware).
    @abc.abstractmethod
    async def aggregate_tokens_by_thread(self, thread_id: str) -> dict[str, Any]:
        """Aggregate token usage for completed runs in a thread.

        Returns a dict with keys: total_tokens, total_input_tokens,
        total_output_tokens, total_runs, by_model (model_name → {tokens, runs}),
        by_caller ({lead_agent, subagent, middleware}).
        """
        pass
