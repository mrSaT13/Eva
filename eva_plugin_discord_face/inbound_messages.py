from typing import Any

from eva.brain.abc import OutputChannelPool
from eva.brain.inbound_messages import PlainTextMessage


class DiscordTextMessage(PlainTextMessage):
    __slots__ = ('author_id', 'channel_id')

    def __init__(
            self,
            text: str,
            *,
            author_id: Any,
            channel_id: Any,
            is_direct: bool,
            outputs: OutputChannelPool,
    ):
        super().__init__(text, outputs, {'is_direct': is_direct})
        self.author_id = author_id
        self.channel_id = channel_id
