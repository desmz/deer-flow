"""Configuration for pre-tool-call authorization."""

from pydantic import BaseModel, Field


class GuardrailProviderConfig(BaseModel):
    """Configuration for a guardrail provider."""

    # [DL-NOTE] `use` is resolved via resolve_class() in tool_error_handling_middleware.py.
    # `config` is passed as **kwargs to the provider's __init__ — open-ended provider settings.
    use: str = Field(description="Class path (e.g. 'deerflow.guardrails.builtin:AllowlistProvider')")
    config: dict = Field(default_factory=dict, description="Provider-specific settings passed as kwargs")


class GuardrailsConfig(BaseModel):
    """Configuration for pre-tool-call authorization.

    When enabled, every tool call passes through the configured provider
    before execution. The provider receives tool name, arguments, and the
    agent's passport reference, and returns an allow/deny decision.
    """

    enabled: bool = Field(default=False, description="Enable guardrail middleware")
    # [DL-INSIGHT] fail_closed=True is a security-first default: if the provider errors,
    # the tool call is blocked rather than allowed through. See guardrails/middleware.py:74.
    fail_closed: bool = Field(default=True, description="Block tool calls if provider errors")
    # [DL-NOTE] passport is forwarded as agent_id to the provider for per-agent policy lookups
    # (e.g. OAP policy server uses it to locate ~/.aport/deerflow/ config).
    passport: str | None = Field(default=None, description="OAP passport path or hosted agent ID")
    provider: GuardrailProviderConfig | None = Field(default=None, description="Guardrail provider configuration")


# [DL-NOTE] Same singleton pattern as tool_search_config and guardrails_config.
# AppConfig wires this via load_guardrails_config_from_dict() at startup (app_config.py:216).
_guardrails_config: GuardrailsConfig | None = None


def get_guardrails_config() -> GuardrailsConfig:
    """Get the guardrails config, returning defaults if not loaded."""
    global _guardrails_config
    if _guardrails_config is None:
        _guardrails_config = GuardrailsConfig()
    return _guardrails_config


def load_guardrails_config_from_dict(data: dict) -> GuardrailsConfig:
    """Load guardrails config from a dict (called during AppConfig loading)."""
    global _guardrails_config
    _guardrails_config = GuardrailsConfig.model_validate(data)
    return _guardrails_config


def reset_guardrails_config() -> None:
    """Reset the cached config instance. Used in tests to prevent singleton leaks."""
    global _guardrails_config
    _guardrails_config = None
