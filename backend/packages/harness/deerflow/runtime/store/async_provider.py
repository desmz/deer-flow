"""Async Store factory — backend mirrors the configured checkpointer.

The store and checkpointer share the same ``checkpointer`` section in
*config.yaml* so they always use the same persistence backend:

- ``type: memory``   → :class:`langgraph.store.memory.InMemoryStore`
- ``type: sqlite``   → :class:`langgraph.store.sqlite.aio.AsyncSqliteStore`
- ``type: postgres`` → :class:`langgraph.store.postgres.aio.AsyncPostgresStore`

Usage (e.g. FastAPI lifespan)::

    from deerflow.runtime.store import make_store

    async with make_store() as store:
        app.state.store = store
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator

from langgraph.store.base import BaseStore

from deerflow.config.app_config import AppConfig, get_app_config
# [DL-NOTE] Imports sqlite utils from store.provider (not _sqlite_utils directly), making
# async_provider an indirect dependent of provider. Compare: checkpointer/async_provider.py
# imports from _sqlite_utils directly — the two packages are inconsistent here.
from deerflow.runtime.store.provider import POSTGRES_CONN_REQUIRED, POSTGRES_STORE_INSTALL, SQLITE_STORE_INSTALL, ensure_sqlite_parent_dir, resolve_sqlite_conn_str

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal backend factory
# ---------------------------------------------------------------------------


@contextlib.asynccontextmanager
async def _async_store(config) -> AsyncIterator[BaseStore]:
    """Async context manager that constructs and tears down a Store.

    The ``config`` argument is a :class:`deerflow.config.checkpointer_config.CheckpointerConfig`
    instance — the same object used by the checkpointer factory.
    """
    if config.type == "memory":
        from langgraph.store.memory import InMemoryStore

        logger.info("Store: using InMemoryStore (in-process, not persistent)")
        yield InMemoryStore()
        return

    if config.type == "sqlite":
        try:
            from langgraph.store.sqlite.aio import AsyncSqliteStore
        except ImportError as exc:
            raise ImportError(SQLITE_STORE_INSTALL) from exc

        conn_str = resolve_sqlite_conn_str(config.connection_string or "store.db")
        # [DL-WARN] Blocking call on the event loop — should use asyncio.to_thread like
        # checkpointer/async_provider._async_checkpointer does for the same operation.
        ensure_sqlite_parent_dir(conn_str)

        async with AsyncSqliteStore.from_conn_string(conn_str) as store:
            await store.setup()
            logger.info("Store: using AsyncSqliteStore (%s)", conn_str)
            yield store
        return

    if config.type == "postgres":
        try:
            from langgraph.store.postgres.aio import AsyncPostgresStore  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(POSTGRES_STORE_INSTALL) from exc

        if not config.connection_string:
            raise ValueError(POSTGRES_CONN_REQUIRED)

        # [DL-INSIGHT] Store manages its own pool via from_conn_string — unlike the checkpointer
        # which requires a manually configured AsyncConnectionPool(autocommit=True, prepare_threshold=0).
        # AsyncPostgresStore encapsulates those requirements internally.
        async with AsyncPostgresStore.from_conn_string(config.connection_string) as store:
            await store.setup()
            logger.info("Store: using AsyncPostgresStore")
            yield store
        return

    raise ValueError(f"Unknown store backend type: {config.type!r}")


# ---------------------------------------------------------------------------
# Public async context manager
# ---------------------------------------------------------------------------


@contextlib.asynccontextmanager
async def make_store(app_config: AppConfig | None = None) -> AsyncIterator[BaseStore]:
    """Async context manager that yields a Store whose backend matches the
    configured checkpointer.

    Reads from the same ``checkpointer`` section of *config.yaml* used by
    :func:`deerflow.runtime.checkpointer.async_provider.make_checkpointer` so
    that both singletons always use the same persistence technology::

        async with make_store(app_config) as store:
            app.state.store = store

    Yields an :class:`~langgraph.store.memory.InMemoryStore` when no
    ``checkpointer`` section is configured (emits a WARNING in that case).
    """
    if app_config is None:
        app_config = get_app_config()

    # [DL-QUESTION] make_store() only reads app_config.checkpointer — no support for the
    # unified database: config section that make_checkpointer() supports. If a deployment
    # uses only database: (not checkpointer:), the store always falls back to InMemoryStore.
    if app_config.checkpointer is None:
        from langgraph.store.memory import InMemoryStore

        logger.warning("No 'checkpointer' section in config.yaml — using InMemoryStore for the store. Thread list will be lost on server restart. Configure a sqlite or postgres backend for persistence.")
        yield InMemoryStore()
        return

    async with _async_store(app_config.checkpointer) as store:
        yield store
