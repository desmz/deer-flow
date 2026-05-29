"""Shared SQLite connection utilities for store and checkpointer providers."""

from __future__ import annotations

import pathlib

from deerflow.config.paths import resolve_path


def resolve_sqlite_conn_str(raw: str) -> str:
    """Return a SQLite connection string ready for use with store/checkpointer backends.

    SQLite special strings (``":memory:"`` and ``file:`` URIs) are returned
    unchanged.  Plain filesystem paths — relative or absolute — are resolved
    to an absolute string via :func:`resolve_path`.
    """
    # [DL-NOTE] :memory: has no filesystem path; file: URIs (RFC 3986) are already absolute
    # — passing either through resolve_path would corrupt the connection string.
    if raw == ":memory:" or raw.startswith("file:"):
        return raw
    # [DL-INSIGHT] resolve_path anchors relative paths to the app base dir, not CWD.
    # A config value like ".deer-flow/checkpoints.db" resolves consistently regardless
    # of where the server process was started from.
    return str(resolve_path(raw))


def ensure_sqlite_parent_dir(conn_str: str) -> None:
    """Create parent directory for a SQLite filesystem path.

    No-op for in-memory databases (``":memory:"``) and ``file:`` URIs.
    """
    if conn_str != ":memory:" and not conn_str.startswith("file:"):
        # [DL-NOTE] parents=True handles deep paths like .deer-flow/data/ on first run.
        # exist_ok=True makes this idempotent — safe to call on every startup.
        pathlib.Path(conn_str).parent.mkdir(parents=True, exist_ok=True)
