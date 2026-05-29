"""Run status and disconnect mode enums."""

from enum import StrEnum


# [DL-INSIGHT] StrEnum values compare equal to raw strings, so RunStatus.success == "success".
# This allows JSON round-tripping and direct DB storage without explicit conversion.
class RunStatus(StrEnum):
    """Lifecycle status of a single run."""

    pending = "pending"
    running = "running"
    # [DL-NOTE] `success` is translated to "idle" when written to thread_meta (LangGraph Server API compat).
    # See: runtime/runs/worker.py — `final_status = "idle" if record.status == RunStatus.success ...`
    success = "success"
    error = "error"
    timeout = "timeout"
    # [DL-NOTE] `interrupted` = user-requested stop; `error` = system/exception failure. Distinct for UI display.
    interrupted = "interrupted"


class DisconnectMode(StrEnum):
    """Behaviour when the SSE consumer disconnects."""

    cancel = "cancel"
    # [DL-NOTE] Trailing `_` avoids shadowing Python's `continue` keyword.
    # `continue_` keeps the background run alive even after the SSE consumer drops. See: app/gateway/services.py.
    continue_ = "continue"
