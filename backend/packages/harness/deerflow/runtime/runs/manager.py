"""In-memory run registry with optional persistent RunStore backing."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from deerflow.utils.time import now_iso as _now_iso

from .schemas import DisconnectMode, RunStatus

if TYPE_CHECKING:
    from deerflow.runtime.runs.store.base import RunStore

logger = logging.getLogger(__name__)


@dataclass
class RunRecord:
    """Mutable record for a single run."""

    run_id: str
    thread_id: str
    assistant_id: str | None
    status: RunStatus
    on_disconnect: DisconnectMode
    multitask_strategy: str = "reject"
    metadata: dict = field(default_factory=dict)
    kwargs: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    # [DL-NOTE] repr=False prevents asyncio.Task from appearing in log/debug output.
    task: asyncio.Task | None = field(default=None, repr=False)
    # [DL-NOTE] Per-record event: worker polls abort_event.is_set() between chunks;
    # abort_action ("interrupt" | "rollback") tells the worker what to do when it fires.
    abort_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    abort_action: str = "interrupt"
    error: str | None = None
    model_name: str | None = None


# [DL-INSIGHT] Two-tier design: RunRecord holds live, non-serialisable state (asyncio.Task, asyncio.Event)
# that exists only for the process lifetime; RunStore mirrors only serialisable fields for persistence.
class RunManager:
    """In-memory run registry with optional persistent RunStore backing.

    All mutations are protected by an asyncio lock. When a ``store`` is
    provided, serializable metadata is also persisted to the store so
    that run history survives process restarts.
    """

    def __init__(self, store: RunStore | None = None) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = asyncio.Lock()
        self._store = store

    # [DL-NOTE] All persistence is best-effort: store failures are logged but never propagated.
    # A DB hiccup must not crash a live run; the in-memory registry is the source of truth.
    async def _persist_to_store(self, record: RunRecord) -> None:
        """Best-effort persist run record to backing store."""
        if self._store is None:
            return
        try:
            await self._store.put(
                record.run_id,
                thread_id=record.thread_id,
                assistant_id=record.assistant_id,
                status=record.status.value,
                multitask_strategy=record.multitask_strategy,
                metadata=record.metadata or {},
                kwargs=record.kwargs or {},
                created_at=record.created_at,
                model_name=record.model_name,
            )
        except Exception:
            logger.warning("Failed to persist run %s to store", record.run_id, exc_info=True)

    async def update_run_completion(self, run_id: str, **kwargs) -> None:
        """Persist token usage and completion data to the backing store."""
        if self._store is not None:
            try:
                await self._store.update_run_completion(run_id, **kwargs)
            except Exception:
                logger.warning("Failed to persist run completion for %s", run_id, exc_info=True)

    async def create(
        self,
        thread_id: str,
        assistant_id: str | None = None,
        *,
        on_disconnect: DisconnectMode = DisconnectMode.cancel,
        metadata: dict | None = None,
        kwargs: dict | None = None,
        multitask_strategy: str = "reject",
    ) -> RunRecord:
        """Create a new pending run and register it."""
        run_id = str(uuid.uuid4())
        now = _now_iso()
        record = RunRecord(
            run_id=run_id,
            thread_id=thread_id,
            assistant_id=assistant_id,
            status=RunStatus.pending,
            on_disconnect=on_disconnect,
            multitask_strategy=multitask_strategy,
            metadata=metadata or {},
            kwargs=kwargs or {},
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._runs[run_id] = record
        await self._persist_to_store(record)
        logger.info("Run created: run_id=%s thread_id=%s", run_id, thread_id)
        return record

    # [DL-NOTE] Lock-free read: safe in asyncio (single event loop thread); no await between read and use.
    def get(self, run_id: str) -> RunRecord | None:
        """Return a run record by ID, or ``None``."""
        return self._runs.get(run_id)

    # [DL-WARN] Docstring says "newest first" but the list comprehension does not reverse.
    # Result is oldest-first (dict insertion order). Tests confirm oldest-first behaviour.
    async def list_by_thread(self, thread_id: str) -> list[RunRecord]:
        """Return all runs for a given thread, newest first."""
        async with self._lock:
            # Dict insertion order matches creation order, so reversing it gives
            # us deterministic newest-first results even when timestamps tie.
            return [r for r in self._runs.values() if r.thread_id == thread_id]

    async def set_status(self, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        """Transition a run to a new status."""
        async with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                logger.warning("set_status called for unknown run %s", run_id)
                return
            record.status = status
            record.updated_at = _now_iso()
            if error is not None:
                record.error = error
        # [DL-NOTE] Store write happens outside the lock to avoid holding it across IO.
        if self._store is not None:
            try:
                await self._store.update_status(run_id, status.value, error=error)
            except Exception:
                logger.warning("Failed to persist status update for run %s", run_id, exc_info=True)
        logger.info("Run %s -> %s", run_id, status.value)

    async def update_model_name(self, run_id: str, model_name: str | None) -> None:
        """Update the model name for a run."""
        async with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                logger.warning("update_model_name called for unknown run %s", run_id)
                return
            record.model_name = model_name
            record.updated_at = _now_iso()
        await self._persist_to_store(record)
        logger.info("Run %s model_name=%s", run_id, model_name)

    # [DL-INSIGHT] cancel() sets abort_event + cancels the asyncio.Task but does NOT write to the store.
    # The worker's CancelledError/finally path calls set_status(interrupted), which does the store write.
    async def cancel(self, run_id: str, *, action: str = "interrupt") -> bool:
        """Request cancellation of a run.

        Args:
            run_id: The run ID to cancel.
            action: "interrupt" keeps checkpoint, "rollback" reverts to pre-run state.

        Sets the abort event with the action reason and cancels the asyncio task.
        Returns ``True`` if the run was in-flight and cancellation was initiated.
        """
        async with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return False
            if record.status not in (RunStatus.pending, RunStatus.running):
                return False
            record.abort_action = action
            record.abort_event.set()
            if record.task is not None and not record.task.done():
                record.task.cancel()
            record.status = RunStatus.interrupted
            record.updated_at = _now_iso()
        logger.info("Run %s cancelled (action=%s)", run_id, action)
        return True

    # [DL-INSIGHT] create_or_reject holds the lock across the inflight-check AND the insert to eliminate
    # the TOCTOU race that two separate "check then create" calls would have under concurrent requests.
    async def create_or_reject(
        self,
        thread_id: str,
        assistant_id: str | None = None,
        *,
        on_disconnect: DisconnectMode = DisconnectMode.cancel,
        metadata: dict | None = None,
        kwargs: dict | None = None,
        multitask_strategy: str = "reject",
        model_name: str | None = None,
    ) -> RunRecord:
        """Atomically check for inflight runs and create a new one.

        For ``reject`` strategy, raises ``ConflictError`` if thread
        already has a pending/running run.  For ``interrupt``/``rollback``,
        cancels inflight runs before creating.

        This method holds the lock across both the check and the insert,
        eliminating the TOCTOU race in separate ``has_inflight`` + ``create``.
        """
        run_id = str(uuid.uuid4())
        now = _now_iso()

        _supported_strategies = ("reject", "interrupt", "rollback")

        async with self._lock:
            if multitask_strategy not in _supported_strategies:
                raise UnsupportedStrategyError(f"Multitask strategy '{multitask_strategy}' is not yet supported. Supported strategies: {', '.join(_supported_strategies)}")

            inflight = [r for r in self._runs.values() if r.thread_id == thread_id and r.status in (RunStatus.pending, RunStatus.running)]

            if multitask_strategy == "reject" and inflight:
                raise ConflictError(f"Thread {thread_id} already has an active run")

            if multitask_strategy in ("interrupt", "rollback") and inflight:
                for r in inflight:
                    r.abort_action = multitask_strategy
                    r.abort_event.set()
                    if r.task is not None and not r.task.done():
                        r.task.cancel()
                    r.status = RunStatus.interrupted
                    r.updated_at = now
                logger.info(
                    "Cancelled %d inflight run(s) on thread %s (strategy=%s)",
                    len(inflight),
                    thread_id,
                    multitask_strategy,
                )

            record = RunRecord(
                run_id=run_id,
                thread_id=thread_id,
                assistant_id=assistant_id,
                status=RunStatus.pending,
                on_disconnect=on_disconnect,
                multitask_strategy=multitask_strategy,
                metadata=metadata or {},
                kwargs=kwargs or {},
                created_at=now,
                updated_at=now,
                model_name=model_name,
            )
            self._runs[run_id] = record

        await self._persist_to_store(record)
        logger.info("Run created: run_id=%s thread_id=%s", run_id, thread_id)
        return record

    async def has_inflight(self, thread_id: str) -> bool:
        """Return ``True`` if *thread_id* has a pending or running run."""
        async with self._lock:
            return any(r.thread_id == thread_id and r.status in (RunStatus.pending, RunStatus.running) for r in self._runs.values())

    # [DL-NOTE] 300s default is intentionally longer than bridge.cleanup's 60s: clients may poll
    # run status via GET /runs/{id} after the SSE stream ends; the record must outlive the buffer.
    async def cleanup(self, run_id: str, *, delay: float = 300) -> None:
        """Remove a run record after an optional delay."""
        if delay > 0:
            await asyncio.sleep(delay)
        async with self._lock:
            self._runs.pop(run_id, None)
        logger.debug("Run record %s cleaned up", run_id)


class ConflictError(Exception):
    """Raised when multitask_strategy=reject and thread has inflight runs."""


class UnsupportedStrategyError(Exception):
    """Raised when a multitask_strategy value is not yet implemented."""
