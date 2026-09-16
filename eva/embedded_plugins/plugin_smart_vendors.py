"""
Мост вендоров умного дома: Яндекс Станция, Google Home, Xiaomi Mi Home,
Tuya, Philips Hue, IKEA Trådfri, Zigbee.

Профессиональная архитектура: все эти вендоры нативно поддерживаются
Home Assistant — Eva управляет ими через HA-сущности, а не плодит
шесть отдельных облачных клиентов. Этот плагин:
- хранит per-vendor настройки (включён/выключен, подсказки по подключению);
- проверяет связность (HA доступен? MQTT-брокер для Zigbee2MQTT доступен?);
- отдаёт каталог вендоров фронту для карточек интеграций.

Прямое управление устройствами идёт через существующие механизмы:
- HA: plugin_automations (ha_url/ha_token)
- Zigbee2MQTT/Tasmota/Tuya-local: plugin_mqtt
"""

from logging import getLogger
from typing import Any, Optional

from eva.plugin_loader.magic_plugin import MagicPlugin

_logger = getLogger('smart_vendors')

VENDORS: tuple[dict[str, Any], ...] = (
    {"id": "yandex", "name": "Яндекс Станция", "backend": "home_assistant",
     "ha_domain": "yandex_station",
     "hint": "Установите интеграцию Yandex Station в Home Assistant, затем управляйте колонкой голосом через Eva."},
    {"id": "google_home", "name": "Google Home", "backend": "home_assistant",
     "ha_domain": "google_assistant",
     "hint": "Свяжите Google Assistant с Home Assistant (Home Assistant Cloud или ручная настройка)."},
    {"id": "xiaomi", "name": "Xiaomi Mi Home", "backend": "home_assistant",
     "ha_domain": "xiaomi_miio",
     "hint": "Добавьте интеграцию Xiaomi Miio в Home Assistant (понадобится токен устройства)."},
    {"id": "tuya", "name": "Tuya", "backend": "home_assistant",
     "ha_domain": "tuya",
     "hint": "Добавьте официальную интеграцию Tuya в Home Assistant через QR-код из приложения Smart Life."},
    {"id": "philips", "name": "Philips Hue", "backend": "home_assistant",
     "ha_domain": "hue",
     "hint": "Интеграция Hue в Home Assistant находится автоматически при нажатии кнопки на мосту."},
    {"id": "ikea", "name": "IKEA Trådfri/Dirigera", "backend": "home_assistant",
     "ha_domain": "tradfri",
     "hint": "Добавьте шлюз IKEA в Home Assistant (Trådfri) или Matter-интеграцию (Dirigera)."},
    {"id": "zigbee", "name": "Zigbee (Zigbee2MQTT)", "backend": "mqtt",
     "ha_domain": "mqtt",
     "hint": "Подключите Zigbee2MQTT к MQTT-брокеру Eva (настройка mqtt), устройства появятся как топики zigbee2mqtt/+."},
)


class SmartVendorsPlugin(MagicPlugin):
    name = 'smart_vendors'
    version = '1.0.0'

    config: dict[str, Any] = {
        "enabled": {v["id"]: False for v in VENDORS},
        "notes": {v["id"]: "" for v in VENDORS},
    }

    config_comment = """
    Вендоры умного дома через Home Assistant / MQTT.

    Параметры:
    - `enabled` - какие вендоры считать подключёнными (yandex, google_home,
                  xiaomi, tuya, philips, ikea, zigbee)
    - `notes`   - произвольные заметки по вендору (IP шлюза, имена и т.д.)

    Само управление идёт через Home Assistant (его интеграции) и MQTT
    (Zigbee2MQTT). Здесь только учёт и проверка связности.
    """

    def _ha_connected(self, pm) -> bool:
        try:
            get_plugin = getattr(pm, 'get_plugin_by_name', None)
            for pname in ('automations', 'voice_commands', 'integrations'):
                p = get_plugin(pname) if callable(get_plugin) else None
                cfg = (getattr(p, 'config', {}) or {}) if p else {}
                if cfg.get('ha_url') and cfg.get('ha_token'):
                    return True
        except Exception:
            pass
        return False

    def _mqtt_connected(self, pm) -> bool:
        try:
            get_plugin = getattr(pm, 'get_plugin_by_name', None)
            p = get_plugin('mqtt') if callable(get_plugin) else None
            if p is not None and hasattr(p, 'is_connected'):
                return bool(p.is_connected())
        except Exception:
            pass
        return False

    def vendor_status(self, vendor_id: str, pm=None) -> dict[str, Any]:
        vendor = next((v for v in VENDORS if v["id"] == vendor_id), None)
        if vendor is None:
            return {"id": vendor_id, "error": "unknown vendor"}
        enabled = bool(self.config.get('enabled', {}).get(vendor_id, False))
        backend_ok: Optional[bool] = None
        if pm is not None:
            if vendor["backend"] == "home_assistant":
                backend_ok = self._ha_connected(pm)
            elif vendor["backend"] == "mqtt":
                backend_ok = self._mqtt_connected(pm)
        state = "off"
        if enabled and backend_ok:
            state = "ok"
        elif enabled:
            state = "misconfigured"
        return {
            "id": vendor["id"], "name": vendor["name"],
            "backend": vendor["backend"], "ha_domain": vendor["ha_domain"],
            "hint": vendor["hint"], "enabled": enabled,
            "backend_ok": backend_ok, "state": state,
            "note": self.config.get('notes', {}).get(vendor_id, ''),
        }

    def define_commands(self, *_args, **_kwargs) -> dict:
        return {
            "умный дом статус|статус вендоров|что подключено": self._handle_status,
        }

    def _handle_status(self, va, text: str):
        enabled = [v["name"] for v in VENDORS
                   if self.config.get('enabled', {}).get(v["id"], False)]
        if enabled:
            va.say("Подключены: " + ", ".join(enabled))
        else:
            va.say("Вендоры не включены. Откройте интеграции и включите нужные.")

    def register_fastapi_endpoints(self, router, pm, *_args, **_kwargs) -> None:
        from fastapi import APIRouter
        from pydantic import BaseModel
        from typing import Optional as Opt

        r: APIRouter = router
        plugin = self

        class VendorPatch(BaseModel):
            enabled: Opt[bool] = None
            note: Opt[str] = None

        @r.get('/vendors')
        async def list_vendors():
            return [plugin.vendor_status(v["id"], pm) for v in VENDORS]

        @r.get('/vendors/{vendor_id}')
        async def get_vendor(vendor_id: str):
            return plugin.vendor_status(vendor_id, pm)

        @r.patch('/vendors/{vendor_id}')
        async def patch_vendor(vendor_id: str, body: VendorPatch):
            if next((v for v in VENDORS if v["id"] == vendor_id), None) is None:
                return {"status": "error", "error": "unknown vendor"}
            if body.enabled is not None:
                plugin.config.setdefault('enabled', {})[vendor_id] = bool(body.enabled)
            if body.note is not None:
                plugin.config.setdefault('notes', {})[vendor_id] = body.note
            return {"status": "ok", **plugin.vendor_status(vendor_id, pm)}
