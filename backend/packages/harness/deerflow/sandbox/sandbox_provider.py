from abc import ABC, abstractmethod

from deerflow.config import get_app_config
from deerflow.reflection import resolve_class
from deerflow.sandbox.sandbox import Sandbox


class SandboxProvider(ABC):
    """Abstract base class for sandbox providers"""

    # [DL-NOTE] Read by the uploads router to decide if files need explicit sandbox sync.
    # True = host dirs are mounted into sandbox (already visible); False = must push via sandbox API.
    uses_thread_data_mounts: bool = False

    @abstractmethod
    def acquire(self, thread_id: str | None = None) -> str:
        """Acquire a sandbox environment and return its ID.

        Returns:
            The ID of the acquired sandbox environment.
        """
        pass

    @abstractmethod
    def get(self, sandbox_id: str) -> Sandbox | None:
        """Get a sandbox environment by ID.

        Args:
            sandbox_id: The ID of the sandbox environment to retain.
        """
        pass

    @abstractmethod
    def release(self, sandbox_id: str) -> None:
        """Release a sandbox environment.

        Args:
            sandbox_id: The ID of the sandbox environment to destroy.
        """
        pass

    def reset(self) -> None:
        # [DL-INSIGHT] Distinct from release(): resets provider-level cached state (e.g. module singleton),
        # not individual sandbox instances. Called before replacing the global provider singleton.
        """Clear cached state that survives provider instance replacement."""
        pass


# [DL-NOTE] Process-level singleton; lazily instantiated by get_sandbox_provider().
_default_sandbox_provider: SandboxProvider | None = None


def get_sandbox_provider(**kwargs) -> SandboxProvider:
    """Get the sandbox provider singleton.

    Returns a cached singleton instance. Use `reset_sandbox_provider()` to clear
    the cache, or `shutdown_sandbox_provider()` to properly shutdown and clear.

    Returns:
        A sandbox provider instance.
    """
    global _default_sandbox_provider
    if _default_sandbox_provider is None:
        config = get_app_config()
        # [DL-INSIGHT] reflection pattern: config.sandbox.use is a class path string (e.g.
        # "deerflow.sandbox.local:LocalSandboxProvider"), resolved at runtime via resolve_class().
        cls = resolve_class(config.sandbox.use, SandboxProvider)
        _default_sandbox_provider = cls(**kwargs)
    return _default_sandbox_provider


def reset_sandbox_provider() -> None:
    """Reset the sandbox provider singleton.

    This clears the cached instance without calling shutdown.
    The next call to `get_sandbox_provider()` will create a new instance.
    Useful for testing or when switching configurations.

    Providers can override `reset()` to clear any module-level state they keep
    alive across instances (for example, `LocalSandboxProvider`'s cached
    `LocalSandbox` singleton). Without it, config/mount changes would not take
    effect on the next acquire().

    Note: If the provider has active sandboxes, they will be orphaned.
    Use `shutdown_sandbox_provider()` for proper cleanup.
    """
    global _default_sandbox_provider
    if _default_sandbox_provider is not None:
        # [DL-WARN] reset() must be called BEFORE nulling the global — otherwise the reference
        # is lost and the inner singleton (e.g. LocalSandboxProvider._singleton) is never cleared.
        _default_sandbox_provider.reset()
        _default_sandbox_provider = None


def shutdown_sandbox_provider() -> None:
    """Shutdown and reset the sandbox provider.

    This properly shuts down the provider (releasing all sandboxes)
    before clearing the singleton. Call this when the application
    is shutting down or when you need to completely reset the sandbox system.
    """
    global _default_sandbox_provider
    if _default_sandbox_provider is not None:
        # [DL-NOTE] shutdown() is not part of the ABC; duck-typed because only resource-heavy
        # providers (AioSandboxProvider) implement it; LocalSandboxProvider uses reset() instead.
        if hasattr(_default_sandbox_provider, "shutdown"):
            _default_sandbox_provider.shutdown()
        _default_sandbox_provider = None


# [DL-NOTE] Test injection point — allows tests to swap in a mock provider without touching config.
def set_sandbox_provider(provider: SandboxProvider) -> None:
    """Set a custom sandbox provider instance.

    This allows injecting a custom or mock provider for testing purposes.

    Args:
        provider: The SandboxProvider instance to use.
    """
    global _default_sandbox_provider
    _default_sandbox_provider = provider
