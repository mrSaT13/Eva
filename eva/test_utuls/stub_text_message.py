from typing import Optional

from eva.brain.abc import InboundMessage, OutputChannelPool
from eva.brain.output_pool import EMPTY_OUTPUT_POOL
from eva.utils.metadata import MetadataMapping


class StubTextMessage(InboundMessage):
    def __init__(self, text: str, meta: Optional[MetadataMapping] = None):
        self._txt = text
        self._meta = meta or {}

    def get_text(self) -> str:
        return self._txt

    def get_related_outputs(self) -> OutputChannelPool:
        return EMPTY_OUTPUT_POOL

    @property
    def meta(self) -> MetadataMapping:
        return self._meta


tm = StubTextMessage
