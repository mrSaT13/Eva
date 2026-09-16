from random import choice

from eva import VAApiExt

name = 'greetings'
version = '3.0.0'

config = {
    'phrases': {
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
    'who_are_you': {
        'ru': [
            "Я Ева — голосовой помощник. Я могу помочь с умным домом, таймерами, погодой, новостями и многим другим. Просто скажите, что вам нужно!",
            "Меня зовут Ева. Я умный голосовой ассистент. Управляю умным домом, ставлю таймеры, рассказываю погоду и новости. Чем могу помочь?",
            "Я Ева — ваш персональный голосовой помощник. Подключена к Home Assistant, знаю погоду, читаю новости. Спросите меня о чём угодно!",
        ],
        'en': [
            "I'm Eva — a voice assistant. I can help with smart home, timers, weather, news and more. Just tell me what you need!",
            "My name is Eva. I'm a smart voice assistant. I manage smart home, set timers, tell weather and news. How can I help?",
        ],
    },
    'what_can_you_do': {
        'ru': [
            "Я могу многое! Вот что я умею: управлять умным домом через Home Assistant — включать и выключать свет, регулировать температуру. Ставить таймеры. Рассказывать погоду. Читать новости из RSS лент. Искать информацию в Википедии. И просто поболтать! Попробуйте спросить: «поставь таймер на 5 минут» или «какая погода».",
            "Вот что я умею: голосовое управление умным домом — свет, климат, замки. Таймеры и напоминания. Погода в любом городе. Новости из ваших RSS лент. Поиск в Википедии. И конечно, простой разговор! Скажите «помощь» и я расскажу подробнее.",
        ],
        'en': [
            "I can do a lot! I manage smart home via Home Assistant — lights, temperature, locks. I set timers, tell weather, read news from RSS feeds, search Wikipedia, and just chat! Try asking: 'set timer for 5 minutes' or 'what's the weather'.",
        ],
    },
}


def _detect_lang(text: str) -> str:
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin = sum(1 for c in text if c.isalpha() and ord(c) < 128)
    return 'ru' if cyrillic >= latin else 'en'


def _respond(va: VAApiExt, text: str, key: str):
    lang = _detect_lang(text)
    phrases = config.get(key, {})
    options = phrases.get(lang, phrases.get('ru', []))
    va.say(choice(options))


def _greet(va: VAApiExt, text: str):
    _respond(va, text, 'phrases')


def _how_are_you(va: VAApiExt, text: str):
    _respond(va, text, 'how_are_you')


def _thanks(va: VAApiExt, text: str):
    _respond(va, text, 'thanks')


def _bye(va: VAApiExt, text: str):
    _respond(va, text, 'bye')


def _who_are_you(va: VAApiExt, text: str):
    _respond(va, text, 'who_are_you')


def _what_can_you_do(va: VAApiExt, text: str):
    _respond(va, text, 'what_can_you_do')


define_commands = {
    "привет|доброе утро|добрый день|здравствуй|hello|hi|hey|good morning": _greet,
    "как дела|как ты|как поживаешь|что нового|how are you|how do you do": _how_are_you,
    "спасибо|благодарю|thanks|thank you|thank": _thanks,
    "пока|до свидания|прощай|до встречи|bye|goodbye|see you": _bye,
    "кто ты|как тебя зовут|что ты за_assистент|расскажи о себе|who are you|what's your name": _who_are_you,
    "что ты умеешь|чем можешь помочь|что можешь|помощь|help|what can you do": _what_can_you_do,
}
