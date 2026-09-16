"""
Плагин таймера Eva.

Поддерживает:
- Голосовые команды: "таймер", "поставь таймер на 5 минут"
- Диалоговый режим: спрашивает время если не указано
- Парсинг: минуты, часы, секунды (цифры и прописью)
- Настройки: звуковое оповещение, текст, уведомления
"""

import asyncio
import re
from logging import getLogger
from time import sleep
from typing import TypedDict, Optional

from eva import VAApiExt
from eva.brain.abc import OutputChannelNotFoundError
from eva.plugin_loader.file_patterns import pick_random_file
from eva.plugin_loader.magic_plugin import MagicPlugin

_logger = getLogger('timer')

_WORD_TO_NUM = {
    'ноль': 0, 'один': 1, 'одна': 1, 'одну': 1, 'два': 2, 'две': 2, 'три': 3,
    'четыре': 4, 'пять': 5, 'шесть': 6, 'семь': 7, 'восемь': 8, 'девять': 9,
    'десять': 10, 'одиннадцать': 11, 'двенадцать': 12, 'тринадцать': 13,
    'четырнадцать': 14, 'пятнадцать': 15, 'шестнадцать': 16, 'семнадцать': 17,
    'восемнадцать': 18, 'девятнадцать': 19, 'двадцать': 20, 'тридцать': 30,
    'сорок': 40, 'пятьдесят': 50, 'шестьдесят': 60, 'семьдесят': 70,
    'восемьдесят': 80, 'девяносто': 90, 'сто': 100, 'двести': 200, 'триста': 300,
}


def _parse_number(text: str) -> Optional[int]:
    text = text.strip().lower()

    if text.isdigit():
        return int(text)

    parts = text.split()
    result = 0
    for part in parts:
        if part in _WORD_TO_NUM:
            val = _WORD_TO_NUM[part]
            if val >= 20:
                result += val
            else:
                if result == 0:
                    result = val
                else:
                    result += val
    return result if result > 0 else None


_TIME_UNITS = r'(час[аовеу]?|минут[ауые]?|мин(?:утк[уеи])?|секунд[ауые]?|сек)'

def _parse_time(text: str) -> Optional[int]:
    text = text.strip().lower()
    text = re.sub(r'^(на|через)\s+', '', text)

    m = re.match(rf'(\d+)\s*{_TIME_UNITS}', text)
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        if unit.startswith('час'):
            return num * 3600
        elif unit.startswith('мин'):
            return num * 60
        elif unit.startswith('сек'):
            return num

    m = re.match(rf'(\S+)\s*{_TIME_UNITS}', text)
    if m:
        num = _parse_number(m.group(1))
        if num is not None:
            unit = m.group(2)
            if unit.startswith('час'):
                return num * 3600
            elif unit.startswith('мин'):
                return num * 60
            elif unit.startswith('сек'):
                return num

    m = re.match(rf'^{_TIME_UNITS}$', text)
    if m:
        unit = m.group(1)
        if unit.startswith('час'):
            return 3600
        elif unit.startswith('мин'):
            return 60
        elif unit.startswith('сек'):
            return 1

    m = re.match(r'(\d+)', text)
    if m:
        return int(m.group(1)) * 60

    num = _parse_number(text)
    if num is not None:
        return num * 60

    return None


def _format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} секунд"
    elif seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        if secs == 0:
            return f"{mins} минут"
        return f"{mins} минут {secs} секунд"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        if mins == 0:
            return f"{hours} часов"
        return f"{hours} часов {mins} минут"


