"""Configuration for deferred tool loading via tool_search."""

from pydantic import BaseModel, Field


# [DL-INSIGHT] When enabled, MCP tools are hidden from the agent's bound tool list.
# They're listed in the system prompt by name and loaded on-demand via `tool_search`.
# This cuts context usage when many MCP servers are connected.
class ToolSearchConfig(BaseModel):
    """Configuration for deferred tool loading via tool_search.

    When enabled, MCP tools are not loaded into the agent's context directly.
    Instead, they are listed by name in the system prompt and discoverable
    via the tool_search tool at runtime.
    """

    enabled: bool = Field(
        default=False,
        description="Defer tools and enable tool_search",
    )


_tool_search_config: ToolSearchConfig | None = None


def get_tool_search_config() -> ToolSearchConfig:
    """Get the tool search config, loading from AppConfig if needed."""
    global _tool_search_config
    if _tool_search_config is None:
        # [DL-NOTE] Safe default: deferred loading is off until AppConfig calls
        # load_tool_search_config_from_dict() during startup (app_config.py:215).
        _tool_search_config = ToolSearchConfig()
    return _tool_search_config


# [DL-NOTE] AppConfig wires this module-level singleton after parsing config.yaml.
# No mtime-based hot reload here — the singleton is only updated when AppConfig reloads.
def load_tool_search_config_from_dict(data: dict) -> ToolSearchConfig:
    """Load tool search config from a dict (called during AppConfig loading)."""
    global _tool_search_config
    _tool_search_config = ToolSearchConfig.model_validate(data)
    return _tool_search_config
