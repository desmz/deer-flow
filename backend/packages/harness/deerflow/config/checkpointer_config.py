"""Configuration for LangGraph checkpointer."""

from typing import Literal

from pydantic import BaseModel, Field

CheckpointerType = Literal["memory", "sqlite", "postgres"]


# [DL-INSIGHT] This config is separate from DatabaseConfig: DatabaseConfig governs
# the app ORM (SQLAlchemy); CheckpointerConfig governs LangGraph graph state persistence
# (via langgraph-checkpoint-sqlite/postgres). They can use the same SQLite file, but
# their clients (SQLAlchemy vs LangGraph's own checkpoint lib) are independent.
class CheckpointerConfig(BaseModel):
    """Configuration for LangGraph state persistence checkpointer."""

    type: CheckpointerType = Field(
        description="Checkpointer backend type. "
        "'memory' is in-process only (lost on restart). "
        "'sqlite' persists to a local file (requires langgraph-checkpoint-sqlite). "
        "'postgres' persists to PostgreSQL (install with deerflow-harness[postgres])."
    )
    connection_string: str | None = Field(
        default=None,
        description="Connection string for sqlite (file path) or postgres (DSN). "
        "Optional for sqlite and defaults to 'store.db' when omitted. "
        "Required for postgres. "
        "For sqlite, use a file path like '.deer-flow/checkpoints.db' or ':memory:' for in-memory. "
        "For postgres, use a DSN like 'postgresql://user:pass@localhost:5432/db'.",
    )


# [DL-NOTE] Module-level singleton — None means no checkpointer is configured (app_config.py
# has no `checkpointer:` section). The provider falls back to reading app_config at runtime.
_checkpointer_config: CheckpointerConfig | None = None


def get_checkpointer_config() -> CheckpointerConfig | None:
    """Get the current checkpointer configuration, or None if not configured."""
    return _checkpointer_config


def set_checkpointer_config(config: CheckpointerConfig | None) -> None:
    """Set the checkpointer configuration."""
    global _checkpointer_config
    _checkpointer_config = config


def load_checkpointer_config_from_dict(config_dict: dict | None) -> None:
    """Load checkpointer configuration from a dictionary."""
    global _checkpointer_config
    if config_dict is None:
        _checkpointer_config = None
        return
    # [DL-NOTE] Called by AppConfig._apply_singleton_configs() on every config load/reload.
    # If the value changed, app_config.py then calls reset_checkpointer() + reset_store()
    # so the runtime singletons rebuild from the new backend. See app_config.py:223-230.
    _checkpointer_config = CheckpointerConfig(**config_dict)
