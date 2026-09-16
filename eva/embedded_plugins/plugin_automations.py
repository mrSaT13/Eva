"""
Плагин автоматизаций Eva.
Реальные автоматизации с интеграцией Home Assistant.
"""

import json
import os
import time
import asyncio
from logging import getLogger
from typing import Any, Optional
from datetime import datetime

from eva.plugin_loader.magic_plugin import MagicPlugin
from eva.plugin_loader.run_operation import call_all_as_wrappers

_logger = getLogger('automations')


class AutomationsPlugin(MagicPlugin):
    name = 'automations'
    version = '4.0.0'

    config: dict[str, Any] = {
        "automations": [],
        "ha_url": "http://localhost:8123",
        "ha_token": "",
        "poll_interval": 30,
    }

    config_comment = """
Настройки автоматизаций Eva.

Параметры:
- ha_url       - URL Home Assistant
- ha_token     - Токен доступа HA
- poll_interval - Интервал опроса HA (секунды)
"""

    def __init__(self):
        super().__init__()
        self._brain = None
        self._last_states = {}
        self._scheduled_tasks = []
        self._load_automations()

    def _get_automations_path(self) -> str:
        home = os.path.expanduser('~/eva')
        return os.path.join(home, 'automations.json')

    def _load_automations(self):
        path = self._get_automations_path()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.config['automations'] = json.load(f)
        except Exception as e:
            _logger.error("Ошибка загрузки: %s", e)

    def _save_automations(self):
        path = self._get_automations_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.config['automations'], f, ensure_ascii=False, indent=2)

    def _generate_id(self) -> str:
        return str(int(time.time() * 1000))

    async def _ha_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        import httpx
        url = f"{self.config['ha_url']}{endpoint}"
        headers = {"Authorization": f"Bearer {self.config['ha_token']}", "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            if method == "GET":
                res = await client.get(url, headers=headers, timeout=10)
            elif method == "POST":
                res = await client.post(url, headers=headers, json=data, timeout=10)
            else:
                return {"error": f"Unknown method: {method}"}
            return res.json() if res.status_code == 200 else {"error": f"HTTP {res.status_code}"}

    def _get_brain(self, pm):
        if self._brain is None:
            try:
                self._brain = call_all_as_wrappers(
                    pm.get_operation_sequence('get_brain'),
                    None,
                )
            except Exception as e:
                _logger.warning("Не удалось получить brain: %s", e)
        return self._brain

    def _execute_action(self, action: dict, pm=None):
        brain = self._brain or (self._get_brain(pm) if pm else None)

        atype = action.get('type', '')
        message = action.get('message', '')

        if atype in ('speak', 'reply'):
            if brain is not None:
                try:
                    import concurrent.futures
                    def interaction(va):
                        va.say_speech(message)
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(brain.submit_active_interaction, interaction)
                        future.result(timeout=5)
                    _logger.info("Executed: %s -> %s", atype, message)
                except Exception as e:
                    _logger.warning("Brain error: %s", e)
                    _logger.info("Automation: %s -> %s", atype, message)
            else:
                _logger.info("Automation: %s -> %s (brain unavailable)", atype, message)

        elif atype == 'service':
            domain = action.get('domain', '')
            service = action.get('service', '')
            entity_id = action.get('entity_id', '')
            data = action.get('data', {})
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._ha_service_call(domain, service, entity_id, data))
                else:
                    loop.run_until_complete(self._ha_service_call(domain, service, entity_id, data))
            except Exception as e:
                _logger.error("Service call error: %s", e)

    async def _ha_service_call(self, domain: str, service: str, entity_id: str = None, data: dict = None):
        service_data = data or {}
        if entity_id:
            service_data["entity_id"] = entity_id
        result = await self._ha_request("POST", f"/api/services/{domain}/{service}", service_data)
        if "error" in result:
            _logger.warning("HA service error: %s", result["error"])
        else:
            _logger.info("HA service called: %s.%s on %s", domain, service, entity_id)

    def define_commands(self, *_args, **_kwargs) -> dict:
        commands = {}
        for auto in self.config.get('automations', []):
            if not auto.get('enabled', True):
                continue
            trigger = auto.get('trigger', {})
            if trigger.get('type') == 'text_command':
                cmd = trigger.get('text', '').strip()
                if cmd:
                    auto_id = auto.get('id', '')
                    commands[cmd] = lambda va, text, a=auto: self._run_automation(va, a)
        return commands

    def _run_automation(self, va, automation: dict):
        for action in automation.get('actions', []):
            self._execute_action(action)
        va.say(f"Выполняю: {automation.get('name', 'автоматизация')}")

    def _check_state_trigger(self, automation: dict, new_states: dict) -> bool:
        trigger = automation.get('trigger', {})
        if trigger.get('type') != 'state':
            return False
        entity_id = trigger.get('entity_id', '')
        condition = trigger.get('condition', '')
        if not entity_id:
            return False
        old_state = self._last_states.get(entity_id)
        new_state = new_states.get(entity_id)
        if old_state is None:
            return False
        if condition and new_state == condition and old_state != condition:
            return True
        if not condition and new_state != old_state:
            return True
        return False

    def _check_time_trigger(self, automation: dict) -> bool:
        trigger = automation.get('trigger', {})
        if trigger.get('type') != 'time':
            return False
        target_time = trigger.get('time', '')
        if not target_time:
            return False
        now = datetime.now()
        current_time = f"{now.hour:02d}:{now.minute:02d}"
        return current_time == target_time

    def _check_interval_trigger(self, automation: dict) -> bool:
        trigger = automation.get('trigger', {})
        if trigger.get('type') != 'interval':
            return False
        interval_seconds = trigger.get('interval_seconds', 0)
        if interval_seconds <= 0:
            return False
        auto_id = automation.get('id', '')
        last_run_key = f"last_interval_{auto_id}"
        last_run = getattr(self, last_run_key, None)
        now = time.time()
        if last_run is None or (now - last_run) >= interval_seconds:
            setattr(self, last_run_key, now)
            return True
        return False

    def _check_cron_trigger(self, automation: dict) -> bool:
        trigger = automation.get('trigger', {})
        if trigger.get('type') != 'cron':
            return False
        cron_expr = trigger.get('cron', '')
        if not cron_expr:
            return False
        now = datetime.now()
        parts = cron_expr.split()
        if len(parts) < 5:
            return False
        minute, hour, day, month, dow = parts[0], parts[1], parts[2], parts[3], parts[4]

        def match_field(field: str, value: int) -> bool:
            if field == '*':
                return True
            if field.startswith('*/'):
                try:
                    return value % int(field[2:]) == 0
                except ValueError:
                    return False
            if '-' in field:
                try:
                    lo, hi = field.split('-', 1)
                    return int(lo) <= value <= int(hi)
                except ValueError:
                    return False
            if ',' in field:
                return str(value) in field.split(',')
            try:
                return int(field) == value
            except ValueError:
                return False

        if not match_field(minute, now.minute):
            return False
        if not match_field(hour, now.hour):
            return False
        if not match_field(day, now.day):
            return False
        if not match_field(month, now.month):
            return False
        if not match_field(dow, now.weekday()):
            return False

        auto_id = automation.get('id', '')
        last_run_key = f"last_cron_{auto_id}"
        current_minute = f"{now.hour:02d}:{now.minute:02d}"
        if getattr(self, last_run_key, None) == current_minute:
            return False
        setattr(self, last_run_key, current_minute)
        return True

    async def _poll_ha_states(self, pm=None):
        if not self.config['ha_token'] or not self.config['ha_url']:
            return
        try:
            result = await self._ha_request("GET", "/api/states")
            if not isinstance(result, list):
                return
            new_states = {s.get("entity_id", ""): s.get("state") for s in result}
            for auto in self.config['automations']:
                if not auto.get('enabled', True):
                    continue
                if self._check_state_trigger(auto, new_states):
                    _logger.info("Сработал триггер: %s", auto.get('name'))
                    for action in auto.get('actions', []):
                        self._execute_action(action, pm)
            self._last_states = new_states
        except Exception as e:
            _logger.debug("Ошибка polling: %s", e)

    async def _check_time_triggers(self, pm=None):
        now = datetime.now()
        current_time = f"{now.hour:02d}:{now.minute:02d}"
        for auto in self.config['automations']:
            if not auto.get('enabled', True):
                continue
            trigger = auto.get('trigger', {})
            if trigger.get('type') == 'time' and trigger.get('time') == current_time:
                auto_id = auto.get('id')
                last_run_key = f"last_run_{auto_id}"
                if getattr(self, last_run_key, None) != current_time:
                    setattr(self, last_run_key, current_time)
                    _logger.info("Сработал time-триггер: %s", auto.get('name'))
                    for action in auto.get('actions', []):
                        self._execute_action(action, pm)

    async def _poll_loop(self, pm):
        self._get_brain(pm)
        while True:
            try:
                await asyncio.sleep(self.config.get('poll_interval', 30))
                await self._poll_ha_states(pm)
                await self._check_time_triggers(pm)
                self._check_interval_triggers(pm)
                self._check_cron_triggers(pm)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("Ошибка polling loop: %s", e)

    def _check_interval_triggers(self, pm=None):
        for auto in self.config.get('automations', []):
            if not auto.get('enabled', True):
                continue
            if self._check_interval_trigger(auto):
                _logger.info("Сработал interval-триггер: %s", auto.get('name'))
                for action in auto.get('actions', []):
                    self._execute_action(action, pm)

    def _check_cron_triggers(self, pm=None):
        for auto in self.config.get('automations', []):
            if not auto.get('enabled', True):
                continue
            if self._check_cron_trigger(auto):
                _logger.info("Сработал cron-триггер: %s", auto.get('name'))
                for action in auto.get('actions', []):
                    self._execute_action(action, pm)

    async def run(self, pm, *_args, **_kwargs):
        task = asyncio.create_task(self._poll_loop(pm))
        self._scheduled_tasks.append(task)

    async def terminate(self, *_args, **_kwargs):
        for task in self._scheduled_tasks:
            task.cancel()
        self._scheduled_tasks.clear()

    def register_fastapi_endpoints(self, router, pm, *_args, **_kwargs):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel
        from typing import List

        r: APIRouter = router
        plugin = self

        class TriggerModel(BaseModel):
            type: str
            entity_id: Optional[str] = None
            time: Optional[str] = None
            event: Optional[str] = None
            condition: Optional[str] = None
            interval_seconds: Optional[int] = None
            cron: Optional[str] = None

        class ActionModel(BaseModel):
            type: str
            entity_id: Optional[str] = None
            service: Optional[str] = None
            data: Optional[dict] = None
            message: Optional[str] = None

        class AutomationCreate(BaseModel):
            name: str
            trigger: TriggerModel
            actions: List[ActionModel]
            enabled: bool = True

        @r.get('/')
        async def list_automations():
            return plugin.config['automations']

        @r.post('/')
        async def create_automation(req: AutomationCreate):
            automation = {
                "id": plugin._generate_id(),
                "name": req.name,
                "trigger": req.trigger.dict(),
                "actions": [a.dict() for a in req.actions],
                "enabled": req.enabled,
            }
            plugin.config['automations'].append(automation)
            plugin._save_automations()
            return automation

        @r.patch('/{auto_id}')
        async def update_automation(auto_id: str, req: dict):
            for auto in plugin.config['automations']:
                if auto['id'] == auto_id:
                    for k, v in req.items():
                        if v is not None:
                            auto[k] = v
                    plugin._save_automations()
                    return auto
            raise HTTPException(404, "Not found")

        @r.delete('/{auto_id}')
        async def delete_automation(auto_id: str):
            plugin.config['automations'] = [a for a in plugin.config['automations'] if a['id'] != auto_id]
            plugin._save_automations()
            return {"status": "deleted"}

        @r.get('/ha_status')
        async def ha_status():
            if not plugin.config['ha_url'] or not plugin.config['ha_token']:
                return {"connected": False, "error": "HA не настроен"}
            try:
                result = await plugin._ha_request("GET", "/api/")
                return {"connected": "message" in result, "message": result.get("message", "")}
            except Exception as e:
                return {"connected": False, "error": str(e)}

        @r.get('/ha/devices')
        async def ha_devices():
            if not plugin.config['ha_token']:
                return []
            try:
                result = await plugin._ha_request("GET", "/api/states")
                if isinstance(result, list):
                    return [
                        {"entity_id": s.get("entity_id"), "state": s.get("state"),
                         "name": s.get("attributes", {}).get("friendly_name", s.get("entity_id")),
                         "domain": s.get("entity_id", "").split(".")[0]}
                        for s in result
                        if s.get("entity_id", "").split(".")[0] in ("light", "switch", "sensor", "binary_sensor", "climate", "media_player", "cover", "lock", "fan")
                    ]
                return []
            except Exception:
                return []

        @r.get('/ha/trigger_types')
        async def trigger_types():
            return [
                {"type": "time", "name": "По времени (HH:MM)"},
                {"type": "interval", "name": "Интервал (каждые N сек)"},
                {"type": "cron", "name": "Расписание (cron)"},
                {"type": "state", "name": "Изменение устройства"},
                {"type": "sun", "name": "Восход/закат"},
                {"type": "manual", "name": "Голосовая команда"},
                {"type": "text_command", "name": "Текстовая команда"},
            ]

        @r.get('/ha/action_types')
        async def action_types():
            return [
                {"type": "service", "name": "Управление устройством"},
                {"type": "speak", "name": "Озвучить текст"},
                {"type": "reply", "name": "Ответ текстом"},
                {"type": "notify", "name": "Уведомление"},
                {"type": "delay", "name": "Задержка"},
            ]

        @r.post('/{auto_id}/test')
        async def test_automation(auto_id: str):
            for auto in plugin.config['automations']:
                if auto['id'] == auto_id:
                    for action in auto.get('actions', []):
                        plugin._execute_action(action, pm)
                    return {"status": "ok", "message": "Действия выполнены"}
            raise HTTPException(404, "Not found")