class TimerPlugin(MagicPlugin):
    name = 'plugin_timer'
    version = '8.0.0'

    class _Config(TypedDict):
        wavRepeatTimes: int
        wavPath: str
        notify_sound: bool
        notify_text: str
        notify_services: bool

    config: _Config = {
        'wavRepeatTimes': 2,
        'wavPath': '{eva_path}/embedded_plugins/media/timer.wav',
        'notify_sound': True,
        'notify_text': 'Таймер сработал! Прошло {time}',
        'notify_services': False,
    }

    config_comment = """
Настройки таймера.

Параметры:
- wavPath          - путь к звуку таймера
- wavRepeatTimes   - количество повторений звука
- notify_sound     - воспроизводить звук при срабатывании
- notify_text      - текст оповещения ({time} = время)
- notify_services  - отправлять уведомления в подключённые сервисы
"""

    def __init__(self) -> None:
        super().__init__()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._active_timers: list[dict] = []
        self._stopwatches: list[dict] = []

    async def init(self, *_args, **_kwargs):
        self._loop = asyncio.get_running_loop()

    def define_commands(self, *_args, **_kwargs):
        return {
            "таймер|тайгер": self._handle_timer,
            "отмени таймер|удали таймер|останови таймер|выключи таймер|стоп таймер": self._handle_cancel_timer,
            "секундомер|секундамер|хронометр": self._handle_stopwatch,
            "останови секундомер|стоп секундомер|выключи секундомер": self._handle_stop_stopwatch,
            "продолжи секундомер|продолжи хронометр": self._handle_resume_stopwatch,
            "сколько таймеров|покажи таймеры|какие таймеры|таймеры|список таймеров": self._handle_list_timers,
            "сколько секундомеров|покажи секундомеры|какие секундомеры|секундомеры|список секундомеров": self._handle_list_stopwatches,
        }

    def _handle_timer(self, va: VAApiExt, phrase: str):
        if phrase.strip():
            seconds = _parse_time(phrase)
            if seconds is not None:
                self._set_timer_real(va, seconds)
                return
            va.say("Не поняла время. Скажите, например: на пять минут, через тридцать секунд, на два часа")
            answer = yield "На сколько поставить таймер?"
            if answer:
                seconds = _parse_time(answer)
                if seconds is not None:
                    self._set_timer_real(va, seconds)
                    return
                va.say("Не поняла время. Попробуйте ещё раз.")
            return

        answer = yield "На сколько поставить таймер?"
        if answer:
            seconds = _parse_time(answer)
            if seconds is not None:
                self._set_timer_real(va, seconds)
                return
            va.say("Не поняла время. Попробуйте сказать: пять минут, тридцать секунд, два часа.")

    def _set_timer_real(self, va: VAApiExt, seconds: int):
        import uuid
        duration_text = _format_duration(seconds)
        timer_id = str(uuid.uuid4())[:8]

        timer_info = {
            "id": timer_id,
            "duration": seconds,
            "remaining": seconds,
            "created": __import__('time').time(),
            "message": duration_text,
        }
        self._active_timers.append(timer_info)

        def done_interaction(va: VAApiExt):
            self._active_timers = [t for t in self._active_timers if t["id"] != timer_id]
            if self.config.get('notify_sound', True):
                try:
                    for i in range(self.config.get('wavRepeatTimes', 2)):
                        va.play_audio(pick_random_file(self.config['wavPath']))
                        sleep(0.2)
                except OutputChannelNotFoundError:
                    va.say("Бип бип!")

            custom_text = self.config.get('notify_text', 'Таймер сработал! Прошло {time}')
            message = custom_text.replace('{time}', duration_text)
            va.say(message)

            if self.config.get('notify_services', False):
                self._notify_services(duration_text)

        async def timer_task():
            await asyncio.sleep(seconds)
            try:
                await self._loop.run_in_executor(
                    None,
                    va.submit_active_interaction,
                    done_interaction
                )
            except Exception:
                _logger.exception("Timer error")

        if self._loop is None:
            raise Exception("Timer set before init()")

        self._loop.call_soon_threadsafe(self._loop.create_task, timer_task())
        va.say(f"Таймер поставлен на {duration_text}")

    def _notify_services(self, duration_text: str):
        _logger.info("Timer notification: %s", duration_text)

    def _handle_cancel_timer(self, va: VAApiExt, _phrase: str):
        if not self._active_timers:
            va.say("Нет активных таймеров")
            return
        count = len(self._active_timers)
        self._active_timers.clear()
        if count == 1:
            va.say("Таймер отменён")
        else:
            va.say(f"Отменено таймеров: {count}")

    def _handle_stopwatch(self, va: VAApiExt, phrase: str):
        label = phrase.strip() or "Секундомер"
        import uuid, time as _time
        sw_id = str(uuid.uuid4())[:8]
        self._stopwatches.append({
            "id": sw_id,
            "started": _time.time(),
            "label": label,
            "paused": False,
            "paused_at": 0,
            "elapsed_total": 0,
        })
        va.say(f"Секундомер «{label}» запущен")

    def _handle_stop_stopwatch(self, va: VAApiExt, _phrase: str):
        if not self._stopwatches:
            va.say("Нет активных секундомеров")
            return
        count = len(self._stopwatches)
        self._stopwatches.clear()
        if count == 1:
            va.say("Секундомер остановлен")
        else:
            va.say(f"Остановлено секундомеров: {count}")

    def _handle_resume_stopwatch(self, va: VAApiExt, _phrase: str):
        import time as _time
        paused = [s for s in self._stopwatches if s["paused"]]
        if not paused:
            va.say("Нет секундомеров на паузе")
            return
        for sw in paused:
            paused_duration = _time.time() - sw["paused_at"]
            sw["elapsed_total"] += paused_duration
            sw["started"] += paused_duration
            sw["paused"] = False
        va.say("Секундомер продолжен")

    def _handle_list_timers(self, va: VAApiExt, _phrase: str):
        if not self._active_timers:
            va.say("У вас нет установленных таймеров")
            return
        import time as _time
        now = _time.time()
        lines = []
        for t in self._active_timers:
            remaining = max(0, t["duration"] - (now - t["created"]))
            lines.append(f"«{t['message']}» — осталось {_format_duration(int(remaining))}")
        va.say(f"Активных таймеров: {len(self._active_timers)}. " + ". ".join(lines))

    def _handle_list_stopwatches(self, va: VAApiExt, _phrase: str):
        if not self._stopwatches:
            va.say("У вас нет запущенных секундомеров")
            return
        import time as _time
        now = _time.time()
        lines = []
        for sw in self._stopwatches:
            if sw["paused"]:
                elapsed = int(sw["elapsed_total"] + (sw["paused_at"] - sw["started"]))
                lines.append(f"«{sw['label']}» — {_format_duration(elapsed)}, на паузе")
            else:
                elapsed = int(now - sw["started"])
                lines.append(f"«{sw['label']}» — {_format_duration(elapsed)}")
        va.say(f"Активных секундомеров: {len(self._stopwatches)}. " + ". ".join(lines))

    def register_fastapi_endpoints(self, router, pm, *_args, **_kwargs):
        from fastapi import APIRouter
        from pydantic import BaseModel

        r: APIRouter = router
        plugin = self

        class TimerConfigUpdate(BaseModel):
            notify_sound: Optional[bool] = None
            notify_text: Optional[str] = None
            notify_services: Optional[bool] = None

        @r.get('/config')
        async def get_timer_config():
            return {
                'notify_sound': plugin.config.get('notify_sound', True),
                'notify_text': plugin.config.get('notify_text', 'Таймер сработал! Прошло {time}'),
                'notify_services': plugin.config.get('notify_services', False),
            }

        @r.patch('/config')
        async def update_timer_config(req: TimerConfigUpdate):
            if req.notify_sound is not None:
                plugin.config['notify_sound'] = req.notify_sound
            if req.notify_text is not None:
                plugin.config['notify_text'] = req.notify_text
            if req.notify_services is not None:
                plugin.config['notify_services'] = req.notify_services
            return {"status": "ok"}

        @r.get('/active')
        async def get_active_timers():
            import time as _time
            now = _time.time()
            result = []
            for t in plugin._active_timers:
                elapsed = now - t["created"]
                remaining = max(0, t["duration"] - elapsed)
                result.append({
                    "id": t["id"],
                    "duration": t["duration"],
                    "remaining": int(remaining),
                    "message": t["message"],
                    "active": remaining > 0,
                })
            return result

        class StopwatchRequest(BaseModel):
            label: Optional[str] = None

        @r.post('/stopwatch/start')
        async def start_stopwatch(req: StopwatchRequest):
            import time as _time, uuid
            sw_id = str(uuid.uuid4())[:8]
            sw = {
                "id": sw_id,
                "started": _time.time(),
                "label": req.label or "Секундомер",
                "paused": False,
                "paused_at": 0,
                "elapsed_total": 0,
            }
            plugin._stopwatches.append(sw)
            return {"id": sw_id, "status": "started"}

        @r.post('/stopwatch/{sw_id}/stop')
        async def stop_stopwatch(sw_id: str):
            plugin._stopwatches = [s for s in plugin._stopwatches if s["id"] != sw_id]
            return {"status": "stopped"}

        @r.post('/stopwatch/{sw_id}/pause')
        async def pause_stopwatch(sw_id: str):
            import time as _time
            for sw in plugin._stopwatches:
                if sw["id"] == sw_id:
                    if not sw["paused"]:
                        sw["paused"] = True
                        sw["paused_at"] = _time.time()
                    else:
                        paused_duration = _time.time() - sw["paused_at"]
                        sw["elapsed_total"] += paused_duration
                        sw["started"] += paused_duration
                        sw["paused"] = False
                    return {"status": "paused" if sw["paused"] else "resumed"}
            return {"error": "not found"}

        @r.get('/stopwatch/active')
        async def get_active_stopwatches():
            import time as _time
            now = _time.time()
            result = []
            for sw in plugin._stopwatches:
                if sw["paused"]:
                    elapsed = sw["elapsed_total"] + (sw["paused_at"] - sw["started"])
                else:
                    elapsed = now - sw["started"]
                result.append({
                    "id": sw["id"],
                    "label": sw["label"],
                    "elapsed": int(elapsed),
                    "paused": sw["paused"],
                })
            return result

        @r.get('/status')
        async def get_timer_status():
            import time as _time
            now = _time.time()
            timers = []
            for t in plugin._active_timers:
                elapsed = now - t["created"]
                remaining = max(0, t["duration"] - elapsed)
                timers.append({
                    "id": t["id"],
                    "duration": t["duration"],
                    "remaining": int(remaining),
                    "message": t["message"],
                    "active": remaining > 0,
                })
            stopwatches = []
            for sw in plugin._stopwatches:
                if sw["paused"]:
                    elapsed = sw["elapsed_total"] + (sw["paused_at"] - sw["started"])
                else:
                    elapsed = now - sw["started"]
                stopwatches.append({
                    "id": sw["id"],
                    "label": sw["label"],
                    "elapsed": int(elapsed),
                    "paused": sw["paused"],
                })
            return {"timers": timers, "stopwatches": stopwatches}
