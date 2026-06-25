"""
Плагин для подключения к LM Studio (OpenAI-compatible API).
LM Studio предоставляет локальный сервер с OpenAI-compatible API.
"""

from typing import Any, Optional, Callable

from langchain_core.language_models import BaseChatModel

name = 'llm_lmstudio'
version = '1.0.0'

config: dict[str, Any] = {
    'base_url': 'http://127.0.0.1:1234/v1',
    'model': 'local-model',
    'temperature': 0.7,
    'api_key': 'lm-studio',
}

config_comment = """
Настройки подключения к LM Studio.

LM Studio - приложение для запуска LLM локально.
Скачать: https://lmstudio.ai/

Параметры:
- base_url     - URL сервера LM Studio (по умолчанию http://localhost:1234/v1)
- model        - название модели (в LM Studio это "local-model" или имя загруженной модели)
- temperature  - температура генерации (0.0-1.0)
- api_key      - API ключ (LM Studio не требует реального ключа, можно оставить lm-studio)

Как настроить:
1. Запустите LM Studio
2. Загрузите любую модель
3. Запустите локальный сервер (вкладка "Local Server")
4. Укажите URL сервера в настройках (обычно http://localhost:1234/v1)
"""


def get_lc_llm(
        nxt: Callable,
        llm: Optional[BaseChatModel],
        llm_settings: dict[str, Any],
        *args, **kwargs
) -> Optional[BaseChatModel]:
    if llm is None and llm_settings.get('type') == 'lmstudio':
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            from langchain_community.chat_models import ChatOpenAI

        settings = {
            'base_url': llm_settings.get('base_url', config['base_url']),
            'model': llm_settings.get('model', config['model']),
            'temperature': llm_settings.get('temperature', config['temperature']),
            'api_key': llm_settings.get('api_key', config['api_key']),
        }

        llm = ChatOpenAI(**settings)

    return nxt(llm, llm_settings, *args, **kwargs)
