"""
Spotify-интеграция Eva: управление воспроизведением через Spotify Web API.

Нужен OAuth-токен пользователя (получить: developer.spotify.com/dashboard,
создать приложение, запросить scope user-modify-playback-state
user-read-playback-state, обменять code на access_token).
Токен вставляется в конфиг `access_token` и обновляется вручную
(или через свой сервис обновления).

Голосовые команды:
- "спотифай играй / пауза / дальше / назад"
- "включи спотифай"
"""

from logging import getLogger
from typing import Any, Optional

from eva.plugin_loader.magic_plugin import MagicPlugin

_logger = getLogger('spotify')


class SpotifyPlugin(MagicPlugin):
    name = 'spotify'
    version = '1.0.0'

    config: dict[str, Any] = {
        "enabled": False,
        "access_token": "",
        "device_id": "",
        "market": "RU",
    }

    config_comment = """
    Управление Spotify через Web API.

    Параметры:
    - `enabled`       - включить интеграцию
    - `access_token`  - OAuth access_token пользователя
                        (scope: user-modify-playback-state, user-read-playback-state).
                        Получить: developer.spotify.com/dashboard -> Create app.
    - `device_id`     - id устройства для воспроизведения (пусто = активное)
    - `market`        - маркет для поиска (по-умолчанию RU)
    """

    def _client(self):
        try:
            import spotipy  # type: ignore
        except ImportError:
            _logger.warning("spotipy не установлен: pip install spotipy")
            return None
        token = (self.config.get('access_token') or '').strip()
        if not token:
            return None
        try:
            return spotipy.Spotify(auth=token)
        except Exception as e:
            _logger.error("Spotify client не создан: %s", e)
            return None

    def _call(self, action: str, *args, **kwargs) -> tuple[bool, str]:
        """Выполняет действие API. Возвращает (ok, сообщение)."""
        sp = self._client()
        if sp is None:
            if not (self.config.get('access_token') or '').strip():
                return False, "Spotify не настроен. Вставьте access_token в конфигурацию."
            return False, "Spotify недоступен. Проверьте токен и зависимость spotipy."
        try:
            getattr(sp, action)(*args, **kwargs)
            return True, "OK"
        except Exception as e:
            msg = str(e)
            _logger.error("Spotify %s: %s", action, msg)
            if '401' in msg or 'Unauthorized' in msg or 'expired' in msg.lower():
                return False, "Токен Spotify истёк. Обновите access_token."
            if '404' in msg or 'NO_ACTIVE_DEVICE' in msg.replace(' ', ''):
                return False, "Нет активного устройства Spotify. Откройте Spotify на устройстве."
            return False, f"Ошибка Spotify: {msg[:150]}"

    # ------------------------------------------------------------------
    # Голосовые команды
    # ------------------------------------------------------------------

    def define_commands(self, *_args, **_kwargs) -> dict:
        return {
            "спотифай играй|включи спотифай|spotify играй|продолжи музыку": self._handle_play,
            "спотифай пауза|спотифай стоп|поставь на паузу|останови музыку": self._handle_pause,
            "спотифай дальше|следующий трек|следующая песня": self._handle_next,
            "спотифай назад|предыдущий трек|предыдущая песня": self._handle_prev,
        }

    def _device_kwargs(self) -> dict:
        if self.config.get('device_id'):
            return {'device_id': self.config['device_id']}
        return {}

    def _handle_play(self, va, text: str):
        ok, msg = self._call('start_playback', **self._device_kwargs())
        va.say("Включаю" if ok else msg)

    def _handle_pause(self, va, text: str):
        ok, msg = self._call('pause_playback', **self._device_kwargs())
        va.say("Пауза" if ok else msg)

    def _handle_next(self, va, text: str):
        ok, msg = self._call('next_track', **self._device_kwargs())
        va.say("Следующий трек" if ok else msg)

    def _handle_prev(self, va, text: str):
        ok, msg = self._call('previous_track', **self._device_kwargs())
        va.say("Предыдущий трек" if ok else msg)

    # ------------------------------------------------------------------
    # REST
    # ------------------------------------------------------------------

    def register_fastapi_endpoints(self, router, *_args, **_kwargs) -> None:
        from fastapi import APIRouter

        r: APIRouter = router
        plugin = self

        @r.get('/spotify/status')
        async def spotify_status():
            sp = plugin._client()
            if sp is None:
                return {"enabled": bool(plugin.config.get('enabled', False)),
                        "configured": bool((plugin.config.get('access_token') or '').strip()),
                        "playing": False}
            try:
                cur = sp.current_playback()
                if not cur:
                    return {"enabled": True, "configured": True,
                            "playing": False, "devices": [d['name'] for d in (sp.devices() or {}).get('devices', [])]}
                item = cur.get('item') or {}
                return {
                    "enabled": True, "configured": True,
                    "playing": bool(cur.get('is_playing')),
                    "track": item.get('name'),
                    "artists": ', '.join(a.get('name', '') for a in item.get('artists', [])),
                    "device": (cur.get('device') or {}).get('name'),
                }
            except Exception as e:
                return {"enabled": True, "configured": True,
                        "playing": False, "error": str(e)[:200]}

        @r.post('/spotify/play')
        async def spotify_play():
            ok, msg = plugin._call('start_playback', **plugin._device_kwargs())
            return {"status": "ok" if ok else "error", "message": msg}

        @r.post('/spotify/pause')
        async def spotify_pause():
            ok, msg = plugin._call('pause_playback', **plugin._device_kwargs())
            return {"status": "ok" if ok else "error", "message": msg}

        @r.post('/spotify/next')
        async def spotify_next():
            ok, msg = plugin._call('next_track', **plugin._device_kwargs())
            return {"status": "ok" if ok else "error", "message": msg}
