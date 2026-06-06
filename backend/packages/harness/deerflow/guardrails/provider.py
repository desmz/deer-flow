"""GuardrailProvider protocol and data structures for pre-tool-call authorization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class GuardrailRequest:
    """Context passed to the provider for each tool call."""

    tool_name: str
    tool_input: dict[str, Any]
    # [DL-NOTE] agent_id carries the passport reference (file path or hosted ID); the provider uses
    # it to look up OAP policy for this specific agent identity.
    agent_id: str | None = None
    thread_id: str | None = None
    is_subagent: bool = False
    timestamp: str = ""


@dataclass
class GuardrailReason:
    """Structured reason for an allow/deny decision (OAP reason object)."""

    # [DL-NOTE] Reason codes follow the OAP standard (e.g. oap.tool_not_allowed, oap.allowed).
    code: str
    message: str = ""


@dataclass
class GuardrailDecision:
    """Provider's allow/deny verdict (aligned with OAP Decision object)."""

    allow: bool
    reasons: list[GuardrailReason] = field(default_factory=list)
    policy_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# [DL-INSIGHT] @runtime_checkable enables isinstance(obj, GuardrailProvider) at runtime.
# Structural (duck-type) Protocol: any class with name + evaluate + aevaluate satisfies it —
# no inheritance required. Verified by the test: isinstance(AllowlistProvider(), GuardrailProvider).
@runtime_checkable
class GuardrailProvider(Protocol):
    """Contract for pluggable tool-call authorization.

    Any class with these methods works - no base class required.
    Providers are loaded by class path via resolve_variable(),
    the same mechanism DeerFlow uses for models, tools, and sandbox.
    """

    name: str

    def evaluate(self, request: GuardrailRequest) -> GuardrailDecision:
        """Evaluate whether a tool call should proceed."""
        ...

    async def aevaluate(self, request: GuardrailRequest) -> GuardrailDecision:
        """Async variant."""
        ...
