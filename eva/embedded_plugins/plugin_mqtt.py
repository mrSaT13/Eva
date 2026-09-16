"""
MQTT-интеграция Eva.

Публикация и подписка на топики MQTT-брокера (Mosquitto и др.).
Совместим с Zigbee2MQTT/Tasmota: топики произвольные, например
zigbee2mqtt/лампа_зал/set с payload {"state": "ON"}.

Голосовые команды:
- "mqtt отправь <топик> <сообщение>"
- "мктт статус"
"""

import json
import time
from logging import getLogger
from threading import Lock
from typing import Any, Optional

from eva.plugin_loader.magic_plugin import MagicPlugin

_logger = getLogger('mqtt')

_DEFAULT_TOPICS = ["eva/in/#", "zigbee2mqtt/+/availability"]


class MqttPlugin(MagicPlugin):
    name = 'mqtt'
    version = '1.0.0'

    config: dict[str, Any] = {
        "enabled": False,
        "host": "127.0.0.1",
        "port": 1883,
        "username": "",
        "password": "",
        "client_id": "eva",
        "topics": _DEFAULT_TOPICS,
        "qos": 0,
    }

    config_comment = """
    MQTT-брокер для IoT устройств.

    Параметры:
    - `enabled`   - включить подключение к брокеру
    - `host`      - адрес брокера (например, 127.0.0.1)
    - `port`      - порт брокера (обычно 1883)
    - `username`  - логин (пусто = без авторизации)
    - `password`  - пароль
    - `client_id` - идентификатор клиента
    - `topics`    - список топиков для подписки (поддерживаются + и #)
    - `qos`       - QoS по-умолчанию (0/1/2)

    Примеры топиков Zigbee2MQTT:
    - zigbee2mqtt/лампа_зал/set -> {"state": "ON"}
    - zigbee2mqtt/лампа_зал -> состояние устройства
    """

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[Any] = None
        self._lock = Lock()
        self._last_message: dict[str, Any] = {}
        self._connected = False

    # ------------------------------------------------------------------
    # Подключение
    # ------------------------------------------------------------------

    def _create_client(self):
        try:
            import paho.mqtt.client as mqtt  # type: ignore
        except ImportError:
            _logger.warning("paho-mqtt не установлен: pip install paho-mqtt. MQTT отключён.")
            return None
        try:
            client = mqtt.Client(client_id=self.config.get('client_id', 'eva') or 'eva')
        except TypeError:
            client = mqtt.Client()
        if self.config.get('username'):
            client.username_pw_set(self.config['username'], self.config.get('password', ''))
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        return client

    def _on_connect(self, client, userdata, flags, rc, *args):
        self._connected = (rc == 0)
        if rc == 0:
            _logger.info("MQTT подключён к %s:%s",
                         self.config.get('host'), self.config.get('port'))
            for topic in self.config.get('topics', []) or []:
                try:
                    client.subscribe(topic, qos=int(self.config.get('qos', 0)))
                except Exception as e:
                    _logger.warning("Подписка %s не удалась: %s", topic, e)
        else:
            _logger.warning("MQTT connect rc=%s", rc)

    def _on_disconnect(self, client, userdata, rc, *args):
        self._connected = False
        _logger.info("MQTT отключён (rc=%s)", rc)

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8', errors='replace')
        except Exception:
            payload = ''
        with self._lock:
            self._last_message = {
                'topic': msg.topic, 'payload': payload, 'time': time.time(),
            }
        _logger.debug("MQTT %s: %s", msg.topic, payload[:200])

    async def run(self, *_args, **_kwargs):
        if not self.config.get('enabled'):
            _logger.info("MQTT выключен (enabled=false)")
            return
        client = self._create_client()
        if client is None:
            return
        self._client = client
        try:
            client.connect(str(self.config.get('host', '127.0.0.1')),
                           int(self.config.get('port', 1883)), keepalive=60)
        except Exception as e:
            _logger.error("MQTT connect %s:%s не удался: %s",
                          self.config.get('host'), self.config.get('port'), e)
            self._client = None
            return
        client.loop_start()
        _logger.info("MQTT loop запущен")

    def terminate(self, *_args, **_kwargs):
        client, self._client = self._client, None
        if client is not None:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # API для других плагинов / автоматизаций
    # ------------------------------------------------------------------

    def publish(self, topic: str, payload: Any, qos: Optional[int] = None) -> bool:
        with self._lock:
            client = self._client
        if client is None or not self._connected:
            _logger.warning("MQTT publish без подключения: %s", topic)
            return False
        if not isinstance(payload, str):
            payload = json.dumps(payload, ensure_ascii=False)
        try:
            info = client.publish(topic, payload,
                                  qos=int(self.config.get('qos', 0)) if qos is None else qos)
            info.wait_for_publish(timeout=5)
            return True
        except Exception as e:
            _logger.error("MQTT publish %s не удался: %s", topic, e)
            return False

    def last_message(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._last_message)

    def is_connected(self) -> bool:
        return bool(self._connected and self._client is not None)

    # ------------------------------------------------------------------
    # Голосовые команды
    # ------------------------------------------------------------------

    def define_commands(self, *_args, **_kwargs) -> dict:
        return {
            "мктт статус|mqtt статус|mqtt подключен": self._handle_status,
            "мктт отправь|mqtt отправь|mqtt опубликуй|отправь mqtt": self._handle_publish,
            "мктт последнее|mqtt последнее|что пришло mqtt": self._handle_last,
        }

    def _handle_status(self, va, text: str):
        if self.is_connected():
            va.say(f"MQTT подключён к {self.config.get('host')}")
        else:
            va.say("MQTT не подключён. Проверьте настройки брокера.")

    def _handle_publish(self, va, text: str):
        parts = text.strip().split()
        # формат: "... отправь <топик> <сообщение...>"
        try:
            idx = next(i for i, w in enumerate(parts)
                       if w in ('отправь', 'опубликуй', 'send', 'publish'))
        except StopIteration:
            va.say("Скажите: эм кью ти ти отправь топик сообщение")
            return
        rest = parts[idx + 1:]
        if len(rest) < 2:
            va.say("Нужны топик и сообщение")
            return
        topic, payload = rest[0], ' '.join(rest[1:])
        if self.publish(topic, payload):
            va.say(f"Отправлено в {topic}")
        else:
            va.say("Не удалось отправить. Нет подключения к брокеру.")

    def _handle_last(self, va, text: str):
        last = self.last_message()
        if last:
            va.say(f"Последнее: {last['topic']}: {last['payload'][:200]}")
        else:
            va.say("Сообщений пока не было")

    # ------------------------------------------------------------------
    # REST
    # ------------------------------------------------------------------

    def register_fastapi_endpoints(self, router, *_args, **_kwargs) -> None:
        from fastapi import APIRouter
        from pydantic import BaseModel

        r: APIRouter = router
        plugin = self

        class PublishModel(BaseModel):
            topic: str
            payload: Any = ""
            qos: Optional[int] = None

        @r.get('/mqtt/status')
        async def mqtt_status():
            return {
                "enabled": bool(plugin.config.get('enabled', False)),
                "connected": plugin.is_connected(),
                "host": plugin.config.get('host'),
                "port": plugin.config.get('port'),
                "topics": plugin.config.get('topics', []),
                "last_message": plugin.last_message(),
            }

        @r.post('/mqtt/publish')
        async def mqtt_publish(body: PublishModel):
            ok = plugin.publish(body.topic, body.payload, body.qos)
            return {"status": "ok" if ok else "error",
                    "connected": plugin.is_connected()}
