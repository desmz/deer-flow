"""Runtime path resolution for standalone harness usage."""

import os
from pathlib import Path


# [DL-INSIGHT] This module is the lowest layer of the path stack: pure CWD/env-var
# resolution with no knowledge of per-user or per-thread structure. paths.py builds on
# top of it. Kept separate so the harness can be used outside a DeerFlow project root.
def project_root() -> Path:
    """Return the caller project root for runtime-owned files."""
    if env_root := os.getenv("DEER_FLOW_PROJECT_ROOT"):
        root = Path(env_root).resolve()
        if not root.exists():
            raise ValueError(f"DEER_FLOW_PROJECT_ROOT is set to '{env_root}', but the resolved path '{root}' does not exist.")
        if not root.is_dir():
            raise ValueError(f"DEER_FLOW_PROJECT_ROOT is set to '{env_root}', but the resolved path '{root}' is not a directory.")
        return root
    # [DL-NOTE] CWD fallback means the harness must be launched from the project root;
    # `make dev` and the Docker entrypoint both enforce this convention.
    return Path.cwd().resolve()


def runtime_home() -> Path:
    """Return the writable DeerFlow state directory."""
    if env_home := os.getenv("DEER_FLOW_HOME"):
        return Path(env_home).resolve()
    # [DL-NOTE] .deer-flow/ inside the project root is where all state lives by default
    # (memory, threads, agents). This is the fallback used in local dev.
    return project_root() / ".deer-flow"


def resolve_path(value: str | os.PathLike[str], *, base: Path | None = None) -> Path:
    """Resolve absolute paths as-is and relative paths against the project root."""
    path = Path(value)
    if not path.is_absolute():
        path = (base or project_root()) / path
    return path.resolve()


def existing_project_file(names: tuple[str, ...]) -> Path | None:
    """Return the first existing named file under the project root."""
    root = project_root()
    for name in names:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None
