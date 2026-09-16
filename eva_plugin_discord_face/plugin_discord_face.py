"""
Discord-лицо Eva: приём и отправка сообщений через Discord-бота.

Токен: discord.com/developers/applications -> Bot -> Token.
ОБЯЗАТЕЛЬНО включите привилегированный intent MESSAGE CONTENT
(Bot -> Privileged Gateway Intents), иначе бот не увидит текст сообщений.

Поведение: в личке отвечает всегда, на серверах — только при упоминании.
"""

import asyncio
import time
from logging import getLogger
from typing import Optional

from eva.brain.abc import Brain, OutputChannel
from eva.brain.output_pool import OutputPoolImpl
from eva.plugin_loader.abc import PluginManager
from eva.plugin_loader.magic_plugin import MagicPlugin
from eva.plugin_loader.run_operation import call_all_as_wrappers, call_all
from eva_plugin_discord_face.inbound_messages import DiscordTextMessage
from eva_plugin_discord_face.outputs import make_channel

_logger = getLogger('face_discord')


class DiscordFacePlugin(MagicPlugin):
    name = 'face_discord'
    version = '1.0.0'

    config_comment = """
    Настройки Discord-бота.

    Доступные параметры:
    - `token` - токен бота (Developer Portal -> Bot -> Token).
                Включите MESSAGE CONTENT intent, иначе бот не увидит текст.
                После изменения токена нужен перезапуск.
    - `reply_mode` - 'reply' (ответом) или 'plain' (простым сообщением)
    """

    config = {
        "token": None,
        "reply_mode": "reply",
    }

    _logger = getLogger(name)

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[object] = None

    def run(self, pm: PluginManager, *_args, **_kwargs):
        try:
            import discord  # type: ignore
        except ImportError:
            self._logger.warning("discord.py не установлен: pip install discord.py. Discord-бот не запущен.")
            return

        token: Optional[str] = self.config.get('token')
        if not token:
            self._logger.warning("Токен Discord-бота не установлен. Бот не будет запущен.")
            return

        brain: Brain = call_all_as_wrappers(
            pm.get_operation_sequence('get_brain'), None, pm)
        if brain is None:
            raise Exception("Не удалось найти мозг.")

        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        self._client = client
        reply_mode = self.config.get('reply_mode', 'reply')

        with brain.send_messages(OutputPoolImpl(())) as send_message:
            @client.event
            async def on_ready():
                self._logger.info("Discord-бот запущен: %s", client.user)

            @client.event
            async def on_message(message):
                try:
                    if message.author == client.user or message.author.bot:
                        return
                    text = (message.content or '').strip()
                    if not text:
                        return
                    is_dm = message.guild is None
                    mentioned = client.user in message.mentions
                    if not is_dm and not mentioned:
                        return
                    if mentioned:
                        text = text.replace(f'<@{client.user.id}>', '').replace(
                            f'<@!{client.user.id}>', '').strip()
                        if not text:
                            return
                    outputs: list[OutputChannel] = [make_channel(
                        asyncio.get_running_loop(), message.channel,
                        reply_message=message if reply_mode == 'reply' else None)]

                    inbound = DiscordTextMessage(
                        text,
                        author_id=message.author.id,
                        channel_id=message.channel.id,
                        is_direct=True,
                        outputs=OutputPoolImpl(outputs),
                    )
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, send_message, inbound)
                except Exception:
                    self._logger.exception("Ошибка обработки Discord-сообщения")

            backoff = 5
            while True:
                try:
                    asyncio.run(client.start(str(token)))
                    return
                except Exception:
                    self._logger.exception(
                        "Discord-подключение упало, перезапуск через %s сек", backoff)
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 300)

    def terminate(self, *_args, **_kwargs):
        client = self._client
        if client is not None:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(client.close(), loop).result(timeout=10)
                else:
                    loop.run_until_complete(client.close())
            except Exception:
                pass
