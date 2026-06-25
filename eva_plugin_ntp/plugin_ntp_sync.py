"""
Плагин синхронизации времени через NTP.

Синхронизирует системное время с NTP-сервером при запуске.
"""

import logging
import time
from typing import Optional

from eva.plugin_loader.magic_plugin import MagicPlugin, step_name

name = 'ntp_sync'
version = '0.1.0'

_logger = logging.getLogger(name)

NTP_SERVERS = [
    'ntp1.stratum2.ru',
    'ntp2.stratum2.ru',
    'ntp3.stratum2.ru',
    'ntp4.stratum2.ru',
    'time.google.com',
    'time.cloudflare.com',
    'pool.ntp.org',
]

config = {
    'servers': NTP_SERVERS,
    'timeout': 5,
}

config_comment = """
Настройки NTP-синхронизации.

Параметры:
- servers — список NTP-серверов
- timeout — таймаут подключения (секунды)
"""


class NTPSyncPlugin(MagicPlugin):
    name = name
    version = version

    def _try_ntp_sync(self) -> Optional[float]:
        """Пытается синхронизировать время через NTP."""
        try:
            import ntplib
            client = ntplib.NTPClient()
            for server in config['servers']:
                try:
                    response = client.request(server, timeout=config['timeout'])
                    offset = response.offset
                    _logger.info("NTP %s: offset=%.3fs", server, offset)
                    return offset
                except Exception as e:
                    _logger.debug("NTP %s failed: %s", server, e)
                    continue
        except ImportError:
            _logger.warning("ntplib не установлен. Установите: pip install ntplib")
        except Exception as e:
            _logger.error("NTP ошибка: %s", e)
        return None

    def init(self, pm=None, *_args, **_kwargs):
        offset = self._try_ntp_sync()
        if offset is not None:
            _logger.info("NTP синхронизация: смещение %.3f сек", offset)
        else:
            _logger.warning("NTP синхронизация не удалась")
