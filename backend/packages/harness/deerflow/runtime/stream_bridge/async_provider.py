"""Async stream bridge factory.

Provides an **async context manager** aligned with
:func:`deerflow.runtime.checkpointer.async_provider.make_checkpointer`.

Usage (e.g. FastAPI lifespan)::

    from deerflow.agents.stream_bridge import make_stream_bridge

    async with make_stream_bridge() as bridge:
        app.state.stream_bridge = bridge
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator

from deerflow.config.app_config import AppConfig
from deerflow.config.stream_bridge_config import get_stream_bridge_config

from .base import StreamBridge

logger = logging.getLogger(__name__)


# [DL-INSIGHT] Same lifespan pattern as make_checkpointer: async CM owns the bridge for the full app lifetime (stored on app.state in deps.py)
# [DL-WARN] Module docstring example uses stale path "deerflow.agents.stream_bridge" — correct import is "deerflow.runtime.stream_bridge"
@contextlib.asynccontextmanager
async def make_stream_bridge(app_config: AppConfig | None = None) -> AsyncIterator[StreamBridge]:
    """Async context manager that yields a :class:`StreamBridge`.

    Falls back to :class:`MemoryStreamBridge` when no configuration is
    provided and nothing is set globally.
    """
    # [DL-NOTE] Dual config sources: explicit AppConfig at Gateway startup; global singleton for tests calling make_stream_bridge() with no args
    if app_config is None:
        config = get_stream_bridge_config()
    else:
        config = app_config.stream_bridge

    # [DL-NOTE] None (no stream_bridge section in config.yaml) collapses to "memory" with default maxsize — in-process, zero external deps
    if config is None or config.type == "memory":
        # [DL-NOTE] Lazy import: deferred to avoid circular dependency between stream_bridge submodules at module load time
        from deerflow.runtime.stream_bridge.memory import MemoryStreamBridge

        maxsize = config.queue_maxsize if config is not None else 256
        bridge = MemoryStreamBridge(queue_maxsize=maxsize)
        logger.info("Stream bridge initialised: memory (queue_maxsize=%d)", maxsize)
        try:
            yield bridge
        finally:
            await bridge.close()
        return

    if config.type == "redis":
        # [DL-NOTE] Redis would enable multi-process Gateway: MemoryStreamBridge can't cross OS process boundaries in a multi-worker deploy
        raise NotImplementedError("Redis stream bridge planned for Phase 2")

    raise ValueError(f"Unknown stream bridge type: {config.type!r}")
