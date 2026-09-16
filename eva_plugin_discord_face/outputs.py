import asyncio
from concurrent.futures import Future
from logging import getLogger
from typing import Any, Callable, Optional

from eva.brain.abc import TextOutputChannel
from eva.constants.labels import pure_text_channel_labels

_logger = getLogger('face_discord')


class DiscordTextChannel(TextOutputChannel):
    """
    Канал отправки текстовых сообщений в Discord-канал/личку.
    Потокобезопасный: планирование отправки в event loop клиента.
    """

    __slots__ = ('_send_fn', '_target')

    def __init__(self, send_fn: Callable[[str], 'Future'], target: str):
        self._send_fn = send_fn
        self._target = target

    def send(self, text: str, **kwargs):
        try:
            fut = self._send_fn(text)
            fut.result(timeout=15)
        except Exception:
            _logger.exception("Discord send в %s не удался", self._target)

    @property
    def meta(self):
        return pure_text_channel_labels()


def make_channel(loop: asyncio.AbstractEventLoop, channel: Any,
                 reply_message: Optional[Any] = None) -> DiscordTextChannel:
    """Создаёт канал. Вызывать в потоке event loop клиента."""
    async def _send(text: str):
        body = text[:2000] or '...'
        if reply_message is not None:
            ref = reply_message.reference or reply_message
            await channel.send(body, reference=ref)
        else:
            await channel.send(body)

    def send_fn(text: str) -> Future:
        return asyncio.run_coroutine_threadsafe(_send(text), loop)

    target = f"#{getattr(channel, 'name', getattr(channel, 'id', '?'))}"
    return DiscordTextChannel(send_fn, target)
