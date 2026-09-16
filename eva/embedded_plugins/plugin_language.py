import re
from typing import Optional

name = 'language'
version = '1.0.0'

_CYRILLIC_RANGE = re.compile(r'[\u0400-\u04FF]')
_LATIN_RANGE = re.compile(r'[a-zA-Z]')


def detect_language(text: str) -> str:
    text_lower = text.lower().strip()

    cyrillic_count = len(_CYRILLIC_RANGE.findall(text_lower))
    latin_count = len(_LATIN_RANGE.findall(text_lower))

    if cyrillic_count > latin_count:
        return 'ru'
    elif latin_count > cyrillic_count:
        return 'en'
    else:
        return 'ru'


def translate_key(key: str, lang: str) -> str:
    translations = {
        'greeting': {
            'ru': [
                "Привет! Я Ева, чем могу помочь?",
                "Рада тебя слышать!",
                "Добрый день! Готова помочь!",
            ],
            'en': [
                "Hi! I'm Eva, how can I help you?",
                "Nice to hear from you!",
                "Hello! Ready to help!",
            ],
        },
        'how_are_you': {
            'ru': [
                "У меня всё отлично! Спасибо, что спрашиваешь.",
                "Прекрасно! Работаю на полную.",
                "Всё хорошо, готова к работе!",
                "Отлично! Чем могу помочь?",
            ],
            'en': [
                "I'm doing great! Thanks for asking.",
                "Fantastic! Working at full capacity.",
                "All good, ready to work!",
                "Excellent! How can I help?",
            ],
        },
        'thanks': {
            'ru': [
                "Пожалуйста! Обращайся ещё.",
                "Рада помочь!",
                "Не за что! Всегда рада помочь.",
            ],
            'en': [
                "You're welcome! Feel free to ask again.",
                "Happy to help!",
                "No problem! Always glad to help.",
            ],
        },
        'bye': {
            'ru': [
                "До встречи! Если что — я здесь.",
                "Пока! Обращайся в любое время.",
                "До свидания! Хорошего дня!",
            ],
            'en': [
                "See you! I'm here if you need anything.",
                "Bye! Reach out anytime.",
                "Goodbye! Have a great day!",
            ],
        },
        'unknown': {
            'ru': [
                "Не совсем поняла, можешь перефразировать?",
                "Хм, не уверена что поняла. Попробуй ещё раз.",
            ],
            'en': [
                "I didn't quite understand, could you rephrase?",
                "Hmm, not sure I got that. Try again.",
            ],
        },
        'time': {
            'ru': ["Сейчас {time}"],
            'en': ["It's {time} now"],
        },
        'date': {
            'ru': ["Сегодня {date}"],
            'en': ["Today is {date}"],
        },
    }

    lang_translations = translations.get(key, {})
    options = lang_translations.get(lang, lang_translations.get('ru', [key]))

    from random import choice
    return choice(options)
