"""Gateway router for IM channel management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channels", tags=["channels"])


# [DL-NOTE] Two thin response DTOs; nested channel status (enabled/running per name)
# is left as loose dict[str, dict] — shape produced by ChannelService.get_status().
class ChannelStatusResponse(BaseModel):
    service_running: bool
    channels: dict[str, dict]


class ChannelRestartResponse(BaseModel):
    success: bool
    message: str


# [DL-INSIGHT] Whole router is a thin HTTP veneer over the ChannelService singleton —
# no business logic here; it just reads/commands the in-process service started at lifespan.
@router.get("/", response_model=ChannelStatusResponse)
async def get_channels_status() -> ChannelStatusResponse:
    """Get the status of all IM channels."""
    # [DL-NOTE] Lazy in-function import of the service module avoids import-time coupling
    # (and the harness→app boundary noise) — same pattern in every handler below.
    from app.channels.service import get_channel_service

    service = get_channel_service()
    # [DL-NOTE] Service absent (channels not configured) is a normal state for GET, not an
    # error: report service_running=False rather than raising. Contrast restart() → 503.
    if service is None:
        return ChannelStatusResponse(service_running=False, channels={})
    status = service.get_status()
    return ChannelStatusResponse(**status)


@router.post("/{name}/restart", response_model=ChannelRestartResponse)
async def restart_channel(name: str) -> ChannelRestartResponse:
    """Restart a specific IM channel."""
    from app.channels.service import get_channel_service

    service = get_channel_service()
    # [DL-NOTE] Mutating op requires a live service → 503 if absent (vs GET's soft empty response).
    if service is None:
        raise HTTPException(status_code=503, detail="Channel service is not running")

    # [DL-INSIGHT] restart_channel returns bool, not exceptions: unknown name / missing config /
    # failed start all collapse to False → 200 with success=False, not a 4xx/5xx. Caller must
    # inspect the body, not just the status code.
    success = await service.restart_channel(name)
    if success:
        logger.info("Channel %s restarted successfully", name)
        return ChannelRestartResponse(success=True, message=f"Channel {name} restarted successfully")
    else:
        logger.warning("Failed to restart channel %s", name)
        return ChannelRestartResponse(success=False, message=f"Failed to restart channel {name}")
