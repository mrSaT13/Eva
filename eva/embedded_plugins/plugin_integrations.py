"""
Интеграции с внешними сервисами.

Поддерживает: FreshRSS, RSS ленты, Music Assistant, Navidrome,
погоду, новости, Wikipedia и другие бесплатные сервисы.
"""

import json
import os
import time
from logging import getLogger
from typing import Any, Optional
from datetime import datetime
from eva.plugin_loader.magic_plugin import MagicPlugin

_logger = getLogger('integrations')


class IntegrationsPlugin(MagicPlugin):
    name = 'integrations'
    version = '1.0.0'

    config: dict[str, Any] = {
        "freshrss_url": "",
        "freshrss_user": "",
        "freshrss_token": "",
        "navidrome_url": "",
        "navidrome_user": "",
        "navidrome_password": "",
        "rss_feeds": [],
        "weather_city": "Moscow",
        "cache_ttl": 300,
    }

    config_comment = """
Интеграции с внешними сервисами.

Параметры:
- freshrss_url    - URL FreshRSS
- freshrss_user   - Пользователь FreshRSS
- freshrss_token  - Токен FreshRSS
- navidrome_url   - URL Navidrome
- navidrome_user  - Пользователь Navidrome
- navidrome_password - Пароль Navidrome
- rss_feeds       - RSS ленты (список URL)
- weather_city    - Город для погоды
- cache_ttl       - Время кэширования (секунды)
"""

    def __init__(self):
        super().__init__()
        self._cache = {}
        self._cache_time = {}

    def _get_cache(self, key: str) -> Any:
        if key in self._cache:
            if time.time() - self._cache_time.get(key, 0) < self.config.get('cache_ttl', 300):
                return self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any):
        self._cache[key] = value
        self._cache_time[key] = time.time()

    def define_commands(self, *_args, **_kwargs) -> dict:
        return {
            "свежие новости|что в мире|последние новости|новости|новости сегодня": self._handle_news,
            "прочитай|прочти|что в ленте": self._handle_read_feed,
            "подкасты|музыка|включи музыку": self._handle_music,
            "погода|какая погода|прогноз": self._handle_weather,
            "вики|википедия|найди в википедии": self._handle_wiki,
            "зайди на|открой сайт|открой страницу": self._handle_open_url,
        }

    def _handle_news(self, va, text: str):
        try:
            import httpx
            feeds = self.config.get('rss_feeds', [])
            if not feeds:
                va.say("RSS ленты не настроены. Добавьте ленты в конфигурацию.")
                return

            from xml.etree import ElementTree
            items = []
            for feed_url in feeds[:5]:
                try:
                    with httpx.Client(timeout=10) as client:
                        res = client.get(feed_url)
                        if res.status_code == 200:
                            root = ElementTree.fromstring(res.text)
                            for item in root.findall('.//item')[:10]:
                                title = item.find('title')
                                desc = item.find('description')
                                if title is not None:
                                    title_text = title.text or ""
                                    desc_text = ""
                                    if desc is not None and desc.text:
                                        import re
                                        desc_text = re.sub(r'<[^>]+>', '', desc.text).strip()[:300]
                                    items.append({"title": title_text, "desc": desc_text})
                except Exception as e:
                    _logger.warning("Error parsing feed %s: %s", feed_url, e)

            if not items:
                va.say("Новости не найдены")
                return

            yield from self._news_dialog(va, items)

        except Exception as e:
            va.say("Ошибка получения новостей")
            _logger.error("News error: %s", e)

    def _news_dialog(self, va, items: list):
        index = 0
        total = len(items)

        while index < total:
            item = items[index]
            title = item["title"]
            desc = item["desc"]

            if desc and len(desc) > 50:
                va.say(f"{title}. {desc}")
                index += 1
            else:
                if index + 1 < total:
                    next_item = items[index + 1]
                    va.say(f"{title}. {next_item['title']}.")
                    index += 2
                else:
                    va.say(title)
                    index += 1

            if index >= total:
                va.say("Это все новости.")
                return

            answer = yield "Хотите ещё новости?"

            if answer is None:
                return

            answer_lower = answer.strip().lower()
            if answer_lower in ("нет", "нет спасибо", "хватит", "стоп", "больше не надо", "нет, спасибо"):
                va.say("Хорошо, как скажете.")
                return

        va.say("Это все новости.")

    def _handle_read_feed(self, va, text: str):
        try:
            import httpx
            feeds = self.config.get('rss_feeds', [])
            if not feeds:
                va.say("RSS ленты не настроены")
                return

            from xml.etree import ElementTree
            items = []
            for feed_url in feeds[:3]:
                try:
                    with httpx.Client(timeout=10) as client:
                        res = client.get(feed_url)
                        if res.status_code == 200:
                            root = ElementTree.fromstring(res.text)
                            for item in root.findall('.//item')[:10]:
                                title = item.find('title')
                                desc = item.find('description')
                                if title is not None:
                                    title_text = title.text or ""
                                    desc_text = ""
                                    if desc is not None and desc.text:
                                        import re
                                        desc_text = re.sub(r'<[^>]+>', '', desc.text).strip()[:300]
                                    items.append({"title": title_text, "desc": desc_text})
                except Exception as e:
                    _logger.warning("Error parsing feed %s: %s", feed_url, e)

            if not items:
                va.say("Нет новых записей")
                return

            yield from self._news_dialog(va, items)

        except Exception as e:
            va.say("Ошибка чтения ленты")
            _logger.error("Read feed error: %s", e)

    def _handle_music(self, va, text: str):
        try:
            import httpx
            navidrome_url = self.config.get('navidrome_url', '')
            if not navidrome_url:
                va.say("Navidrome не настроен. Укажите URL в конфигурации.")
                return

            with httpx.Client(timeout=10) as client:
                res = client.get(
                    f"{navidrome_url}/rest/getRandomSongs",
                    params={
                        "u": self.config.get('navidrome_user', ''),
                        "p": self.config.get('navidrome_password', ''),
                        "v": "1.8.0",
                        "c": "eva",
                        "f": "json",
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    songs = data.get("subsonic-response", {}).get("randomSongs", {}).get("song", [])
                    if songs:
                        song = songs[0]
                        va.say(f"Включаю: {song.get('title', 'Unknown')} - {song.get('artist', 'Unknown')}")
                    else:
                        va.say("Песни не найдены в библиотеке")
                else:
                    va.say("Не удалось подключиться к Navidrome")
        except Exception as e:
            va.say("Ошибка воспроизведения музыки")
            _logger.error("Music error: %s", e)

    def _handle_weather(self, va, text: str):
        try:
            import httpx
            city = self.config.get('weather_city', 'Moscow')
            if text.strip():
                city = text.strip()

            result = None

            try:
                with httpx.Client(timeout=20, follow_redirects=True) as client:
                    res = client.get(f"https://wttr.in/{city}?format=j1&lang=ru")
                    if res.status_code == 200:
                        data = res.json()
                        current = data.get("current_condition", [{}])[0]
                        temp = current.get("temp_C", "нет данных")
                        desc_list = current.get("weatherDesc", [{}])
                        desc = desc_list[0].get("value", "нет данных") if desc_list else "нет данных"
                        humidity = current.get("humidity", "нет данных")
                        wind = current.get("windspeedKmph", "нет данных")
                        feels = current.get("FeelsLikeC", "нет данных")
                        result = f"Сейчас в {city}: {desc}, {temp} градусов, ощущается как {feels}. Влажность {humidity} процентов, ветер {wind} километров в час."
            except Exception as e:
                _logger.warning("wttr.in failed: %s, trying open-meteo", e)

            if not result:
                try:
                    import urllib.request
                    import json as json_mod
                    url = f"https://api.open-meteo.com/v1/forecast?latitude=55.75&longitude=37.62&current_weather=true"
                    if "москва" not in city.lower():
                        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
                        with urllib.request.urlopen(geo_url, timeout=10) as resp:
                            geo_data = json_mod.loads(resp.read())
                            if geo_data.get("results"):
                                lat = geo_data["results"][0]["latitude"]
                                lon = geo_data["results"][0]["longitude"]
                                url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                    with urllib.request.urlopen(url, timeout=10) as resp:
                        data = json_mod.loads(resp.read())
                        cw = data.get("current_weather", {})
                        temp = cw.get("temperature", "нет данных")
                        wind = cw.get("windspeed", "нет данных")
                        code = cw.get("weathercode", 0)
                        wmo = {0: "ясно", 1: "малооблачно", 2: "облачно", 3: "пасмурно",
                               45: "туман", 48: "туман", 51: "морось", 53: "морось", 55: "сильная морось",
                               61: "дождь", 63: "дождь", 65: "сильный дождь", 71: "снег", 73: "снег",
                               75: "сильный снег", 80: "ливень", 95: "гроза"}
                        desc = wmo.get(code, f"код {code}")
                        result = f"Сейчас в {city}: {desc}, {temp} градусов, ветер {wind} километров в час."
                except Exception as e:
                    _logger.warning("open-meteo also failed: %s", e)

            if result:
                va.say(result)
            else:
                va.say(f"Не удалось получить погоду для {city}. Попробуйте позже.")
        except Exception as e:
            va.say("Ошибка получения погоды")
            _logger.error("Weather error: %s", e)

    def _handle_wiki(self, va, text: str):
        try:
            import httpx
            query = text.strip()
            if not query:
                va.say("Что искать в Википедии?")
                return

            with httpx.Client(timeout=10, headers={
                "User-Agent": "Eva/1.0 (https://github.com/eva-assistant; eva@example.com)"
            }) as client:
                res = client.get(
                    "https://ru.wikipedia.org/api/rest_v1/page/summary/" + query
                )
                if res.status_code == 200:
                    data = res.json()
                    extract = data.get("extract", "")
                    if extract:
                        va.say(extract[:500])
                    else:
                        va.say(f"Не удалось найти информацию о {query}")
                else:
                    va.say(f"Не удалось найти информацию о {query} в Википедии")
        except Exception as e:
            va.say("Ошибка поиска в Википедии")
            _logger.error("Wiki error: %s", e)

    def _handle_open_url(self, va, text: str):
        url = text.strip()
        if not url:
            va.say("Укажите URL")
            return

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        va.say(f"Открываю {url}")

    def register_fastapi_endpoints(self, router, pm, *_args, **_kwargs):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel
        from typing import List

        r: APIRouter = router
        plugin = self

        class RSSFeedModel(BaseModel):
            url: str
            name: Optional[str] = ""

        class FreshRSSConfig(BaseModel):
            url: str
            user: str
            token: str

        class NavidromeConfig(BaseModel):
            url: str
            user: str
            password: str

        @r.get('/rss/feeds')
        async def list_rss_feeds():
            return plugin.config.get('rss_feeds', [])

        @r.post('/rss/feeds')
        async def add_rss_feed(req: RSSFeedModel):
            feeds = plugin.config.get('rss_feeds', [])
            feeds.append(req.url)
            plugin.config['rss_feeds'] = feeds
            return {"status": "added", "url": req.url}

        @r.delete('/rss/feeds')
        async def remove_rss_feed(url: str):
            feeds = plugin.config.get('rss_feeds', [])
            plugin.config['rss_feeds'] = [f for f in feeds if f != url]
            return {"status": "removed"}

        @r.get('/rss/latest')
        async def latest_rss_items():
            import asyncio
            from xml.etree import ElementTree

            feeds = plugin.config.get('rss_feeds', [])
            items = []
            for feed_url in feeds[:5]:
                try:
                    content = await plugin._fetch_url(feed_url)
                    if content:
                        root = ElementTree.fromstring(content)
                        for item in root.findall('.//item')[:5]:
                            title = item.find('title')
                            link = item.find('link')
                            pub_date = item.find('pubDate')
                            if title is not None:
                                items.append({
                                    "title": title.text or "",
                                    "link": link.text if link is not None else "",
                                    "date": pub_date.text if pub_date is not None else "",
                                    "feed": feed_url,
                                })
                except Exception as e:
                    _logger.warning("Error parsing feed %s: %s", feed_url, e)
            return items

        @r.get('/freshrss/status')
        async def freshrss_status():
            url = plugin.config.get('freshrss_url', '')
            if not url:
                return {"configured": False}
            return {"configured": True, "url": url}

        @r.get('/navidrome/status')
        async def navidrome_status():
            url = plugin.config.get('navidrome_url', '')
            if not url:
                return {"configured": False}
            return {"configured": True, "url": url}

        @r.get('/navidrome/songs')
        async def navidrome_songs():
            import httpx
            url = plugin.config.get('navidrome_url', '')
            if not url:
                return []
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.get(
                        f"{url}/rest/getSongs",
                        params={
                            "u": plugin.config.get('navidrome_user', ''),
                            "p": plugin.config.get('navidrome_password', ''),
                            "v": "1.8.0",
                            "c": "eva",
                            "f": "json",
                        },
                        timeout=10
                    )
                    if res.status_code == 200:
                        data = res.json()
                        return data.get("subsonic-response", {}).get("songs", {}).get("song", [])
            except Exception:
                pass
            return []

        @r.get('/weather')
        async def get_weather(city: str = "Moscow"):
            import httpx
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.get(f"https://wttr.in/{city}?format=j1", timeout=10)
                    if res.status_code == 200:
                        data = res.json()
                        current = data.get("current_condition", [{}])[0]
                        return {
                            "city": city,
                            "temp": current.get("temp_C", ""),
                            "description": current.get("weatherDesc", [{}])[0].get("value", ""),
                            "humidity": current.get("humidity", ""),
                            "wind": current.get("windspeedKmph", ""),
                        }
            except Exception:
                pass
            return {"error": "Weather service unavailable"}
