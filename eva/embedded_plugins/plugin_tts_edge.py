"""
Плагин TTS на основе Microsoft Edge TTS.
Бесплатный,高质量, поддерживает русский и английский.
Требует: pip install edge-tts
"""

import asyncio
import os
import tempfile
from functools import cache
from logging import getLogger
from typing import Optional, Any, TypedDict

from eva.face.abc import FileWritingTTS, TTSResultFile
from eva.face.tts_helpers import create_disposable_tts_result_file
from eva.utils.metadata import MetadataMapping

name = 'plugin_tts_edge'
version = '1.0.0'

_logger = getLogger(name)


class _Config(TypedDict):
    default_voice: str
    voices: dict[str, str]


config: _Config = {
    "default_voice": "ru-RU-SvetlanaNeural",
    "voices": {
        "ru_female": "ru-RU-SvetlanaNeural",
        "ru_male": "ru-RU-DmitryNeural",
        "en_female": "en-US-JennyNeural",
        "en_male": "en-US-GuyNeural",
        "en_uk_female": "en-GB-SoniaNeural",
        "en_uk_male": "en-GB-RyanNeural",
    },
}

config_comment = """
Настройки TTS Edge (Microsoft Edge TTS).

Голоса по умолчанию:
- ru_female: ru-RU-SvetlanaNeural (русский женский)
- ru_male: ru-RU-DmitryNeural (русский мужской)
- en_female: en-US-JennyNeural (английский женский)
- en_male: en-US-GuyNeural (английский мужской)

Полный список голосов: edge-tts --list-voices
"""


def _get_edge_tts():
    try:
        import edge_tts
        return edge_tts
    except ImportError:
        _logger.error("Пакет edge-tts не установлен. Установите: pip install edge-tts")
        return None


def _detect_language(text: str) -> str:
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin = sum(1 for c in text if c.isalpha() and ord(c) < 128)
    return 'ru' if cyrillic >= latin else 'en'


def _synthesize_sync(text: str, voice: str, output_path: str):
    edge_tts = _get_edge_tts()
    if edge_tts is None:
        raise Exception("edge-tts не установлен")

    async def _do_save():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(asyncio.run, _do_save()).result()
        else:
            loop.run_until_complete(_do_save())
    except RuntimeError:
        asyncio.run(_do_save())


class EdgeTTS(FileWritingTTS):
    def __init__(self, voice: str):
        self._voice = voice

    def say_to_file(self, text: str, file_base_path: Optional[str] = None, **kwargs) -> TTSResultFile:
        file = create_disposable_tts_result_file(file_base_path, '.mp3')

        voice = kwargs.get('voice', self._voice)
        if voice is None:
            lang = _detect_language(text)
            voice = config['voices'].get(f'{lang}_female', config['default_voice'])

        _logger.debug("Синтезирую: voice=%s, text=%s", voice, text[:50])

        _synthesize_sync(text, voice, file.get_full_path())

        return file

    def get_settings_hash(self) -> str:
        return str(hash(self._voice))

    @property
    def meta(self) -> MetadataMapping:
        return {
            'edge.voice': self._voice,
        }


def create_file_tts(nxt, prev: Optional[FileWritingTTS], config_data: dict[str, Any], *args, **kwargs):
    if config_data.get('type') == 'edge':
        voice = config_data.get('voice', config['default_voice'])
        prev = prev or EdgeTTS(voice)

    return nxt(prev, config_data, *args, **kwargs)
