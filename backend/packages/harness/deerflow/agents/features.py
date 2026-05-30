"""Declarative feature flags and middleware positioning for create_deerflow_agent.

Pure data classes and decorators — no I/O, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from langchain.agents.middleware import AgentMiddleware


# [DL-INSIGHT] RuntimeFeatures is a declarative alternative to passing a raw middleware list.
# The factory reads it and assembles the chain — callers describe *what* they want, not *how* to build it.
@dataclass
class RuntimeFeatures:
    """Declarative feature flags for ``create_deerflow_agent``.

    Most features accept:
    - ``True``: use the built-in default middleware
    - ``False``: disable
    - An ``AgentMiddleware`` instance: use this custom implementation instead

    ``summarization`` and ``guardrail`` have no built-in default — they only
    accept ``False`` (disable) or an ``AgentMiddleware`` instance (custom).
    """

    sandbox: bool | AgentMiddleware = True
    memory: bool | AgentMiddleware = False
    # [DL-NOTE] Literal[False] instead of bool signals "no sensible built-in default exists" at the type level.
    # Callers must supply a real AgentMiddleware or leave it off — they can't accidentally enable it with True.
    summarization: Literal[False] | AgentMiddleware = False
    subagent: bool | AgentMiddleware = False
    vision: bool | AgentMiddleware = False
    auto_title: bool | AgentMiddleware = False
    guardrail: Literal[False] | AgentMiddleware = False
    loop_detection: bool | AgentMiddleware = True


# ---------------------------------------------------------------------------
# Middleware positioning decorators
# ---------------------------------------------------------------------------


# [DL-INSIGHT] @Next/@Prev let callers declare relative position rather than an absolute list index.
# This is robust to chain reordering: "I go after DanglingToolCallMiddleware" stays valid if other
# middlewares are added or removed around it. The anchor is validated eagerly at decoration time.
def Next(anchor: type[AgentMiddleware]):
    """Declare this middleware should be placed after *anchor* in the chain."""
    if not (isinstance(anchor, type) and issubclass(anchor, AgentMiddleware)):
        raise TypeError(f"@Next expects an AgentMiddleware subclass, got {anchor!r}")

    def decorator(cls: type[AgentMiddleware]) -> type[AgentMiddleware]:
        # [DL-NOTE] Stamps a class attribute; factory.py reads it via getattr(type(mw), "_next_anchor", None).
        cls._next_anchor = anchor  # type: ignore[attr-defined]
        return cls

    return decorator


def Prev(anchor: type[AgentMiddleware]):
    """Declare this middleware should be placed before *anchor* in the chain."""
    if not (isinstance(anchor, type) and issubclass(anchor, AgentMiddleware)):
        raise TypeError(f"@Prev expects an AgentMiddleware subclass, got {anchor!r}")

    def decorator(cls: type[AgentMiddleware]) -> type[AgentMiddleware]:
        cls._prev_anchor = anchor  # type: ignore[attr-defined]
        return cls

    return decorator
