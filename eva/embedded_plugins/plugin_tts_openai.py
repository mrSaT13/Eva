"""
Плагин TTS на основе OpenAI API.
Требует API ключ. Поддерживает русский и английский.
Требует: pip install openai
"""

import os
from logging import getLogger
from typing import Optional, Any, TypedDict

from eva.face.abc import FileWritingTTS, TTSResultFile
from eva.face.tts_helpers import create_disposable_tts_result_file
from eva.utils.metadata import MetadataMapping

name = 'plugin_tts_openai'
version = '1.0.0'

_logger = getLogger(name)


class _Config(TypedDict):
    api_key: str
    base_url: str
    default_model: str
    default_voice: str


config: _Config = {
    "api_key": "",
    "base_url": "https://api.openai.com/v1",
    "default_model": "tts-1",
    "default_voice": "nova",
}

config_comment = """
Настройки TTS OpenAI.

Параметры:
- api_key       - API ключ OpenAI (или совместимого сервиса)
- base_url      - URL API (по умолчанию OpenAI, можно использовать совместимые сервисы)
- default_model - модель: "tts-1" (быстрая) или "tts-1-hd" (качественная)
- default_voice - голос: alloy, echo, fable, onyx, nova, shimmer

Русские голоса работают, но лучше всего подходит nova (женский) и echo (мужской).
"""


def _get_openai_client():
    try:
        from openai import OpenAI
    except ImportError:
        _logger.error("Пакет openai не установлен. Установите: pip install openai")
        return None

    if not config['api_key']:
        _logger.warning("API ключ OpenAI не установлен")
        return None

    return OpenAI(
        api_key=config['api_key'],
        base_url=config['base_url'],
    )


def _detect_language(text: str) -> str:
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin = sum(1 for c in text if c.isalpha() and ord(c) < 128)
    return 'ru' if cyrillic >= latin else 'en'


class OpenAITTS(FileWritingTTS):
    def __init__(self, model: str, voice: str):
        self._model = model
        self._voice = voice

    def say_to_file(self, text: str, file_base_path: Optional[str] = None, **kwargs) -> TTSResultFile:
        file = create_disposable_tts_result_file(file_base_path, '.mp3')

        client = _get_openai_client()
        if client is None:
            raise Exception("OpenAI TTS недоступен: не установлен пакет или нет API ключа")

        model = kwargs.get('model', self._model)
        voice = kwargs.get('voice', self._voice)

        _logger.debug("Синтезирую: model=%s, voice=%s, text=%s", model, voice, text[:50])

        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
        )

        response.stream_to_file(file.get_full_path())

        return file

    def get_settings_hash(self) -> str:
        return str(hash(f"{self._model}:{self._voice}"))

    @property
    def meta(self) -> MetadataMapping:
        return {
            'openai.model': self._model,
            'openai.voice': self._voice,
        }


def create_file_tts(nxt, prev: Optional[FileWritingTTS], config_data: dict[str, Any], *args, **kwargs):
    if config_data.get('type') == 'openai':
        model = config_data.get('model', config['default_model'])
        voice = config_data.get('voice', config['default_voice'])
        prev = prev or OpenAITTS(model, voice)

    return nxt(prev, config_data, *args, **kwargs)
