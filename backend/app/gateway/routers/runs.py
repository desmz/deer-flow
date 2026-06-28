"""Stateless runs endpoints -- stream and wait without a pre-existing thread.

These endpoints auto-create a temporary thread when no ``thread_id`` is
supplied in the request body.  When a ``thread_id`` **is** provided, it
is reused so that conversation history is preserved across calls.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.gateway.authz import require_permission
from app.gateway.deps import get_checkpointer, get_feedback_repo, get_run_event_store, get_run_manager, get_run_store, get_stream_bridge
from app.gateway.routers.thread_runs import RunCreateRequest
from app.gateway.services import sse_consumer, start_run
from deerflow.runtime import serialize_channel_values

logger = logging.getLogger(__name__)
# [DL-INSIGHT] Sibling of thread_runs.py but runs are NOT nested under a thread here
# (/api/runs/... vs /api/threads/{id}/runs/...). This is the LangGraph "stateless runs" surface.
router = APIRouter(prefix="/api/runs", tags=["runs"])


# [DL-NOTE] "Stateless" is a misnomer when a thread_id is supplied: passing
# config.configurable.thread_id reuses an existing thread (stateful); omitting it mints a fresh uuid.
def _resolve_thread_id(body: RunCreateRequest) -> str:
    """Return the thread_id from the request body, or generate a new one."""
    thread_id = (body.config or {}).get("configurable", {}).get("thread_id")
    if thread_id:
        return str(thread_id)
    return str(uuid.uuid4())


# [DL-INSIGHT] No @require_permission here (unlike thread_runs.create_run): AuthMiddleware still
# enforces 401 globally, but there is no pre-existing thread to owner_check, so route-level guard is skipped.
@router.post("/stream")
async def stateless_stream(body: RunCreateRequest, request: Request) -> StreamingResponse:
    """Create a run and stream events via SSE.

    If ``config.configurable.thread_id`` is provided, the run is created
    on the given thread so that conversation history is preserved.
    Otherwise a new temporary thread is created.
    """
    thread_id = _resolve_thread_id(body)
    bridge = get_stream_bridge(request)
    run_mgr = get_run_manager(request)
    record = await start_run(body, thread_id, request)

    return StreamingResponse(
        sse_consumer(bridge, record, request, run_mgr),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            # [DL-NOTE] Created via /api/runs but Content-Location points at the canonical
            # /api/threads/{id}/runs/{rid} resource so the SDK resolves the run the same way.
            "Content-Location": f"/api/threads/{thread_id}/runs/{record.run_id}",
        },
    )


@router.post("/wait", response_model=dict)
async def stateless_wait(body: RunCreateRequest, request: Request) -> dict:
    """Create a run and block until completion.

    If ``config.configurable.thread_id`` is provided, the run is created
    on the given thread so that conversation history is preserved.
    Otherwise a new temporary thread is created.
    """
    thread_id = _resolve_thread_id(body)
    record = await start_run(body, thread_id, request)

    if record.task is not None:
        try:
            await record.task
        except asyncio.CancelledError:
            pass

    checkpointer = get_checkpointer(request)
    config = {"configurable": {"thread_id": thread_id}}
    try:
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if checkpoint_tuple is not None:
            checkpoint = getattr(checkpoint_tuple, "checkpoint", {}) or {}
            channel_values = checkpoint.get("channel_values", {})
            return serialize_channel_values(channel_values)
    except Exception:
        logger.exception("Failed to fetch final state for run %s", record.run_id)

    return {"status": record.status.value, "error": record.error}


# ---------------------------------------------------------------------------
# Run-scoped read endpoints
# ---------------------------------------------------------------------------


# [DL-INSIGHT] Ownership enforcement moves to the DATA layer here. With no thread_id in the URL,
# the decorator can't owner_check; instead run_store.get is expected to scope to the current user
# via the user contextvar, returning None (→404) for runs owned by someone else.
# [DL-QUESTION] The RunStore.get(run_id) interface takes no user_id (base.py:42), so this isolation
# is purely impl-dependent — MemoryRunStore does no filtering, so dev/test mode has no cross-user guard.
async def _resolve_run(run_id: str, request: Request) -> dict:
    """Fetch run by run_id with user ownership check. Raises 404 if not found."""
    run_store = get_run_store(request)
    record = await run_store.get(run_id)  # user_id=AUTO filters by contextvar
    if record is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return record


# [DL-NOTE] require_permission has no owner_check (no thread_id in the path); per-run ownership
# is instead enforced inside _resolve_run. Pagination uses the same limit+1 has_more trick as thread_runs.
@router.get("/{run_id}/messages")
@require_permission("runs", "read")
async def run_messages(
    run_id: str,
    request: Request,
    limit: int = Query(default=50, le=200, ge=1),
    before_seq: int | None = Query(default=None),
    after_seq: int | None = Query(default=None),
) -> dict:
    """Return paginated messages for a run (cursor-based).

    Pagination:
    - after_seq: messages with seq > after_seq (forward)
    - before_seq: messages with seq < before_seq (backward)
    - neither: latest messages

    Response: { data: [...], has_more: bool }
    """
    run = await _resolve_run(run_id, request)
    event_store = get_run_event_store(request)
    rows = await event_store.list_messages_by_run(
        run["thread_id"],
        run_id,
        limit=limit + 1,
        before_seq=before_seq,
        after_seq=after_seq,
    )
    has_more = len(rows) > limit
    data = rows[:limit] if has_more else rows
    return {"data": data, "has_more": has_more}


@router.get("/{run_id}/feedback")
@require_permission("runs", "read")
async def run_feedback(run_id: str, request: Request) -> list[dict]:
    """Return all feedback for a run."""
    run = await _resolve_run(run_id, request)
    feedback_repo = get_feedback_repo(request)
    return await feedback_repo.list_by_run(run["thread_id"], run_id)
