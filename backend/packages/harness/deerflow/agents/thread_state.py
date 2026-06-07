from typing import Annotated, NotRequired, TypedDict

# [DL-NOTE] AgentState provides messages: Annotated[list[BaseMessage], add_messages] — the core conversation accumulator.
# All 17 middlewares and the lead agent node share this single mutable state dict across the LangGraph turn.
from langchain.agents import AgentState


class SandboxState(TypedDict):
    sandbox_id: NotRequired[str | None]


class ThreadDataState(TypedDict):
    workspace_path: NotRequired[str | None]
    uploads_path: NotRequired[str | None]
    outputs_path: NotRequired[str | None]


class ViewedImageData(TypedDict):
    base64: str
    mime_type: str


def merge_artifacts(existing: list[str] | None, new: list[str] | None) -> list[str]:
    """Reducer for artifacts list - merges and deduplicates artifacts."""
    if existing is None:
        return new or []
    if new is None:
        return existing
    # Use dict.fromkeys to deduplicate while preserving order
    # [DL-INSIGHT] existing comes first in the concat, so existing items keep their positions.
    # Re-adding an already-present artifact path is a silent no-op — idempotent by design.
    return list(dict.fromkeys(existing + new))


def merge_viewed_images(existing: dict[str, ViewedImageData] | None, new: dict[str, ViewedImageData] | None) -> dict[str, ViewedImageData]:
    """Reducer for viewed_images dict - merges image dictionaries.

    Special case: If new is an empty dict {}, it clears the existing images.
    This allows middlewares to clear the viewed_images state after processing.
    """
    if existing is None:
        return new or {}
    if new is None:
        return existing
    # Special case: empty dict means clear all viewed images
    # [DL-INSIGHT] {} is the supported in-band clear signal, but ViewImageMiddleware does NOT use it.
    # The middleware deduplicates via message-content substring search instead; viewed_images accumulates.
    if len(new) == 0:
        return {}
    # Merge dictionaries, new values override existing ones for same keys
    return {**existing, **new}


# [DL-INSIGHT] SandboxState and ThreadDataState partition state into middleware-owned slices,
# preventing field-name collisions and making ownership explicit across the 17-middleware chain.
class ThreadState(AgentState):
    sandbox: NotRequired[SandboxState | None]
    thread_data: NotRequired[ThreadDataState | None]
    title: NotRequired[str | None]
    # [DL-NOTE] Annotated fields carry explicit reducers; NotRequired fields use last-write-wins.
    # Only fields where multiple graph nodes append data concurrently need a reducer.
    artifacts: Annotated[list[str], merge_artifacts]
    todos: NotRequired[list | None]
    uploaded_files: NotRequired[list[dict] | None]
    viewed_images: Annotated[dict[str, ViewedImageData], merge_viewed_images]  # image_path -> {base64, mime_type}
