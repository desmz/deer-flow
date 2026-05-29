"""Abstract stream bridge protocol.

StreamBridge decouples agent workers (producers) from SSE endpoints
(consumers), aligning with LangGraph Platform's Queue + StreamManager
architecture.
"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


# [DL-INSIGHT] frozen=True: events are shared across producer and consumer coroutines — immutability removes any need for a mutex
@dataclass(frozen=True)
class StreamEvent:
    """Single stream event.

    Attributes:
        id: Monotonically increasing event ID (used as SSE ``id:`` field,
            supports ``Last-Event-ID`` reconnection).
        event: SSE event name, e.g. ``"metadata"``, ``"updates"``,
            ``"events"``, ``"error"``, ``"end"``.
        data: JSON-serialisable payload.
    """

    id: str
    event: str
    data: Any


# [DL-NOTE] Dunder names ("__heartbeat__", "__end__") prevent collision with real LangGraph event names like "metadata", "updates"
# [DL-NOTE] id="" on both: sentinels are intercepted by the SSE consumer before reaching the browser, so they never advance Last-Event-ID
HEARTBEAT_SENTINEL = StreamEvent(id="", event="__heartbeat__", data=None)
END_SENTINEL = StreamEvent(id="", event="__end__", data=None)


class StreamBridge(abc.ABC):
    """Abstract base for stream bridges."""

    @abc.abstractmethod
    async def publish(self, run_id: str, event: str, data: Any) -> None:
        """Enqueue a single event for *run_id* (producer side)."""

    # [DL-NOTE] Separate from publish() so implementations can close the underlying queue/channel, not just enqueue a named event
    @abc.abstractmethod
    async def publish_end(self, run_id: str) -> None:
        """Signal that no more events will be produced for *run_id*."""

    # [DL-INSIGHT] Regular def (not async def) lets implementations be async generators (yield) without forcing a coroutine wrapper
    @abc.abstractmethod
    def subscribe(
        self,
        run_id: str,
        *,
        last_event_id: str | None = None,
        heartbeat_interval: float = 15.0,
    ) -> AsyncIterator[StreamEvent]:
        """Async iterator that yields events for *run_id* (consumer side).

        Yields :data:`HEARTBEAT_SENTINEL` when no event arrives within
        *heartbeat_interval* seconds.  Yields :data:`END_SENTINEL` once
        the producer calls :meth:`publish_end`.
        """

    # [DL-WARN] delay > 0 is critical in production: producer calls cleanup() right after publish_end() while consumer may still drain
    @abc.abstractmethod
    async def cleanup(self, run_id: str, *, delay: float = 0) -> None:
        """Release resources associated with *run_id*.

        If *delay* > 0 the implementation should wait before releasing,
        giving late subscribers a chance to drain remaining events.
        """

    # [DL-NOTE] Default no-op keeps in-memory bridge trivial; Redis/DB backends override to release connections on shutdown
    async def close(self) -> None:
        """Release backend resources.  Default is a no-op."""
