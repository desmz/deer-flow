"""Hooks fired before summarization removes messages from state."""
# [DL-INSIGHT] "Rescue before erasure" pattern: SummarizationMiddleware is about to
# permanently remove messages from LangGraph state. This hook intercepts them first
# so MemoryMiddleware's after-agent pass won't find them already gone.

from __future__ import annotations

from deerflow.agents.memory.message_processing import detect_correction, detect_reinforcement, filter_messages_for_memory
from deerflow.agents.memory.queue import get_memory_queue
from deerflow.agents.middlewares.summarization_middleware import SummarizationEvent
from deerflow.config.memory_config import get_memory_config
from deerflow.runtime.user_context import resolve_runtime_user_id


def memory_flush_hook(event: SummarizationEvent) -> None:
    """Flush messages about to be summarized into the memory queue."""
    if not get_memory_config().enabled or not event.thread_id:
        return

    filtered_messages = filter_messages_for_memory(list(event.messages_to_summarize))
    # [DL-NOTE] Both sides of an exchange must be present — a turn with only human
    # or only AI messages has no useful signal for fact extraction.
    user_messages = [message for message in filtered_messages if getattr(message, "type", None) == "human"]
    assistant_messages = [message for message in filtered_messages if getattr(message, "type", None) == "ai"]
    if not user_messages or not assistant_messages:
        return

    correction_detected = detect_correction(filtered_messages)
    reinforcement_detected = not correction_detected and detect_reinforcement(filtered_messages)
    # [DL-NOTE] resolve_runtime_user_id() reads from the LangGraph Runtime object — more
    # reliable here than get_effective_user_id() since the Runtime survives thread-pool
    # boundaries where the ContextVar may already be cleared.
    user_id = resolve_runtime_user_id(event.runtime)
    queue = get_memory_queue()
    # [DL-INSIGHT] add_nowait() (delay=0), not add() (30s debounce): messages are being
    # removed from state right now so there is no time to wait — process immediately.
    queue.add_nowait(
        thread_id=event.thread_id,
        messages=filtered_messages,
        agent_name=event.agent_name,
        user_id=user_id,
        correction_detected=correction_detected,
        reinforcement_detected=reinforcement_detected,
    )
