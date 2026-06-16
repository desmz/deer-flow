"""Configuration for the custom agents management API."""

from pydantic import BaseModel, Field


# [DL-INSIGHT] A single boolean guards read AND write access to all custom-agent HTTP routes
# (SOUL.md, config, USER.md). Default=False is the secure default: the agent management
# API is opt-in, not available unless explicitly enabled in config.yaml.
class AgentsApiConfig(BaseModel):
    """Configuration for custom-agent and user-profile management routes."""

    enabled: bool = Field(
        default=False,
        description=("Whether to expose the custom-agent management API over HTTP. When disabled, the gateway rejects read/write access to custom agent SOUL.md, config, and USER.md prompt-management routes."),
    )


# [DL-NOTE] Initialized to AgentsApiConfig() (enabled=False), never None. Routes are
# registered at startup regardless — the 403 gate fires at request time, not boot time.
_agents_api_config: AgentsApiConfig = AgentsApiConfig()


def get_agents_api_config() -> AgentsApiConfig:
    """Get the current agents API configuration."""
    return _agents_api_config


def set_agents_api_config(config: AgentsApiConfig) -> None:
    """Set the agents API configuration."""
    global _agents_api_config
    _agents_api_config = config


def load_agents_api_config_from_dict(config_dict: dict) -> None:
    """Load agents API configuration from a dictionary."""
    global _agents_api_config
    # [DL-NOTE] Called by AppConfig._apply_singleton_configs() on every config reload —
    # toggling agents_api.enabled in config.yaml takes effect without a process restart.
    _agents_api_config = AgentsApiConfig(**config_dict)
