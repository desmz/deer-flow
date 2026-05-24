"""Process-local authentication for Gateway internal callers."""

from __future__ import annotations

import secrets
from types import SimpleNamespace

from deerflow.runtime.user_context import DEFAULT_USER_ID

INTERNAL_AUTH_HEADER_NAME = "X-DeerFlow-Internal-Token"
# [DL-INSIGHT] Token is generated once at import time and lives only in process memory —
# never written to disk, never logged. Regenerated on every process restart.
_INTERNAL_AUTH_TOKEN = secrets.token_urlsafe(32)


def create_internal_auth_headers() -> dict[str, str]:
    """Return headers that authenticate same-process Gateway internal calls."""
    return {INTERNAL_AUTH_HEADER_NAME: _INTERNAL_AUTH_TOKEN}


def is_valid_internal_auth_token(token: str | None) -> bool:
    """Return True when *token* matches the process-local internal token."""
    # [DL-NOTE] compare_digest is constant-time — prevents timing side-channel attacks
    # even though the token only travels over localhost.
    return bool(token) and secrets.compare_digest(token, _INTERNAL_AUTH_TOKEN)


def get_internal_user():
    """Return the synthetic user used for trusted internal channel calls."""
    # [DL-INSIGHT] All IM channel traffic (Feishu, Slack, Telegram, etc.) runs as DEFAULT_USER_ID
    # ("default") — no per-channel user isolation. Threads created via channels are shared.
    return SimpleNamespace(id=DEFAULT_USER_ID, system_role="internal")
