"""
Конструктор навыков Eva.

Позволяет через веб-интерфейс создавать «навыки» (skills) — голосовые команды,
которые при срабатывании выполняют цепочку действий и озвучивают реакцию.

Структура навыка (JSON):
{
    "id": "abc123",
    "intent": "Home.TurnOnLight",       # точечная нотация для группировки
    "name": "Включи свет",
    "description": "Включает свет в комнате через HA",
    "enabled": true,
    "phrases": ["включи свет", "включи свет в {room}"],   # {slot} — переменные
    "matchMode": "contains",             # contains | exact | regex
    "slots": [                           # типизированные параметры
        {"name": "room", "type": "list", "required": false,
         "values": ["кухня","спальня"], "defaultValue": "зал", "examples": []}
    ],
    "actions": [                         # цепочка действий
        {"type": "ha_service", "config": {"service": "light.turn_on",
                                          "entity_id": "light.{room}"}}
    ],
    "reactions": [                       # возможные ответы
        {"text": "Включаю свет в {room}", "tts": "Включаю свет в {room}!"}
    ],
    "session": {"enabled": false, "ttl": 60},
    "category": "home"
}

Поддерживаемые типы действий:
- text      — озвучить текст (text)
- http      — HTTP-запрос (method, url, headers, body) с подстановкой {slots}
- plugin    — вызов функции подключённого плагина (plugin, function, args)
- ha_service — Home Assistant service (entity_id, service, data)
- timer     — таймер (seconds, message)
- llm       — языковая модель (prompt, system)
- macro     — последовательность других навыков (skills — массив id)

REST API:
- GET  /api/skills/list       — список навыков
- POST /api/skills/save       — сохранить массив навыков
- POST /api/skills/test/{id}  — тест навыка (выполняет действия имитационно)
- POST /api/skills/run        — найти и выполнить навык по фразе ({"text": "..."})
- GET  /api/skills/match      — найти навык по фразе без выполнения
"""

import json
import os
import re
import time
import asyncio
import logging
from typing import Any, Optional
from datetime import datetime

from eva.plugin_loader.magic_plugin import MagicPlugin, operation, after, step_name
from eva.plugin_loader.run_operation import call_all_as_wrappers
from eva.embedded_plugins.dialogue_engine import get_engine, DialogueEngine

_logger = logging.getLogger('eva_skills')


class _SkillMatchContext:
    """Контекст, перехватывающий неизвестные команды и ищущий совпадение в скиллах."""
    __slots__ = ('_plugin', '_next')

    def __init__(self, plugin: 'EvaSkillsPlugin', next_ctx):
        self._plugin = plugin
        self._next = next_ctx

    def handle_command(self, va, message):
        text = message.get_text()
        lower = text.lower().strip()

        # Ищем новый навык по имени
        skill_name = None
        for prefix in ['запусти навык ', 'выполни навык ', 'навык ', 'skill run ']:
            if lower.startswith(prefix):
                skill_name = lower[len(prefix):].strip()
                break
        if skill_name:
            for s in self._plugin.config.get('skills', []):
                if not s.get('enabled', True):
                    continue
                sname = s.get('name', '').lower()
                sintent = s.get('intent', '').lower()
                if skill_name in sname or skill_name in sintent or sname.startswith(skill_name):
                    return self._plugin._start_dialogue_skill(va, s)

        # Обычное совпадение по фразам
        match = self._plugin.match_skill(text)
        if match:
            skill, phrase, slots = match
            if skill.get('type') == 'dialogue':
                return self._plugin._start_dialogue_skill(va, skill)
            self._plugin._handle_skill(va, text, skill)
            return self._next

        return self._next.handle_command(va, message) if self._next else None


