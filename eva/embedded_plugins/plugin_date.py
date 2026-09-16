from datetime import datetime

from eva import VAApiExt

name = 'skill_date'
version = '2.1.0'

_DAY_OF_WEEK_RU = (
    "понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"
)

_DAY_OF_WEEK_EN = (
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
)

_MONTHS_RU = (
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
)

_MONTHS_EN = (
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
)


def _detect_lang(text: str) -> str:
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin = sum(1 for c in text if c.isalpha() and ord(c) < 128)
    return 'ru' if cyrillic >= latin else 'en'


def _play_date(va: VAApiExt, phrase: str):
    now = datetime.now()
    lang = _detect_lang(phrase)

    if lang == 'en':
        day = _DAY_OF_WEEK_EN[now.weekday()]
        month = _MONTHS_EN[now.month - 1]
        va.say(f"Today is {day}, {month} {now.day}, {now.year}")
    else:
        day = _DAY_OF_WEEK_RU[now.weekday()]
        month = _MONTHS_RU[now.month - 1]
        day_num = now.day
        if day_num == 1:
            day_str = "первое"
        elif day_num == 2:
            day_str = "второе"
        elif day_num == 3:
            day_str = "третье"
        else:
            day_str = str(day_num)
        va.say(f"Сегодня {day}, {day_str} {month}")


define_commands = {"дата|date|what's the date|what date|today": _play_date}
