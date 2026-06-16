import os
import threading

from pydantic import BaseModel, Field

# [DL-INSIGHT] Tracing is the only config subsystem that reads exclusively from env vars —
# NOT from config.yaml. No AppConfig field, no hot-reload. Changing tracing requires a
# process restart. This follows LangChain/LangSmith's own env-var conventions.
_config_lock = threading.Lock()


class LangSmithTracingConfig(BaseModel):
    """Configuration for LangSmith tracing."""

    enabled: bool = Field(...)
    api_key: str | None = Field(...)
    project: str = Field(...)
    endpoint: str = Field(...)

    @property
    def is_configured(self) -> bool:
        # [DL-NOTE] is_configured = enabled AND keys present. This is the gate for actually
        # creating a tracer. enabled=True but no key → not configured (silent, no tracer).
        return self.enabled and bool(self.api_key)

    def validate(self) -> None:
        # [DL-NOTE] validate() raises on enabled-but-missing-key — called explicitly at
        # startup by validate_enabled_tracing_providers(), not automatically by Pydantic.
        if self.enabled and not self.api_key:
            raise ValueError("LangSmith tracing is enabled but LANGSMITH_API_KEY (or LANGCHAIN_API_KEY) is not set.")


class LangfuseTracingConfig(BaseModel):
    """Configuration for Langfuse tracing."""

    enabled: bool = Field(...)
    public_key: str | None = Field(...)
    secret_key: str | None = Field(...)
    host: str = Field(...)

    @property
    def is_configured(self) -> bool:
        return self.enabled and bool(self.public_key) and bool(self.secret_key)

    def validate(self) -> None:
        if not self.enabled:
            return
        missing: list[str] = []
        if not self.public_key:
            missing.append("LANGFUSE_PUBLIC_KEY")
        if not self.secret_key:
            missing.append("LANGFUSE_SECRET_KEY")
        if missing:
            raise ValueError(f"Langfuse tracing is enabled but required settings are missing: {', '.join(missing)}")


class TracingConfig(BaseModel):
    """Tracing configuration for supported providers."""

    langsmith: LangSmithTracingConfig = Field(...)
    langfuse: LangfuseTracingConfig = Field(...)

    @property
    def is_configured(self) -> bool:
        return bool(self.enabled_providers)

    @property
    def explicitly_enabled_providers(self) -> list[str]:
        # [DL-NOTE] explicitly_enabled = enabled flag is True, regardless of whether keys
        # are present. Used by validate_enabled() to decide which providers to validate.
        enabled: list[str] = []
        if self.langsmith.enabled:
            enabled.append("langsmith")
        if self.langfuse.enabled:
            enabled.append("langfuse")
        return enabled

    @property
    def enabled_providers(self) -> list[str]:
        # [DL-NOTE] enabled_providers = enabled AND keys present (is_configured).
        # Only these providers get actual tracer callbacks wired in factory.py.
        enabled: list[str] = []
        if self.langsmith.is_configured:
            enabled.append("langsmith")
        if self.langfuse.is_configured:
            enabled.append("langfuse")
        return enabled

    def validate_enabled(self) -> None:
        self.langsmith.validate()
        self.langfuse.validate()


_tracing_config: TracingConfig | None = None


_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _env_flag_preferred(*names: str) -> bool:
    """Return the boolean value of the first env var that is present and non-empty."""
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip():
            return value.strip().lower() in _TRUTHY_VALUES
    return False


def _first_env_value(*names: str) -> str | None:
    """Return the first non-empty environment value from candidate names."""
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def get_tracing_config() -> TracingConfig:
    """Get the current tracing configuration from environment variables."""
    global _tracing_config
    if _tracing_config is not None:
        return _tracing_config
    # [DL-INSIGHT] Classic double-checked locking: outer check avoids lock contention on
    # the hot path; inner check prevents a second thread from re-initializing after the
    # first thread built the singleton while this thread was waiting for the lock.
    with _config_lock:
        if _tracing_config is not None:
            return _tracing_config
        _tracing_config = TracingConfig(
            langsmith=LangSmithTracingConfig(
                # [DL-NOTE] LangSmith accepts legacy LANGCHAIN_* env var aliases so configs
                # written for older LangChain versions still work without changes.
                enabled=_env_flag_preferred("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", "LANGCHAIN_TRACING"),
                api_key=_first_env_value("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"),
                project=_first_env_value("LANGSMITH_PROJECT", "LANGCHAIN_PROJECT") or "deer-flow",
                endpoint=_first_env_value("LANGSMITH_ENDPOINT", "LANGCHAIN_ENDPOINT") or "https://api.smith.langchain.com",
            ),
            langfuse=LangfuseTracingConfig(
                enabled=_env_flag_preferred("LANGFUSE_TRACING"),
                public_key=_first_env_value("LANGFUSE_PUBLIC_KEY"),
                secret_key=_first_env_value("LANGFUSE_SECRET_KEY"),
                host=_first_env_value("LANGFUSE_BASE_URL") or "https://cloud.langfuse.com",
            ),
        )
        return _tracing_config


def get_enabled_tracing_providers() -> list[str]:
    """Return the configured tracing providers that are enabled and complete."""
    return get_tracing_config().enabled_providers


def get_explicitly_enabled_tracing_providers() -> list[str]:
    """Return tracing providers explicitly enabled by config, even if incomplete."""
    return get_tracing_config().explicitly_enabled_providers


def validate_enabled_tracing_providers() -> None:
    """Validate that any explicitly enabled providers are fully configured."""
    get_tracing_config().validate_enabled()


def is_tracing_enabled() -> bool:
    """Check if any tracing provider is enabled and fully configured."""
    return get_tracing_config().is_configured
