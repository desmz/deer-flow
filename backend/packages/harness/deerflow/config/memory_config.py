"""Configuration for memory mechanism."""

from pydantic import BaseModel, Field


class MemoryConfig(BaseModel):
    """Configuration for global memory mechanism."""

    # [DL-INSIGHT] Two independent switches: `enabled` gates collection (updater + queue run);
    # `injection_enabled` gates injection (memory appears in system prompt). You can collect
    # without injecting (background learning, no prompt cost) but not the reverse.
    enabled: bool = Field(
        default=True,
        description="Whether to enable memory mechanism",
    )
    # [DL-INSIGHT] Empty string = per-user isolation at `{base_dir}/users/{user_id}/memory.json`.
    # Absolute path opts out of per-user isolation — all users share one file. This is the
    # backward-compat escape hatch for operators who set an explicit path before per-user
    # isolation was introduced.
    storage_path: str = Field(
        default="",
        description=(
            "Path to store memory data. "
            "If empty, defaults to per-user memory at `{base_dir}/users/{user_id}/memory.json`. "
            "Absolute paths are used as-is and opt out of per-user isolation "
            "(all users share the same file). "
            "Relative paths are resolved against `Paths.base_dir` "
            "(not the backend working directory). "
            "Note: if you previously set this to `.deer-flow/memory.json`, "
            "the file will now be resolved as `{base_dir}/.deer-flow/memory.json`; "
            "migrate existing data or use an absolute path to preserve the old location."
        ),
    )
    # [DL-NOTE] Reflection class path loaded via rsplit(".", 1) in storage.py:228 — same concept
    # as `use` on other configs, but uses manual import rather than the resolve_class() utility.
    storage_class: str = Field(
        default="deerflow.agents.memory.storage.FileMemoryStorage",
        description="The class path for memory storage provider",
    )
    # [DL-NOTE] Read at timer-scheduling time in queue.py:160, not once at startup —
    # so changing this via set_memory_config() takes effect on the next debounce cycle.
    debounce_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Seconds to wait before processing queued updates (debounce)",
    )
    model_name: str | None = Field(
        default=None,
        description="Model name to use for memory updates (None = use default model)",
    )
    max_facts: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Maximum number of facts to store",
    )
    # [DL-NOTE] Read in updater.py:565 — facts with confidence below this threshold are discarded
    # during LLM extraction before being written to storage.
    fact_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for storing facts",
    )
    injection_enabled: bool = Field(
        default=True,
        description="Whether to inject memory into system prompt",
    )
    # [DL-NOTE] Read in prompt.py:586 to cap how much memory content enters the LLM context per turn.
    max_injection_tokens: int = Field(
        default=2000,
        ge=100,
        le=8000,
        description="Maximum tokens to use for memory injection",
    )


# [DL-NOTE] Unlike guardrails_config, this initializes eagerly (not None) — get_memory_config()
# is safe to call before AppConfig loads. AppConfig overwrites it via load_memory_config_from_dict().
_memory_config: MemoryConfig = MemoryConfig()


def get_memory_config() -> MemoryConfig:
    """Get the current memory configuration."""
    return _memory_config


def set_memory_config(config: MemoryConfig) -> None:
    """Set the memory configuration."""
    global _memory_config
    _memory_config = config


def load_memory_config_from_dict(config_dict: dict) -> None:
    """Load memory configuration from a dictionary."""
    global _memory_config
    _memory_config = MemoryConfig(**config_dict)
