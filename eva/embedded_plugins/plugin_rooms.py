"""
Управление комнатами и зонами из Home Assistant.

Позволяет управлять устройствами по комнатам,
получать список комнат и устройств.
"""

import json
import os
from logging import getLogger
from typing import Any, Optional

from eva.plugin_loader.magic_plugin import MagicPlugin

_logger = getLogger('rooms')


class RoomsPlugin(MagicPlugin):
    name = 'rooms'
    version = '1.0.0'

    config: dict[str, Any] = {
        "ha_url": "http://localhost:8123",
        "ha_token": "",
        "cache_ttl": 300,
    }

    config_comment = """
Управление комнатами из Home Assistant.

Параметры:
- ha_url     - URL Home Assistant
- ha_token   - Токен доступа HA
- cache_ttl  - Время кэширования (секунды)
"""

    def __init__(self):
        super().__init__()
        self._areas_cache = None
        self._devices_cache = None
        self._cache_time = 0

    async def _ha_request(self, method: str, endpoint: str) -> Any:
        import httpx
        url = f"{self.config['ha_url']}{endpoint}"
        headers = {"Authorization": f"Bearer {self.config['ha_token']}", "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            if method == "GET":
                res = await client.get(url, headers=headers, timeout=10)
            else:
                return None
            return res.json() if res.status_code == 200 else None

    def _ha_request_sync(self, method: str, endpoint: str) -> Any:
        import httpx
        url = f"{self.config['ha_url']}{endpoint}"
        headers = {"Authorization": f"Bearer {self.config['ha_token']}", "Content-Type": "application/json"}
        with httpx.Client(timeout=10) as client:
            if method == "GET":
                res = client.get(url, headers=headers)
            else:
                return None
            return res.json() if res.status_code == 200 else None

    async def _get_areas(self) -> list:
        import time
        now = time.time()
        if self._areas_cache and (now - self._cache_time) < self.config.get('cache_ttl', 300):
            return self._areas_cache

        try:
            result = self._ha_request_sync("GET", "/api/config/area_registry")
            if isinstance(result, list):
                self._areas_cache = result
                self._cache_time = now
                return result
        except Exception as e:
            _logger.warning("Error fetching areas: %s", e)

        return self._areas_cache or []

    async def _get_devices(self) -> list:
        import time
        now = time.time()
        if self._devices_cache and (now - self._cache_time) < self.config.get('cache_ttl', 300):
            return self._devices_cache

        try:
            result = self._ha_request_sync("GET", "/api/states")
            if isinstance(result, list):
                devices = []
                for s in result:
                    entity_id = s.get("entity_id", "")
                    domain = entity_id.split(".")[0]
                    if domain in ("light", "switch", "climate", "cover", "lock", "fan", "media_player"):
                        area_id = s.get("attributes", {}).get("area_id", "")
                        devices.append({
                            "entity_id": entity_id,
                            "name": s.get("attributes", {}).get("friendly_name", entity_id),
                            "state": s.get("state"),
                            "domain": domain,
                            "area_id": area_id,
                        })
                self._devices_cache = devices
                self._cache_time = now
                return devices
        except Exception as e:
            _logger.warning("Error fetching devices: %s", e)

        return self._devices_cache or []

    async def _get_devices_by_area(self, area_name: str) -> list:
        areas = await self._get_areas()
        devices = await self._get_devices()

        area_id = None
        for area in areas:
            if area.get("name", "").lower() == area_name.lower():
                area_id = area.get("area_id")
                break

        if not area_id:
            return []

        return [d for d in devices if d.get("area_id") == area_id]

    async def _control_device(self, entity_id: str, action: str) -> bool:
        domain = entity_id.split(".")[0]

        service_map = {
            "turn_on": "turn_on",
            "turn_off": "turn_off",
            "toggle": "toggle",
        }

        service = service_map.get(action, action)

        try:
            result = self._ha_request_sync("POST", f"/api/services/{domain}/{service}")
            if isinstance(result, dict) and "error" in result:
                _logger.warning("HA service error: %s", result["error"])
                return False
            _logger.info("Device control: %s.%s on %s", domain, service, entity_id)
            return True
        except Exception as e:
            _logger.error("Device control error: %s", e)
            return False

    async def _control_room(self, area_name: str, action: str) -> dict:
        devices = await self._get_devices_by_area(area_name)
        results = {}

        for device in devices:
            entity_id = device["entity_id"]
            success = await self._control_device(entity_id, action)
            results[entity_id] = success

        return {
            "area": area_name,
            "action": action,
            "devices_count": len(devices),
            "results": results,
        }

    def define_commands(self, *_args, **_kwargs) -> dict:
        return {
            "комнаты|список комнат": self._handle_list_rooms,
            "комната|где|в комнате": self._handle_room_info,
            "выключи в|отключи в|выключить в": self._handle_room_off,
            "включи в|включить в": self._handle_room_on,
            "все выключить|выключи всё|выключи все": self._handle_all_off,
            "все включить|включи всё|включи все": self._handle_all_on,
        }

    def _handle_list_rooms(self, va, text: str):
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                areas = loop.run_until_complete(self._get_areas())
            finally:
                loop.close()
            if not areas:
                va.say("Комнаты не найдены. Проверьте настройки Home Assistant.")
                return
            room_names = [a.get("name", "Без имени") for a in areas]
            va.say("Комнаты: " + ", ".join(room_names))
        except Exception as e:
            va.say("Ошибка получения комнат")
            _logger.error("List rooms error: %s", e)

    def _handle_room_info(self, va, text: str):
        try:
            area_name = text.strip()
            if not area_name:
                va.say("Укажите название комнаты")
                return

            import asyncio
            loop = asyncio.new_event_loop()
            try:
                devices = loop.run_until_complete(self._get_devices_by_area(area_name))
            finally:
                loop.close()

            if not devices:
                va.say(f"В комнате {area_name} нет устройств")
                return

            device_list = []
            for d in devices:
                state = "включено" if d["state"] == "on" else "выключено"
                device_list.append(f"{d['name']} - {state}")

            va.say(f"В комнате {area_name}: " + ", ".join(device_list))
        except Exception as e:
            va.say("Ошибка получения информации о комнате")
            _logger.error("Room info error: %s", e)

    def _handle_room_off(self, va, text: str):
        try:
            area_name = text.strip()
            if not area_name:
                va.say("Укажите название комнаты")
                return

            import asyncio
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(self._control_room(area_name, "turn_off"))
            finally:
                loop.close()
            va.say(f"Выключено в {area_name}: {result['devices_count']} устройств")
        except Exception as e:
            va.say("Ошибка выключения")
            _logger.error("Room off error: %s", e)

    def _handle_room_on(self, va, text: str):
        try:
            area_name = text.strip()
            if not area_name:
                va.say("Укажите название комнаты")
                return

            import asyncio
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(self._control_room(area_name, "turn_on"))
            finally:
                loop.close()
            va.say(f"Включено в {area_name}: {result['devices_count']} устройств")
        except Exception as e:
            va.say("Ошибка включения")
            _logger.error("Room on error: %s", e)

    def _handle_all_off(self, va, text: str):
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                devices = loop.run_until_complete(self._get_devices())
            finally:
                loop.close()

            count = 0
            for device in devices:
                if device["state"] == "on":
                    import asyncio as _a
                    loop2 = _a.new_event_loop()
                    try:
                        success = loop2.run_until_complete(self._control_device(device["entity_id"], "turn_off"))
                    finally:
                        loop2.close()
                    if success:
                        count += 1

            va.say(f"Выключено {count} устройств")
        except Exception as e:
            va.say("Ошибка выключения всех устройств")
            _logger.error("All off error: %s", e)

    def _handle_all_on(self, va, text: str):
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                devices = loop.run_until_complete(self._get_devices())
            finally:
                loop.close()

            count = 0
            for device in devices:
                if device["state"] == "off":
                    import asyncio as _a
                    loop2 = _a.new_event_loop()
                    try:
                        success = loop2.run_until_complete(self._control_device(device["entity_id"], "turn_on"))
                    finally:
                        loop2.close()
                    if success:
                        count += 1

            va.say(f"Включено {count} устройств")
        except Exception as e:
            va.say("Ошибка включения всех устройств")
            _logger.error("All on error: %s", e)

    def register_fastapi_endpoints(self, router, pm, *_args, **_kwargs):
        from fastapi import APIRouter
        from pydantic import BaseModel

        r: APIRouter = router
        plugin = self

        class ControlRequest(BaseModel):
            entity_id: str
            action: str

        class RoomControlRequest(BaseModel):
            area_name: str
            action: str

        @r.get('/')
        async def list_rooms():
            return await plugin._get_areas()

        @r.get('/devices')
        async def list_devices():
            return await plugin._get_devices()

        @r.get('/devices/{area_name}')
        async def devices_by_room(area_name: str):
            return await plugin._get_devices_by_area(area_name)

        @r.post('/control')
        async def control_device(req: ControlRequest):
            success = await plugin._control_device(req.entity_id, req.action)
            return {"success": success, "entity_id": req.entity_id, "action": req.action}

        @r.post('/room/control')
        async def control_room(req: RoomControlRequest):
            return await plugin._control_room(req.area_name, req.action)
