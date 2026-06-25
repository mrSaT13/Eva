import datetime

from langchain_core.tools import tool

from eva.plugin_loader.magic_plugin import operation

name = 'ai_skill_datetime'
version = '0.1.0'

MONTHS_RU = [
    '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
]

WEEKDAYS_RU = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']


@operation('lc_tools')
@tool(parse_docstring=True)
def get_date_and_time() -> str:
    """
    Возвращает текущие дату и время. Используй когда пользователь спрашивает время или дату.
    """
    now = datetime.datetime.now()
    weekday = WEEKDAYS_RU[now.weekday()]
    month = MONTHS_RU[now.month]
    return f"Сейчас {weekday}, {now.day} {month} {now.year} года, {now.strftime('%H:%M')}."
