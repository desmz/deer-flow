"""Sandbox metadata for cross-process discovery and state persistence."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SandboxInfo:
    """Persisted sandbox metadata that enables cross-process discovery.

    This dataclass holds all the information needed to reconnect to an
    existing sandbox from a different process (e.g., gateway vs langgraph,
    multiple workers, or across K8s pods with shared storage).
    """

    sandbox_id: str
    # [DL-INSIGHT] sandbox_url is the single reconnection token — both processes (Gateway + LangGraph)
    # use this URL to open an HTTP connection to the sandbox container.
    sandbox_url: str  # e.g. http://localhost:8080 or http://k3s:30001
    # [DL-NOTE] container_name/container_id are non-None only for LocalBackend (Docker on the same host);
    # RemoteBackend (K8s via Provisioner) uses sandbox_url directly and leaves these None.
    container_name: str | None = None  # Only for local container backend
    container_id: str | None = None  # Only for local container backend
    # [DL-NOTE] created_at is used by the orphan reconciliation sweep to GC stale sandboxes.
    # See: test_sandbox_orphan_reconciliation.py for the age-based eviction logic.
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "sandbox_id": self.sandbox_id,
            "sandbox_url": self.sandbox_url,
            "container_name": self.container_name,
            "container_id": self.container_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SandboxInfo:
        return cls(
            sandbox_id=data["sandbox_id"],
            # [DL-NOTE] Backward compat: field was renamed from "base_url" to "sandbox_url".
            sandbox_url=data.get("sandbox_url", data.get("base_url", "")),
            container_name=data.get("container_name"),
            container_id=data.get("container_id"),
            created_at=data.get("created_at", time.time()),
        )
