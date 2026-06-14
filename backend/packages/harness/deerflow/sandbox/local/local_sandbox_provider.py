import logging
from pathlib import Path

from deerflow.sandbox.local.local_sandbox import LocalSandbox, PathMapping
from deerflow.sandbox.sandbox import Sandbox
from deerflow.sandbox.sandbox_provider import SandboxProvider

logger = logging.getLogger(__name__)

# [DL-INSIGHT] Module-level singleton survives provider instance replacement.
# reset() must explicitly clear this or stale path mappings persist across config reloads (see regression test_reset_sandbox_provider_clears_local_singleton).
_singleton: LocalSandbox | None = None


class LocalSandboxProvider(SandboxProvider):
    # [DL-NOTE] Tells uploads router to write files directly to the thread dir on the host filesystem.
    # When False (AioSandboxProvider), uploads are pushed through the sandbox write API into the container instead.
    uses_thread_data_mounts = True

    def __init__(self):
        """Initialize the local sandbox provider with path mappings."""
        self._path_mappings = self._setup_path_mappings()

    def _setup_path_mappings(self) -> list[PathMapping]:
        """
        Setup path mappings for local sandbox.

        Maps container paths to actual local paths, including skills directory
        and any custom mounts configured in config.yaml.

        Returns:
            List of path mappings
        """
        mappings: list[PathMapping] = []

        # Map skills container path to local skills directory
        try:
            from deerflow.config import get_app_config

            config = get_app_config()
            skills_path = config.skills.get_skills_path()
            container_path = config.skills.container_path

            # Only add mapping if skills directory exists
            if skills_path.exists():
                mappings.append(
                    PathMapping(
                        container_path=container_path,
                        local_path=str(skills_path),
                        read_only=True,  # Skills directory is always read-only
                    )
                )

            # Map custom mounts from sandbox config
            # [DL-NOTE] These three container paths are reserved: user config cannot shadow them with custom mounts.
            _RESERVED_CONTAINER_PREFIXES = [container_path, "/mnt/acp-workspace", "/mnt/user-data"]
            sandbox_config = config.sandbox
            if sandbox_config and sandbox_config.mounts:
                for mount in sandbox_config.mounts:
                    host_path = Path(mount.host_path)
                    container_path = mount.container_path.rstrip("/") or "/"

                    if not host_path.is_absolute():
                        logger.warning(
                            "Mount host_path must be absolute, skipping: %s -> %s",
                            mount.host_path,
                            mount.container_path,
                        )
                        continue

                    if not container_path.startswith("/"):
                        logger.warning(
                            "Mount container_path must be absolute, skipping: %s -> %s",
                            mount.host_path,
                            mount.container_path,
                        )
                        continue

                    # Reject mounts that conflict with reserved container paths
                    if any(container_path == p or container_path.startswith(p + "/") for p in _RESERVED_CONTAINER_PREFIXES):
                        logger.warning(
                            "Mount container_path conflicts with reserved prefix, skipping: %s",
                            mount.container_path,
                        )
                        continue
                    # Ensure the host path exists before adding mapping
                    if host_path.exists():
                        mappings.append(
                            PathMapping(
                                container_path=container_path,
                                local_path=str(host_path.resolve()),
                                read_only=mount.read_only,
                            )
                        )
                    else:
                        logger.warning(
                            "Mount host_path does not exist, skipping: %s -> %s",
                            mount.host_path,
                            mount.container_path,
                        )
        except Exception as e:
            # Log but don't fail if config loading fails
            logger.warning("Could not setup path mappings: %s", e, exc_info=True)

        return mappings

    # [DL-INSIGHT] thread_id is ignored — all threads share one LocalSandbox singleton with fixed path mappings.
    # Per-thread /mnt/user-data translation is handled in tools.py (replace_virtual_path), not via path_mappings here.
    def acquire(self, thread_id: str | None = None) -> str:
        global _singleton
        if _singleton is None:
            _singleton = LocalSandbox("local", path_mappings=self._path_mappings)
        return _singleton.id

    def get(self, sandbox_id: str) -> Sandbox | None:
        if sandbox_id == "local":
            if _singleton is None:
                self.acquire()
            return _singleton
        return None

    # [DL-NOTE] No-op by design: the singleton is reused across all threads and turns.
    # AioSandboxProvider.release() stops a Docker container here; LocalSandbox has nothing to tear down.
    def release(self, sandbox_id: str) -> None:
        # LocalSandbox uses singleton pattern - no cleanup needed.
        # Note: This method is intentionally not called by SandboxMiddleware
        # to allow sandbox reuse across multiple turns in a thread.
        # For Docker-based providers (e.g., AioSandboxProvider), cleanup
        # happens at application shutdown via the shutdown() method.
        pass

    def reset(self) -> None:
        # reset_sandbox_provider() must also clear the module singleton.
        global _singleton
        _singleton = None

    def shutdown(self) -> None:
        # LocalSandboxProvider has no extra resources beyond the shared
        # singleton, so shutdown uses the same cleanup path as reset.
        self.reset()