class EvaSkillsPlugin(MagicPlugin):
    name = 'eva_skills'
    version = '1.0.0'

    config: dict[str, Any] = {
        'skills': [],
    }

    config_comment = """
Конструктор навыков Eva.

Навыки создаются через веб-интерфейс (Настройки → Навыки → Создать навык)
и автоматически регистрируются как голосовые команды.

Параметры:
- skills — массив навыков (см. формат в начале файла)
"""

    @operation('create_root_context')
    @after('load_commands')
    @step_name('skill_match_fallback')
    def create_root_context(self, nxt, prev, *args, **kwargs):
        return nxt(_SkillMatchContext(self, prev), *args, **kwargs)

    def __init__(self):
        super().__init__()
        self._brain: Any = None

    # ------------------------------------------------------------------
    # Хранилище
    # ------------------------------------------------------------------

    def _get_skills_path(self) -> str:
        home = os.environ.get('EVA_HOME', os.path.expanduser('~/eva'))
        return os.path.join(home, 'skills.json')

    def _load_skills(self):
        path = self._get_skills_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.config['skills'] = json.load(f)
                _logger.info("Загружено %d навыков из %s", len(self.config['skills']), path)
            except Exception as e:
                _logger.error("Ошибка загрузки навыков: %s", e)
                self.config['skills'] = []
        else:
            self.config['skills'] = self.config.get('skills') or []

        if not self.config['skills']:
            self.config['skills'] = self._default_skills()
            self._save_skills()
            _logger.info("Созданы шаблонные навыки по умолчанию (%d)", len(self.config['skills']))

    def _default_skills(self) -> list[dict]:
        import uuid
        def uid():
            return str(uuid.uuid4())[:8]
        return [
            {
                "id": uid(), "intent": "Timer.Set", "name": "Поставить таймер",
                "description": "Устанавливает таймер на заданное количество времени",
                "enabled": True, "matchMode": "contains", "category": "system",
                "phrases": ["таймер на {time}", "поставь таймер на {time}", "поставить таймер на {time}"],
                "slots": [{"name": "time", "type": "string", "required": True, "examples": ["5 минут", "час", "30 секунд"]}],
                "actions": [{"type": "timer", "config": {"seconds": "{time}"}}],
                "reactions": [{"text": "Таймер поставлен на {time}", "tts": "Таймер поставлен на {time}"}],
                "session": {"enabled": False, "ttl": 60},
            },
            {
                "id": uid(), "intent": "Timer.Cancel", "name": "Отменить таймер",
                "description": "Отменяет все активные таймеры",
                "enabled": True, "matchMode": "contains", "category": "system",
                "phrases": ["отмени таймер", "удали таймер", "останови таймер", "выключи таймер"],
                "slots": [],
                "actions": [{"type": "text", "config": {"text": "Таймер отменён"}}],
                "reactions": [{"text": "Таймер отменён", "tts": "Таймер отменён"}],
                "session": {"enabled": False, "ttl": 60},
            },
            {
                "id": uid(), "intent": "Stopwatch.Start", "name": "Запустить секундомер",
                "description": "Запускает секундомер",
                "enabled": True, "matchMode": "contains", "category": "system",
                "phrases": ["секундомер", "запусти секундомер", "включи секундомер", "хронометр"],
                "slots": [{"name": "label", "type": "string", "required": False, "defaultValue": "Секундомер", "examples": ["тренировка", "готовка"]}],
                "actions": [{"type": "text", "config": {"text": "Секундомер запущен"}}],
                "reactions": [{"text": "Секундомер запущен", "tts": "Секундомер запущен"}],
                "session": {"enabled": False, "ttl": 60},
            },
            {
                "id": uid(), "intent": "Stopwatch.Stop", "name": "Остановить секундомер",
                "description": "Останавливает все активные секундомеры",
                "enabled": True, "matchMode": "contains", "category": "system",
                "phrases": ["останови секундомер", "стоп секундомер", "выключи секундомер"],
                "slots": [],
                "actions": [{"type": "text", "config": {"text": "Секундомер остановлен"}}],
                "reactions": [{"text": "Секундомер остановлен", "tts": "Секундомер остановлен"}],
                "session": {"enabled": False, "ttl": 60},
            },
            {
                "id": uid(), "intent": "Weather.Get", "name": "Узнать погоду",
                "description": "Показывает текущую погоду в городе",
                "enabled": True, "matchMode": "contains", "category": "info",
                "phrases": ["погода", "какая погода", "прогноз погоды", "погода в {city}"],
                "slots": [{"name": "city", "type": "string", "required": False, "defaultValue": "", "examples": ["Москва", "Санкт-Петербург"]}],
                "actions": [{"type": "text", "config": {"text": "Узнаю погоду..."}}],
                "reactions": [{"text": "Вот данные о погоде", "tts": "Вот данные о погоде"}],
                "session": {"enabled": False, "ttl": 60},
            },
            {
                "id": uid(), "intent": "News.Get", "name": "Последние новости",
                "description": "Читает последние новости из RSS лент",
                "enabled": True, "matchMode": "contains", "category": "info",
                "phrases": ["новости", "что нового", "свежие новости", "последние новости", "что в мире"],
                "slots": [],
                "actions": [{"type": "text", "config": {"text": "Загружаю новости..."}}],
                "reactions": [{"text": "Вот последние новости", "tts": "Вот последние новости"}],
                "session": {"enabled": False, "ttl": 60},
            },
            {
                "id": uid(), "intent": "Wiki.Search", "name": "Поиск в Википедии",
                "description": "Ищет информацию в Википедии",
                "enabled": True, "matchMode": "contains", "category": "info",
                "phrases": ["вики {query}", "википедия {query}", "найди в википедии {query}", "что такое {query}"],
                "slots": [{"name": "query", "type": "string", "required": True, "examples": ["квантовая физика", "Эйфелева башня"]}],
                "actions": [{"type": "text", "config": {"text": "Ищу в Википедии..."}}],
                "reactions": [{"text": "Нашла в Википедии", "tts": "Нашла в Википедии"}],
                "session": {"enabled": False, "ttl": 60},
            },
            {
                "id": uid(), "intent": "Time.Current", "name": "Текущее время",
                "description": "Показывает текущее время и дату",
                "enabled": True, "matchMode": "contains", "category": "info",
                "phrases": ["время", "который час", "сколько времени", "текущее время", "дата", "какое сегодня число"],
                "slots": [],
                "actions": [{"type": "text", "config": {"text": "{datetime}"}}],
                "reactions": [{"text": "Сейчас {time}", "tts": "Сейчас {time}"}],
                "session": {"enabled": False, "ttl": 60},
            },
        ]

    def _save_skills(self) -> bool:
        path = self._get_skills_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.config['skills'], f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            _logger.error("Ошибка сохранения навыков: %s", e)
            return False

    # ------------------------------------------------------------------
    # Утилиты парсинга
    # ------------------------------------------------------------------

    @staticmethod
    def extract_slot_names(phrase: str) -> list[str]:
        return list({m.group(1) for m in re.finditer(r'\{(\w+)\}', phrase)})

    def parse_phrase_to_slots(
        self,
        phrase: str,
        template: str,
        slots: list[dict],
    ) -> dict[str, str]:
        """Парсит фразу пользователя и возвращает пары {slot_name: value}."""
        result: dict[str, str] = {}

        if '{' not in template:
            # Без слотов — просто проверяем вхождение
            if template.lower() in phrase.lower():
                return {}
            return {}

        # Экранируем спецсимволы regex, кроме {slot}
        re_text = ''
        for part in re.split(r'(\{\w+\})', template):
            if part.startswith('{') and part.endswith('}'):
                re_text += '(.+?)'
            else:
                re_text += re.escape(part)

        m = re.fullmatch(re_text, phrase, re.IGNORECASE | re.DOTALL)
        names = self.extract_slot_names(template)

        if m:
            for i, name in enumerate(names):
                val = (m.group(i + 1) or '').strip()
                if val:
                    result[name] = val
        else:
            # Фоллбэк contains — для каждого слота оставляем заглушку
            for n in names:
                result[n] = ''

        # Валидация по типам + значения по умолчанию
        for s in slots:
            name = s.get('name', '')
            if not name:
                continue
            if not result.get(name) and s.get('defaultValue') is not None:
                result[name] = str(s['defaultValue'])

            val = result.get(name, '')
            stype = s.get('type', 'string')

            if stype == 'list' and val and s.get('values'):
                lower = val.lower()
                best = None
                for v in s['values']:
                    if v.lower() == lower:
                        best = v
                        break
                if not best:
                    for v in s['values']:
                        if v.lower() in lower or lower in v.lower():
                            best = v
                            break
                if best:
                    result[name] = best

            elif stype == 'number' and val:
                cleaned = re.sub(r'[^\d,.\-]', '', val).replace(',', '.')
                try:
                    n = float(cleaned)
                    result[name] = str(int(n) if n.is_integer() else n)
                except ValueError:
                    pass

            elif stype == 'bool' and val:
                yes = ['да', 'включи', 'включить', 'yes', 'on', 'true']
                no = ['нет', 'выключи', 'выключить', 'off', 'false']
                low = val.lower()
                if any(w in low for w in yes):
                    result[name] = 'true'
                elif any(w in low for w in no):
                    result[name] = 'false'

            elif stype == 'date' and val:
                # Простая обработка: "завтра", "через час" — оставляем как есть
                pass

        return result

    @staticmethod
    def resolve_template(text: str, slots: dict[str, str], extra: Optional[dict[str, str]] = None) -> str:
        if not text:
            return text
        vars_ = dict(slots)
        if extra:
            vars_.update(extra)

        # Системные переменные
        now = datetime.now()
        sys_vars = {
            'time': now.strftime('%H:%M'),
            'date': now.strftime('%d.%m.%Y'),
            'datetime': now.strftime('%d.%m.%Y %H:%M'),
            'hour': str(now.hour),
            'minute': str(now.minute),
            'phrase': '',  # заполняется отдельно
            'last_response': '',
            'user_text': '',
        }
        sys_vars.update(vars_)

        def repl(m):
            key = m.group(1)
            return str(sys_vars.get(key, m.group(0)))

        return re.sub(r'\{(\w+)\}', repl, text)

    # ------------------------------------------------------------------
    # Поиск подходящего навыка
    # ------------------------------------------------------------------

    def match_skill(self, text: str) -> Optional[tuple[dict, str, dict[str, str]]]:
        """Ищет навык, подходящий под фразу.

        Возвращает (skill, matched_phrase, slots) или None.
        """
        text_low = text.lower().strip()
        best: Optional[tuple[float, dict, str, dict[str, str]]] = None

        for skill in self.config.get('skills', []):
            if not skill.get('enabled', True):
                continue
            for phrase in skill.get('phrases', []):
                slots = self.parse_phrase_to_slots(text, phrase, skill.get('slots', []))
                # Оценка совпадения
                if not phrase or '{' not in phrase:
                    # Простое вхождение
                    if phrase.lower() in text_low:
                        score = len(phrase)
                        if best is None or score > best[0]:
                            best = (score, skill, phrase, {})
                    continue

                # Слотовая фраза — парсим regex
                re_text = ''
                for part in re.split(r'(\{\w+\})', phrase):
                    if part.startswith('{') and part.endswith('}'):
                        re_text += '(.+?)'
                    else:
                        re_text += re.escape(part)

                if re.fullmatch(re_text, text, re.IGNORECASE | re.DOTALL):
                    # Чем короче фраза-шаблон (но больше фиксированной части),
                    # тем выше приоритет.
                    fixed = sum(len(p) for p in re.split(r'\{\w+\}', phrase) if p)
                    score = fixed + len(slots) * 0.1
                    if best is None or score > best[0]:
                        best = (score, skill, phrase, slots)

        if best is None:
            return None
        return best[1], best[2], best[3]

    # ------------------------------------------------------------------
    # Исполнение действий
    # ------------------------------------------------------------------

    async def _http_action(self, action: dict, slots: dict[str, str]) -> str:
        method = action.get('method', 'GET').upper()
        url = self.resolve_template(action.get('url', ''), slots)
        headers_str = self.resolve_template(action.get('headers', '{}'), slots)
        body_str = self.resolve_template(action.get('body', ''), slots)

        try:
            headers = json.loads(headers_str) if headers_str.strip() else {}
        except Exception:
            headers = {}

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                if method == 'GET':
                    resp = await client.get(url, headers=headers)
                else:
                    body = None
                    if body_str.strip():
                        try:
                            body = json.loads(body_str)
                        except Exception:
                            body = body_str
                    resp = await client.request(method, url, headers=headers, json=body if isinstance(body, (dict, list)) else None, content=body if isinstance(body, str) else None)
                text = resp.text[:5000]
                _logger.info("HTTP %s %s → %d", method, url, resp.status_code)
                return text
        except Exception as e:
            _logger.error("HTTP error: %s", e)
            return ''

    async def _ha_service_action(self, action: dict, slots: dict[str, str]) -> bool:
        """Вызов Home Assistant через встроенный voice_commands плагин (если есть),
        иначе напрямую через HA REST API."""
        entity_id = self.resolve_template(action.get('entity_id', ''), slots)
        service = action.get('service', '')
        data_str = self.resolve_template(action.get('data', '{}'), slots)
        try:
            data = json.loads(data_str) if data_str.strip() else {}
        except Exception:
            data = {}

        # Пытаемся делегировать существующему voice_commands
        try:
            from eva.plugin_loader.magic_plugin import MagicPlugin  # noqa
        except Exception:
            pass

        # Прямой вызов HA (настройки берём из конфига voice_commands или automations)
        ha_url, ha_token = self._get_ha_settings()
        if not (ha_url and ha_token):
            _logger.warning("HA не настроен")
            return False

        if '.' not in service:
            _logger.error("HA service должен быть в формате domain.service, получено: %r", service)
            return False

        domain, svc = service.split('.', 1)
        url = f"{ha_url}/api/services/{domain}/{svc}"
        headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json",
        }
        if entity_id:
            data.setdefault('entity_id', entity_id)

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, headers=headers, json=data)
                _logger.info("HA %s.%s на %s → %d", domain, svc, entity_id, resp.status_code)
                return 200 <= resp.status_code < 300
        except Exception as e:
            _logger.error("HA error: %s", e)
            return False

    def _get_ha_settings(self) -> tuple[Optional[str], Optional[str]]:
        """Берём HA URL/token из других плагинов или напрямую из конфига."""
        pm = getattr(self, '_pm', None)
        if pm is not None:
            try:
                for plugin_name in ('voice_commands', 'automations', 'integrations'):
                    p = pm.get_plugin_by_name(plugin_name) if hasattr(pm, 'get_plugin_by_name') else None
                    if p is None:
                        continue
                    cfg = getattr(p, 'config', {}) or {}
                    url = cfg.get('ha_url')
                    token = cfg.get('ha_token')
                    if url and token:
                        return url, token
            except Exception:
                pass
        # Fallback: читаем напрямую из YAML внутри EVA_HOME
        try:
            import yaml
            from eva.plugin_loader.file_patterns import first_substitution
            try:
                config_dir = first_substitution('{eva_home}/config')
            except Exception:
                config_dir = os.path.join(
                    os.environ.get('EVA_HOME', os.path.expanduser('~/eva')), 'config')
            for fname in ('automations.yaml', 'voice_commands.yaml', 'integrations.yaml'):
                fpath = os.path.join(config_dir, fname)
                if os.path.exists(fpath):
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        url = data.get('ha_url')
                        token = data.get('ha_token')
                        if url and token:
                            return url, token
        except Exception:
            pass
        return os.environ.get('HA_URL'), os.environ.get('HA_TOKEN')

    async def _timer_action(self, action: dict, slots: dict[str, str]) -> str:
        """Установка таймера через встроенный plugin_timer (если доступен)."""
        seconds_expr = str(action.get('seconds', 60))
        seconds_expr = self.resolve_template(seconds_expr, slots)
        message = self.resolve_template(action.get('message', 'Таймер сработал!'), slots)

        # Вычислим длительность: поддержка простых выражений "X * 60"
        try:
            if '*' in seconds_expr or '+' in seconds_expr or '-' in seconds_expr:
                # Безопасный eval — только математика
                seconds = int(eval(seconds_expr, {'__builtins__': {}}, {}))
            else:
                seconds = int(float(seconds_expr))
        except Exception as e:
            _logger.warning("Не удалось распарсить seconds=%r: %s", seconds_expr, e)
            return ''

        # Делегируем встроенному таймеру
        try:
            from eva.embedded_plugins.plugin_timer import TimerPlugin  # type: ignore
        except Exception:
            TimerPlugin = None

        if TimerPlugin is not None:
            # Найдём инстанс таймера среди активных плагинов
            try:
                pm = getattr(self, '_pm', None)
                if pm is not None:
                    timer = next(
                        (p for p in (pm.get_plugins() if hasattr(pm, 'get_plugins') else [])
                         if isinstance(p, TimerPlugin)),
                        None,
                    )
                    if timer is not None:
                        loop = asyncio.get_running_loop()
                        loop.call_later(seconds, lambda: self._brain_say(message))
                        _logger.info("Таймер поставлен на %d сек через plugin_timer", seconds)
                        return f'Таймер поставлен на {seconds} секунд'
            except Exception:
                pass

        # Фоллбэк: собственный таймер
        async def fire():
            await asyncio.sleep(seconds)
            await self._brain_say(message)
            _logger.info("Таймер сработал: %s", message)

        asyncio.create_task(fire())
        return f'Таймер поставлен на {seconds} секунд'

    async def _brain_say(self, text: str):
        """Озвучить текст через мозг (если доступен)."""
        if not text:
            return
        if self._brain is None:
            self._brain = self._get_brain()
        if self._brain is None:
            _logger.info("Eva: %s", text)
            return
        try:
            import concurrent.futures

            def interaction(va):
                va.say_speech(text)

            with concurrent.futures.ThreadPoolExecutor() as ex:
                fut = ex.submit(self._brain.submit_active_interaction, interaction)
                fut.result(timeout=10)
        except Exception as e:
            _logger.warning("Не удалось озвучить: %s", e)

    async def _play_sound(self, sound_path: str):
        """Воспроизвести звуковой файл."""
        if not sound_path:
            return
        if self._brain is None:
            self._brain = self._get_brain()
        if self._brain is None:
            return
        try:
            import concurrent.futures

            def interaction(va):
                va.play_audio(sound_path)

            with concurrent.futures.ThreadPoolExecutor() as ex:
                fut = ex.submit(self._brain.submit_active_interaction, interaction)
                fut.result(timeout=10)
        except Exception as e:
            _logger.warning("Не удалось воспроизвести звук: %s", e)

    def _get_brain(self):
        pm = getattr(self, '_pm', None)
        if pm is None:
            return None
        try:
            return call_all_as_wrappers(pm.get_operation_sequence('get_brain'), None)
        except Exception as e:
            _logger.warning("Не удалось получить brain: %s", e)
            return None

    async def _plugin_action(self, action: dict, slots: dict[str, str]) -> str:
        """Вызов функции подключённого плагина (по имени)."""
        plugin_name = action.get('plugin', '')
        func_name = action.get('function', '')
        args_str = self.resolve_template(action.get('args', ''), slots)

        if not plugin_name or not func_name:
            return ''

        # Разбор аргументов: comma-separated, уважаем кавычки
        args: list[str] = []
        if args_str.strip():
            import shlex
            try:
                args = shlex.split(args_str)
            except Exception:
                args = [a.strip() for a in args_str.split(',')]

        pm = getattr(self, '_pm', None)
        if pm is None:
            _logger.warning("Нет доступа к плагинам")
            return ''

        plugin = None
        if hasattr(pm, 'get_plugin_by_name'):
            plugin = pm.get_plugin_by_name(plugin_name)
        if plugin is None and hasattr(pm, 'get_plugins'):
            for p in pm.get_plugins():
                if getattr(p, 'name', None) == plugin_name:
                    plugin = p
                    break

        if plugin is None:
            _logger.warning("Плагин %s не найден", plugin_name)
            return ''

        func = getattr(plugin, func_name, None)
        if func is None:
            _logger.warning("У плагина %s нет функции %s", plugin_name, func_name)
            return ''

        try:
            result = func(*args)
            return str(result) if result is not None else ''
        except Exception as e:
            _logger.error("Ошибка вызова %s.%s: %s", plugin_name, func_name, e)
            return ''

    async def _llm_action(self, action: dict, slots: dict[str, str]) -> str:
        """Запрос к LLM (через eva_plugin_llm если доступен)."""
        prompt = self.resolve_template(action.get('prompt', ''), slots)
        system = self.resolve_template(action.get('system', ''), slots)

        pm = getattr(self, '_pm', None)
        if pm is None:
            return ''

        # Поиск LLM-плагина
        llm_plugin = None
        if hasattr(pm, 'get_plugin_by_name'):
            for name in ('plugin_llm_fallback_context', 'plugin_llm_lmstudio',
                         'plugin_llm_ollama', 'plugin_llm_openai'):
                p = pm.get_plugin_by_name(name)
                if p is not None:
                    llm_plugin = p
                    break
        if llm_plugin is None and hasattr(pm, 'get_plugins'):
            for p in pm.get_plugins():
                n = getattr(p, 'name', '') or ''
                if 'llm' in n.lower():
                    llm_plugin = p
                    break

        if llm_plugin is None:
            _logger.warning("LLM-плагин не найден — пропускаю действие llm")
            return ''

        # Универсальный вызов: у каждого LLM-плагина обычно есть метод ask/ask_llm
        for method in ('ask', 'ask_llm', 'complete', 'generate'):
            fn = getattr(llm_plugin, method, None)
            if fn is None:
                continue
            try:
                import inspect
                if inspect.iscoroutinefunction(fn):
                    result = await fn(prompt, system=system) if system else await fn(prompt)
                else:
                    result = fn(prompt, system=system) if system else fn(prompt)
                return str(result or '')
            except TypeError:
                try:
                    if inspect.iscoroutinefunction(fn):
                        result = await fn(prompt)
                    else:
                        result = fn(prompt)
                    return str(result or '')
                except Exception as e:
                    _logger.warning("LLM.%s ошибка: %s", method, e)
                    continue
            except Exception as e:
                _logger.warning("LLM.%s ошибка: %s", method, e)
                continue

        return ''

    async def execute_actions(self, skill: dict, slots: dict[str, str]) -> str:
        """Выполняет все actions навыка по очереди. Возвращает last_response."""
        last_response = ''
        for action in skill.get('actions', []):
            atype = action.get('type', 'text')
            config = action.get('config', {})
            # action сразу хранит поля на верхнем уровне — нормализуем
            merged = dict(config)
            merged.setdefault('type', atype)

            try:
                if atype == 'text':
                    last_response = self.resolve_template(config.get('text', ''), slots)
                    if last_response:
                        await self._brain_say(last_response)
                elif atype == 'http':
                    last_response = await self._http_action(merged, slots)
                elif atype == 'ha_service':
                    ok = await self._ha_service_action(merged, slots)
                    last_response = 'OK' if ok else 'Ошибка HA'
                elif atype == 'timer':
                    last_response = await self._timer_action(merged, slots)
                elif atype == 'plugin':
                    last_response = await self._plugin_action(merged, slots)
                elif atype == 'llm':
                    last_response = await self._llm_action(merged, slots)
                elif atype == 'macro':
                    # Выполнение поднавыков
                    for sub_id in config.get('skills', []):
                        sub = next((s for s in self.config['skills'] if s.get('id') == sub_id), None)
                        if sub:
                            sub_text = self.resolve_template(' '.join(sub.get('phrases', [])), slots)
                            sub_match = self.match_skill(sub_text)
                            if sub_match:
                                _, _, sub_slots = sub_match
                                last_response = await self.execute_actions(sub, sub_slots)
                else:
                    _logger.warning("Неизвестный тип действия: %s", atype)
            except Exception as e:
                _logger.exception("Ошибка выполнения действия %s: %s", atype, e)
                last_response = f'Ошибка: {e}'

        return last_response

    async def run_skill_by_text(self, text: str) -> dict:
        """Находит навык по фразе и выполняет его."""
        # Проверяем активные диалоговые сессии
        engine = get_engine()
        for key, session in engine._sessions.items():
            if not session.finished and session.skill_id:
                skill = next((s for s in self.config.get('skills', []) if s.get('id') == session.skill_id), None)
                if skill and skill.get('type') == 'dialogue':
                    result = engine.process_step(skill, session, text)
                    if result.get('text'):
                        await self._brain_say(result['text'])
                    if result.get('sound'):
                        await self._play_sound(result['sound'])
                    return {
                        'matched': True,
                        'intent': skill.get('intent'),
                        'skill_name': skill.get('name'),
                        'matched_phrase': text,
                        'response': result.get('text', ''),
                    }

        match = self.match_skill(text)
        if not match:
            return {
                'matched': False,
                'text': text,
                'message': 'Не нашёл подходящего навыка',
            }

        skill, matched_phrase, slots = match
        slots = dict(slots)
        slots['phrase'] = text
        slots['user_text'] = text

        # Диалоговый навык — запускаем сценарий
        if skill.get('type') == 'dialogue':
            session = engine.create_session(skill.get('id', ''))
            dialogue = skill.get('dialogue', {})
            session.variables = {k: v for k, v in dialogue.get('variables', {}).items()}
            result = engine.process_step(skill, session, '')
            if result.get('text'):
                await self._brain_say(result['text'])
            if result.get('sound'):
                await self._play_sound(result['sound'])
            return {
                'matched': True,
                'intent': skill.get('intent'),
                'skill_name': skill.get('name'),
                'matched_phrase': matched_phrase,
                'response': result.get('text', ''),
            }

        # Обычный навык
        last_response = await self.execute_actions(skill, slots)

        # Реакция — выбираем первую и подставляем
        reactions = skill.get('reactions', [])
        if reactions:
            # Если есть last_response — добавляем в слоты
            full_slots = dict(slots)
            full_slots['last_response'] = last_response
            reaction_text = self.resolve_template(reactions[0].get('text', ''), full_slots)
        else:
            reaction_text = last_response or 'Готово'

        # Озвучиваем реакцию (если не text-action её уже произнёс)
        has_speak = any(a.get('type') == 'text' for a in skill.get('actions', []))
        if not has_speak and reaction_text:
            await self._brain_say(reaction_text)

        return {
            'matched': True,
            'intent': skill.get('intent'),
            'skill_id': skill.get('id'),
            'skill_name': skill.get('name'),
            'matched_phrase': matched_phrase,
            'slots': slots,
            'actions_count': len(skill.get('actions', [])),
            'response': reaction_text,
            'last_action_result': last_response,
        }

    # ------------------------------------------------------------------
    # Регистрация команд в command-tree
    # ------------------------------------------------------------------

    def define_commands(self, *_args, **_kwargs) -> dict:
        """Каждый навык = команда в мозге Евы."""
        commands: dict[str, Any] = {}
        registered_intents = set()
        for skill in self.config.get('skills', []):
            if not skill.get('enabled', True):
                continue
            intent = skill.get('intent') or skill.get('name', '')
            if intent in registered_intents:
                continue
            registered_intents.add(intent)
            commands[f'выполни навык {intent}|запусти навык {intent}|skill run {intent}'] = (
                lambda va, text, s=skill: self._handle_skill(va, text, s)
            )

        commands['тест навыков|test skills|сколько навыков'] = self._handle_test_skills

        return commands

    def _handle_skill(self, va, text: str, skill: dict):
        """Обработчик для конкретного навыка, вызванного через command-tree."""
        reactions = skill.get('reactions', [])
        if reactions:
            va.say(reactions[0].get('text', 'Готово'))
        else:
            va.say('Готово')

    def _start_dialogue_skill(self, va, skill: dict):
        """Запуск диалогового навыка через генератор — полная изоляция ввода."""
        from eva.brain.contexts import GeneratorContext, ApiExtProvider

        dialogue = skill.get('dialogue', {})
        steps = {s['id']: s for s in dialogue.get('steps', [])}
        exit_phrases = dialogue.get('exit_phrases', ['хватит', 'стоп', 'пока', 'выйти'])
        variables = dict(dialogue.get('variables', {}))

        def dialogue_gen():
            import random
            current_id = 'start'
            user_input = ''

            while True:
                block = steps.get(current_id)
                if not block:
                    return 'Сценарий завершён.'

                text_input = user_input.lower().strip()
                if text_input in exit_phrases:
                    return 'Хорошо! Если захочешь — обращайся.'

                block_type = block.get('type', 'text')

                if block_type in ('text', 'intro'):
                    text = block.get('text', '')
                    if isinstance(text, list):
                        text = random.choice(text)
                    for k, v in variables.items():
                        text = text.replace('{' + k + '}', str(v))

                    question = block.get('question', '')
                    if question:
                        for k, v in variables.items():
                            question = question.replace('{' + k + '}', str(v))

                    if question and not user_input:
                        user_input = yield f"{text}\n\n{question}"
                        continue

                    if question and user_input:
                        save_to = block.get('save_to', 'user_answer')
                        variables[save_to] = user_input

                    next_id = block.get('next', '')
                    if next_id:
                        current_id = next_id
                    else:
                        return text
                    user_input = ''
                    continue

                elif block_type == 'loop':
                    save_to = block.get('save_to', 'user_answer')
                    if user_input:
                        variables[save_to] = user_input

                    counter_var = block.get('counter_var', '$loop_count')
                    variables[counter_var] = variables.get(counter_var, 0) + 1

                    template = block.get('template', '{user_answer}')
                    for k, v in variables.items():
                        template = template.replace('{' + k + '}', str(v))

                    exit_cond = block.get('exit_condition', '')
                    if exit_cond:
                        try:
                            expr = exit_cond
                            for k, v in variables.items():
                                if isinstance(v, (int, float)):
                                    expr = expr.replace(k, str(v))
                            if bool(eval(expr, {"__builtins__": {}}, {})):
                                current_id = block.get('next', '')
                                user_input = ''
                                continue
                        except Exception:
                            pass

                    current_id = block.get('self_loop', block.get('id', ''))
                    user_input = yield template
                    continue

                elif block_type == 'finale':
                    text = block.get('text', 'Готово.')
                    if isinstance(text, list):
                        text = random.choice(text)
                    for k, v in variables.items():
                        text = text.replace('{' + k + '}', str(v))
                    return text

                else:
                    return 'Сценарий завершён.'

        gen = dialogue_gen()
        ext = ApiExtProvider(None)
        ctx = GeneratorContext(gen, ext)
        return ctx.start(va)

    async def _run_async(self, va, skill, slots):
        last_response = await self.execute_actions(skill, slots)
        full_slots = dict(slots)
        full_slots['last_response'] = last_response
        reactions = skill.get('reactions', [])
        if reactions:
            reaction_text = self.resolve_template(reactions[0].get('text', ''), full_slots)
            va.say(reaction_text)

    def _handle_test_skills(self, va, text: str):
        count = sum(1 for s in self.config.get('skills', []) if s.get('enabled', True))
        va.say(f'Активных навыков: {count}')

    # ------------------------------------------------------------------
    # REST API
    # ------------------------------------------------------------------

    def register_fastapi_endpoints(self, router, pm, *_args, **_kwargs):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel
        from typing import List, Optional

        self._pm = pm  # сохраняем для executor'а
        r: APIRouter = router
        plugin = self

        class SkillActionModel(BaseModel):
            id: Optional[str] = None
            type: str
            config: dict = {}

        class SkillSlotModel(BaseModel):
            id: Optional[str] = None
            name: str
            type: str = 'string'
            required: bool = False
            examples: List[str] = []
            values: Optional[List[str]] = None
            defaultValue: Optional[str] = None

        class SkillReactionModel(BaseModel):
            id: Optional[str] = None
            text: str
            tts: Optional[str] = None
            sound: Optional[str] = None

        class SkillSessionModel(BaseModel):
            enabled: bool = False
            ttl: int = 60

        class SkillModel(BaseModel):
            id: Optional[str] = None
            intent: str
            name: str
            description: str = ''
            enabled: bool = True
            phrases: List[str] = []
            matchMode: str = 'contains'
            slots: List[SkillSlotModel] = []
            actions: List[SkillActionModel] = []
            reactions: List[SkillReactionModel] = []
            session: SkillSessionModel = SkillSessionModel()
            category: str = 'custom'
            type: str = 'simple'
            dialogue: Optional[dict] = None

        @r.get('/list')
        async def list_skills():
            return plugin.config.get('skills', [])

        class SaveRequest(BaseModel):
            skills: List[SkillModel]

        @r.post('/save')
        async def save_skills(req: SaveRequest):
            plugin.config['skills'] = [s.dict() for s in req.skills]
            ok = plugin._save_skills()
            return {
                'status': 'ok' if ok else 'partial',
                'count': len(plugin.config['skills']),
                'persisted': ok,
            }

        class RunRequest(BaseModel):
            text: str

        @r.post('/run')
        async def run_skill(req: RunRequest):
            result = await plugin.run_skill_by_text(req.text)
            return result

        @r.get('/match')
        async def match_skill(text: str):
            result = plugin.match_skill(text)
            if not result:
                return {'matched': False}
            skill, phrase, slots = result
            return {
                'matched': True,
                'intent': skill.get('intent'),
                'skill_name': skill.get('name'),
                'matched_phrase': phrase,
                'slots': slots,
            }

        @r.post('/test/{skill_id}')
        async def test_skill(skill_id: str):
            skill = next((s for s in plugin.config.get('skills', []) if s.get('id') == skill_id), None)
            if not skill:
                raise HTTPException(404, 'Skill not found')
            # Используем первую фразу как тестовый ввод
            test_phrase = skill.get('phrases', ['тест'])[0]
            slots = plugin.parse_phrase_to_slots(test_phrase, test_phrase, skill.get('slots', []))
            return {
                'status': 'ok',
                'skill_name': skill.get('name'),
                'test_phrase': test_phrase,
                'slots': slots,
                'actions_count': len(skill.get('actions', [])),
            }

        @r.get('/action_types')
        async def action_types():
            return [
                {'type': 'text', 'name': 'Текстовый ответ'},
                {'type': 'http', 'name': 'HTTP-запрос'},
                {'type': 'plugin', 'name': 'Вызов плагина'},
                {'type': 'ha_service', 'name': 'Home Assistant'},
                {'type': 'timer', 'name': 'Таймер'},
                {'type': 'llm', 'name': 'Языковая модель (LLM)'},
                {'type': 'macro', 'name': 'Макрос (другие навыки)'},
            ]

        @r.get('/slot_types')
        async def slot_types():
            return [
                {'type': 'string', 'name': 'Строка', 'example': 'Москва, кухня'},
                {'type': 'number', 'name': 'Число', 'example': '5, 25, 100.5'},
                {'type': 'date', 'name': 'Дата', 'example': 'завтра, 25.12'},
                {'type': 'geo', 'name': 'Геолокация', 'example': 'Москва, ул. Ленина 5'},
                {'type': 'list', 'name': 'Список', 'example': 'свет / шторы / климат'},
                {'type': 'bool', 'name': 'Да/Нет', 'example': 'да, нет, включи'},
            ]

        @r.get('/integrations')
        async def list_integrations():
            info = {
                'ha_connected': False,
                'ha_url': None,
                'plugins': [],
                'skills_count': len(plugin.config.get('skills', [])),
            }
            try:
                for pname in ('voice_commands', 'automations', 'integrations'):
                    p = pm.get_plugin_by_name(pname) if hasattr(pm, 'get_plugin_by_name') else None
                    if p is not None:
                        cfg = getattr(p, 'config', {}) or {}
                        if cfg.get('ha_url'):
                            info['ha_connected'] = True
                            info['ha_url'] = cfg['ha_url']
                            break
            except Exception:
                pass
            try:
                for step in pm.get_operation_sequence('define_commands'):
                    pname = getattr(step.plugin, 'name', 'unknown')
                    if pname not in info['plugins']:
                        info['plugins'].append(pname)
            except Exception:
                pass
            return info

        @r.get('/ha/entities')
        async def ha_entities(filter: str = '', domain: str = '', limit: int = 500):
            ha_url, ha_token = plugin._get_ha_settings()
            if not (ha_url and ha_token):
                return {'entities': [], 'error': 'HA не подключён'}
            try:
                import httpx
                async with httpx.AsyncClient(timeout=15) as client:
                    # Получаем areas (комнаты)
                    areas_resp = await client.get(
                        f"{ha_url}/api/areas",
                        headers={"Authorization": f"Bearer {ha_token}"}
                    )
                    areas = {}
                    if areas_resp.status_code == 200:
                        for area in areas_resp.json():
                            areas[area.get('area_id', '')] = area.get('name', '')

                    resp = await client.get(
                        f"{ha_url}/api/states",
                        headers={"Authorization": f"Bearer {ha_token}"}
                    )
                    if resp.status_code != 200:
                        return {'entities': [], 'error': f'HTTP {resp.status_code}'}
                    states = resp.json()
                    entities = []
                    for s in states:
                        eid = s.get('entity_id', '')
                        d = eid.split('.')[0] if '.' in eid else ''
                        if domain and d != domain:
                            continue
                        friendly = (s.get('attributes') or {}).get('friendly_name', '')
                        area_id = (s.get('attributes') or {}).get('area_id', '')
                        area_name = areas.get(area_id, '') if area_id else ''
                        if filter:
                            fl = filter.lower()
                            if fl not in eid.lower() and fl not in friendly.lower() and fl not in area_name.lower():
                                continue
                        entities.append({
                            'entity_id': eid,
                            'state': s.get('state', ''),
                            'domain': d,
                            'friendly_name': friendly,
                            'unit': (s.get('attributes') or {}).get('unit_of_measurement', ''),
                            'area': area_name,
                        })
                        if len(entities) >= limit:
                            break
                    domains = sorted(set(e['domain'] for e in entities))
                    area_list = sorted(set(e['area'] for e in entities if e['area']))
                    return {'entities': entities, 'domains': domains, 'areas': area_list, 'total': len(states)}
            except Exception as e:
                return {'entities': [], 'error': str(e)}

        @r.get('/ha/services')
        async def ha_services(domain: str = ''):
            ha_url, ha_token = plugin._get_ha_settings()
            if not (ha_url and ha_token):
                return {'services': [], 'error': 'HA не подключён'}
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"{ha_url}/api/services",
                        headers={"Authorization": f"Bearer {ha_token}"}
                    )
                    if resp.status_code != 200:
                        return {'services': [], 'error': f'HTTP {resp.status_code}'}
                    services = resp.json()
                    result = []
                    for svc in services:
                        svc_domain = svc.get('domain', '')
                        if domain and svc_domain != domain:
                            continue
                        for name, info in (svc.get('services') or {}).items():
                            result.append({
                                'domain': svc_domain,
                                'service': name,
                                'full': f"{svc_domain}.{name}",
                                'name': info.get('name', name),
                                'description': info.get('description', ''),
                                'target': bool(info.get('target')),
                                'fields': list((info.get('fields') or {}).keys()),
                            })
                    return {'services': result}
            except Exception as e:
                return {'services': [], 'error': str(e)}

        @r.get('/dialogue/sessions')
        async def list_dialogue_sessions():
            engine = get_engine()
            sessions = []
            for key, session in engine._sessions.items():
                if not session.finished:
                    skill = next((s for s in plugin.config.get('skills', []) if s.get('id') == session.skill_id), None)
                    sessions.append({
                        'key': key,
                        'skill_id': session.skill_id,
                        'skill_name': skill.get('name', '') if skill else '',
                        'current_step': session.current_step_id,
                        'variables': session.variables,
                        'step_count': session.system_vars.get('$step_count', 0),
                    })
            return {'sessions': sessions}

        @r.post('/dialogue/process')
        async def dialogue_process(req: dict):
            skill_id = req.get('skill_id', '')
            user_input = req.get('text', '')
            skill = next((s for s in plugin.config.get('skills', []) if s.get('id') == skill_id), None)
            if not skill or skill.get('type') != 'dialogue':
                return {'error': 'Навык не найден или не диалоговый'}
            engine = get_engine()
            session = engine.get_session(skill_id)
            if not session or session.finished:
                session = engine.create_session(skill_id)
                dialogue = skill.get('dialogue', {})
                session.variables = {k: v for k, v in dialogue.get('variables', {}).items()}
            result = engine.process_step(skill, session, user_input)
            if result.get('text'):
                await plugin._brain_say(result['text'])
            return result

        class AutoCreateRequest(BaseModel):
            request: str

        @r.post('/auto_create')
        async def auto_create_skill(req: AutoCreateRequest):
            import uuid as _uuid
            skill = {
                "id": str(_uuid.uuid4())[:8],
                "intent": f"Auto.{req.request[:30].replace(' ', '.')}",
                "name": req.request[:50],
                "description": req.request,
                "enabled": True,
                "matchMode": "contains",
                "category": "auto",
                "phrases": [req.request.lower()],
                "slots": [],
                "actions": [
                    {"type": "text", "config": {"text": f"Выполняю: {req.request}"}}
                ],
                "reactions": [
                    {"text": f"Готово: {req.request}", "tts": f"Выполнила: {req.request}"}
                ],
                "session": {"enabled": False, "ttl": 60},
            }
            plugin.config['skills'].append(skill)
            plugin._save_skills()
            return {
                'status': 'ok',
                'skill': skill,
                'message': f"Навык '{skill['name']}' создан. Перезапустите для активации."
            }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init(self, *_args, **_kwargs):
        self._load_skills()
        self._brain = self._get_brain()
