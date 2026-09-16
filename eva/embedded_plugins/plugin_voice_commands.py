"""
Голосовые команды для автоматизаций и макросы с переменными.

Позволяет привязывать голосовые команды к автоматизациям
и использовать переменные в командах и ответах.
"""

import json
import os
import re
import time
from logging import getLogger
from typing import Any, Optional, Callable
from datetime import datetime

from eva.plugin_loader.magic_plugin import MagicPlugin
from eva.plugin_loader.run_operation import call_all_as_wrappers

_logger = getLogger('voice_commands')


class VoiceCommandsPlugin(MagicPlugin):
    name = 'voice_commands'
    version = '1.0.0'

    config: dict[str, Any] = {
        "macros": [],
        "ha_url": "http://localhost:8123",
        "ha_token": "",
    }

    config_comment = """
Голосовые команды и макросы Eva.

Параметры:
- macros      - список макросов (команда -> действия)
- ha_url      - URL Home Assistant
- ha_token    - Токен доступа HA
"""

    def __init__(self):
        super().__init__()
        self._brain = None
        self._load_macros()

    def _get_macros_path(self) -> str:
        home = os.path.expanduser('~/eva')
        return os.path.join(home, 'voice_macros.json')

    def _load_macros(self):
        path = self._get_macros_path()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.config['macros'] = json.load(f)
        except Exception as e:
            _logger.error("Ошибка загрузки макросов: %s", e)

    def _save_macros(self):
        path = self._get_macros_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.config['macros'], f, ensure_ascii=False, indent=2)

    def _generate_id(self) -> str:
        return str(int(time.time() * 1000))

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

    def _resolve_variables(self, text: str, context: dict = None) -> str:
        if not text:
            return text

        now = datetime.now()
        default_vars = {
            "time": now.strftime("%H:%M"),
            "date": now.strftime("%d.%m.%Y"),
            "datetime": now.strftime("%d.%m.%Y %H:%M"),
            "hour": str(now.hour),
            "minute": str(now.minute),
            "day": str(now.day),
            "month": str(now.month),
            "year": str(now.year),
            "weekday": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"][now.weekday()],
        }

        if context:
            default_vars.update(context)

        def replace_var(match):
            var_name = match.group(1)
            return str(default_vars.get(var_name, match.group(0)))

        return re.sub(r'\{(\w+)\}', replace_var, text)

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

    async def _execute_ha_service(self, domain: str, service: str, entity_id: str = None, data: dict = None) -> bool:
        try:
            service_data = data or {}
            if entity_id:
                service_data["entity_id"] = entity_id
            result = await self._ha_request("POST", f"/api/services/{domain}/{service}", service_data)
            if "error" in result:
                _logger.warning("HA service error: %s", result["error"])
                return False
            _logger.info("HA service executed: %s.%s on %s", domain, service, entity_id)
            return True
        except Exception as e:
            _logger.error("HA service execution error: %s", e)
            return False

    def _execute_action(self, action: dict, context: dict = None, pm=None):
        brain = self._brain or (self._get_brain(pm) if pm else None)
        atype = action.get('type', '')
        message = action.get('message', '')

        if context:
            message = self._resolve_variables(message, context)

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
            else:
                _logger.info("Action: %s -> %s (brain unavailable)", atype, message)

        elif atype == 'service':
            domain = action.get('domain', '')
            service = action.get('service', '')
            entity_id = action.get('entity_id', '')
            data = action.get('data', {})
            if context and entity_id:
                entity_id = self._resolve_variables(entity_id, context)
            try:
                import asyncio
                asyncio.create_task(self._execute_ha_service(domain, service, entity_id, data))
            except Exception as e:
                _logger.error("Service execution error: %s", e)

        elif atype == 'delay':
            seconds = action.get('seconds', 1)
            if context:
                seconds = int(self._resolve_variables(str(seconds), context))
            try:
                import asyncio
                asyncio.get_event_loop().call_later(seconds, lambda: None)
            except Exception:
                pass

    def _find_matching_macro(self, text: str) -> Optional[dict]:
        text_lower = text.strip().lower()
        for macro in self.config.get('macros', []):
            if not macro.get('enabled', True):
                continue
            trigger = macro.get('trigger', '').strip().lower()
            if not trigger:
                continue
            if trigger in text_lower or text_lower in trigger:
                return macro
        return None

    def define_commands(self, *_args, **_kwargs) -> dict:
        commands = {}

        for macro in self.config.get('macros', []):
            if not macro.get('enabled', True):
                continue
            trigger = macro.get('trigger', '').strip()
            if not trigger:
                continue
            macro_id = macro.get('id', '')
            commands[trigger] = lambda va, text, m=macro: self._handle_macro_command(va, text, m)

        if not commands:
            commands["проверь макросы|тест макросов"] = self._handle_test_macros

        return commands

    def _handle_macro_command(self, va, text: str, macro: dict):
        context = {"user_text": text}
        actions = macro.get('actions', [])

        for action in actions:
            self._execute_action(action, context)

        response = macro.get('response', '')
        if response:
            response = self._resolve_variables(response, context)
            va.say(response)
        else:
            va.say(f"Выполняю: {macro.get('name', 'макрос')}")

    def _handle_test_macros(self, va, text: str):
        count = len([m for m in self.config.get('macros', []) if m.get('enabled', True)])
        va.say(f"Активных макросов: {count}")

    def register_fastapi_endpoints(self, router, pm, *_args, **_kwargs):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel
        from typing import List

        r: APIRouter = router
        plugin = self

        class MacroActionModel(BaseModel):
            type: str
            message: Optional[str] = None
            entity_id: Optional[str] = None
            domain: Optional[str] = None
            service: Optional[str] = None
            data: Optional[dict] = None
            seconds: Optional[int] = None

        class MacroCreate(BaseModel):
            name: str
            trigger: str
            response: Optional[str] = ""
            actions: List[MacroActionModel] = []
            enabled: bool = True

        @r.get('/')
        async def list_macros():
            return plugin.config['macros']

        @r.post('/')
        async def create_macro(req: MacroCreate):
            macro = {
                "id": plugin._generate_id(),
                "name": req.name,
                "trigger": req.trigger,
                "response": req.response,
                "actions": [a.dict() for a in req.actions],
                "enabled": req.enabled,
            }
            plugin.config['macros'].append(macro)
            plugin._save_macros()
            return macro

        @r.patch('/{macro_id}')
        async def update_macro(macro_id: str, req: dict):
            for macro in plugin.config['macros']:
                if macro['id'] == macro_id:
                    for k, v in req.items():
                        if v is not None:
                            macro[k] = v
                    plugin._save_macros()
                    return macro
            raise HTTPException(404, "Macro not found")

        @r.delete('/{macro_id}')
        async def delete_macro(macro_id: str):
            plugin.config['macros'] = [m for m in plugin.config['macros'] if m['id'] != macro_id]
            plugin._save_macros()
            return {"status": "deleted"}

        @r.post('/{macro_id}/test')
        async def test_macro(macro_id: str):
            for macro in plugin.config['macros']:
                if macro['id'] == macro_id:
                    context = {"time": datetime.now().strftime("%H:%M")}
                    for action in macro.get('actions', []):
                        plugin._execute_action(action, context, pm)
                    return {"status": "ok", "message": f"Макрос '{macro['name']}' выполнен"}
            raise HTTPException(404, "Macro not found")

        @r.get('/variables')
        async def list_variables():
            now = datetime.now()
            return {
                "time": now.strftime("%H:%M"),
                "date": now.strftime("%d.%m.%Y"),
                "datetime": now.strftime("%d.%m.%Y %H:%M"),
                "hour": str(now.hour),
                "minute": str(now.minute),
                "weekday": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"][now.weekday()],
                "user_text": "текст пользователя",
            }
