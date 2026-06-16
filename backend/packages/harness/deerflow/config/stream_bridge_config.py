"""Configuration for stream bridge."""

from typing import Literal

from pydantic import BaseModel, Field

StreamBridgeType = Literal["memory", "redis"]


class StreamBridgeConfig(BaseModel):
    """Configuration for the stream bridge that connects agent workers to SSE endpoints."""

    # [DL-WARN] Only "memory" is implemented. "redis" is declared in the Literal type
    # but has no implementation — selecting it will silently fall back to memory in
    # async_provider.py because the type check there only branches on "memory".
    type: StreamBridgeType = Field(
        default="memory",
        description="Stream bridge backend type. 'memory' uses in-process asyncio.Queue (single-process only). 'redis' uses Redis Streams (planned for Phase 2, not yet implemented).",
    )
    redis_url: str | None = Field(
        default=None,
        description="Redis URL for the redis stream bridge type. Example: 'redis://localhost:6379/0'.",
    )
    # [DL-NOTE] This is the SSE event buffer per run. 256 events covers most conversations;
    # a slow SSE consumer that falls behind will start blocking the agent worker at this limit.
    queue_maxsize: int = Field(
        default=256,
        description="Maximum number of events buffered per run in the memory bridge.",
    )


# [DL-INSIGHT] Singleton starts as None (unlike MemoryConfig's eager default). AppConfig field
# is also Optional — the entire `stream_bridge:` section can be absent from config.yaml.
# async_provider.py falls back to queue_maxsize=256 when get_stream_bridge_config() returns None.
_stream_bridge_config: StreamBridgeConfig | None = None


def get_stream_bridge_config() -> StreamBridgeConfig | None:
    """Get the current stream bridge configuration, or None if not configured."""
    return _stream_bridge_config


def set_stream_bridge_config(config: StreamBridgeConfig | None) -> None:
    """Set the stream bridge configuration."""
    global _stream_bridge_config
    _stream_bridge_config = config


def load_stream_bridge_config_from_dict(config_dict: dict | None) -> None:
    """Load stream bridge configuration from a dictionary."""
    global _stream_bridge_config
    if config_dict is None:
        _stream_bridge_config = None
        return
    _stream_bridge_config = StreamBridgeConfig(**config_dict)
