"""IM Channel integration for DeerFlow.

Provides a pluggable channel system that connects external messaging platforms
(Feishu/Lark, Slack, Telegram) to the DeerFlow agent via the ChannelManager,
which uses ``langgraph-sdk`` to communicate with Gateway's LangGraph-compatible API.
"""

# [DL-NOTE] Docstring lists only Feishu/Slack/Telegram, but the package ships
# 7 adapters (also Discord, DingTalk, WeChat, WeCom) — docstring is stale.

from app.channels.base import Channel
from app.channels.message_bus import InboundMessage, MessageBus, OutboundMessage

# [DL-INSIGHT] Deliberately minimal facade: only the abstract contract (Channel)
# and the bus message envelopes are re-exported. ChannelManager / start_channel_service
# are NOT here — callers deep-import them, keeping concrete adapters off the public surface.
__all__ = [
    "Channel",
    "InboundMessage",
    "MessageBus",
    "OutboundMessage",
]
