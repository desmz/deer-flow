# [DL-NOTE] Only base + memory are top-level imports. db and jsonl are lazily imported inside
# make_run_event_store() so SQLAlchemy and aiosqlite are never loaded on test-only paths.
from deerflow.runtime.events.store.base import RunEventStore
from deerflow.runtime.events.store.memory import MemoryRunEventStore


def make_run_event_store(config=None) -> RunEventStore:
    """Create a RunEventStore based on run_events.backend configuration."""
    if config is None or config.backend == "memory":
        return MemoryRunEventStore()
    if config.backend == "db":
        from deerflow.persistence.engine import get_session_factory

        sf = get_session_factory()
        if sf is None:
            # [DL-INSIGHT] Graceful degradation: run_events.backend=db but database.backend=memory
            # (no engine created) — silently falls back to memory rather than crashing at startup.
            # database.backend=memory but run_events.backend=db -> fallback
            return MemoryRunEventStore()
        from deerflow.runtime.events.store.db import DbRunEventStore

        return DbRunEventStore(sf, max_trace_content=config.max_trace_content)
    if config.backend == "jsonl":
        from deerflow.runtime.events.store.jsonl import JsonlRunEventStore

        return JsonlRunEventStore()
    raise ValueError(f"Unknown run_events backend: {config.backend!r}")


# [DL-NOTE] DbRunEventStore and JsonlRunEventStore are intentionally absent from __all__ —
# callers should depend on the RunEventStore interface, not the concrete implementations.
__all__ = ["MemoryRunEventStore", "RunEventStore", "make_run_event_store"]
