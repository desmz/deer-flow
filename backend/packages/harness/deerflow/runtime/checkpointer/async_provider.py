"""Async checkpointer factory.

Provides an **async context manager** for long-running async servers that need
proper resource cleanup.

Supported backends: memory, sqlite, postgres.

Usage (e.g. FastAPI lifespan)::

    from deerflow.runtime.checkpointer.async_provider import make_checkpointer

    async with make_checkpointer() as checkpointer:
        app.state.checkpointer = checkpointer  # InMemorySaver if not configured

For sync usage see :mod:`deerflow.runtime.checkpointer.provider`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator

from langgraph.types import Checkpointer

from deerflow.config.app_config import AppConfig, get_app_config
# [DL-NOTE] Imports error constants from provider.py rather than redefining them — ensures
# both sync and async paths emit identical actionable install instructions.
from deerflow.runtime.checkpointer.provider import (
    POSTGRES_CONN_REQUIRED,
    POSTGRES_INSTALL,
    SQLITE_INSTALL,
)
from deerflow.runtime.store._sqlite_utils import ensure_sqlite_parent_dir, resolve_sqlite_conn_str

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Async factory
# ---------------------------------------------------------------------------


@contextlib.asynccontextmanager
async def _async_checkpointer(config) -> AsyncIterator[Checkpointer]:
    """Async context manager that constructs and tears down a checkpointer."""
    if config.type == "memory":
        from langgraph.checkpoint.memory import InMemorySaver

        yield InMemorySaver()
        return

    if config.type == "sqlite":
        try:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        except ImportError as exc:
            raise ImportError(SQLITE_INSTALL) from exc

        conn_str = resolve_sqlite_conn_str(config.connection_string or "store.db")
        # [DL-NOTE] mkdir is a blocking filesystem call — offloaded to a thread to avoid
        # stalling the event loop. The sync provider calls it directly (acceptable there).
        await asyncio.to_thread(ensure_sqlite_parent_dir, conn_str)
        async with AsyncSqliteSaver.from_conn_string(conn_str) as saver:
            await saver.setup()
            yield saver
        return

    if config.type == "postgres":
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from psycopg_pool import AsyncConnectionPool
        except ImportError as exc:
            raise ImportError(POSTGRES_INSTALL) from exc

        if not config.connection_string:
            raise ValueError(POSTGRES_CONN_REQUIRED)

        # [DL-INSIGHT] autocommit=True required by LangGraph's Postgres checkpointer.
        # prepare_threshold=0 disables psycopg3 server-side statement caching — it conflicts
        # with autocommit mode and causes errors on repeated checkpointer calls.
        async with AsyncConnectionPool(
            conninfo=config.connection_string,
            max_size=20,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        ) as pool:
            saver = AsyncPostgresSaver(pool)
            await saver.setup()
            yield saver
        return

    raise ValueError(f"Unknown checkpointer type: {config.type!r}")


# ---------------------------------------------------------------------------
# Public async context manager
# ---------------------------------------------------------------------------


@contextlib.asynccontextmanager
async def _async_checkpointer_from_database(db_config) -> AsyncIterator[Checkpointer]:
    """Async context manager that constructs a checkpointer from unified DatabaseConfig."""
    if db_config.backend == "memory":
        from langgraph.checkpoint.memory import InMemorySaver

        yield InMemorySaver()
        return

    if db_config.backend == "sqlite":
        try:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        except ImportError as exc:
            raise ImportError(SQLITE_INSTALL) from exc

        conn_str = db_config.checkpointer_sqlite_path
        # [DL-WARN] Calls ensure_sqlite_parent_dir directly (blocking) rather than via
        # asyncio.to_thread — inconsistent with _async_checkpointer above.
        ensure_sqlite_parent_dir(conn_str)
        async with AsyncSqliteSaver.from_conn_string(conn_str) as saver:
            await saver.setup()
            yield saver
        return

    if db_config.backend == "postgres":
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from psycopg_pool import AsyncConnectionPool
        except ImportError as exc:
            raise ImportError(POSTGRES_INSTALL) from exc

        if not db_config.postgres_url:
            raise ValueError("database.postgres_url is required for the postgres backend")

        async with AsyncConnectionPool(
            conninfo=db_config.postgres_url,
            max_size=20,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        ) as pool:
            saver = AsyncPostgresSaver(pool)
            await saver.setup()
            yield saver
        return

    raise ValueError(f"Unknown database backend: {db_config.backend!r}")


@contextlib.asynccontextmanager
async def make_checkpointer(app_config: AppConfig | None = None) -> AsyncIterator[Checkpointer]:
    """Async context manager that yields a checkpointer for the caller's lifetime.
    Resources are opened on enter and closed on exit -- no global state::

        async with make_checkpointer(app_config) as checkpointer:
            app.state.checkpointer = checkpointer

    Yields an ``InMemorySaver`` when no checkpointer is configured in *config.yaml*.

    Priority:
    1. Legacy ``checkpointer:`` config section (backward compatible)
    2. Unified ``database:`` config section
    3. Default InMemorySaver
    """

    if app_config is None:
        app_config = get_app_config()

    # [DL-INSIGHT] Three-tier config priority: (1) legacy standalone checkpointer: section →
    # (2) unified database: section → (3) InMemorySaver default. The legacy path is kept so
    # existing config.yaml files with a checkpointer: block work unchanged.
    # Legacy: standalone checkpointer config takes precedence
    if app_config.checkpointer is not None:
        async with _async_checkpointer(app_config.checkpointer) as saver:
            yield saver
            return

    # Unified database config
    # [DL-NOTE] getattr guards against older AppConfig versions that lack the database field.
    # The != "memory" check skips the factory path when no real DB is configured — DatabaseConfig
    # always has a default backend="memory", so without this guard every unconfigured deployment
    # would take the database factory path and yield InMemorySaver redundantly.
    db_config = getattr(app_config, "database", None)
    if db_config is not None and db_config.backend != "memory":
        async with _async_checkpointer_from_database(db_config) as saver:
            yield saver
            return

    # Default: in-memory
    from langgraph.checkpoint.memory import InMemorySaver

    yield InMemorySaver()
